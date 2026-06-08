"""
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
--------------------------------------------------------------------------------
 Project : EBS AP PAF — Accounts Payable Invoice Automation Agent
 Module  : qa_checks.py — pre-load data-quality validation gate
 Version : 1.0.0      Build : 2026.06.02      Date : 2026-06-02
--------------------------------------------------------------------------------
 Deterministic checks run AFTER the interface rows are built and BEFORE anything
 is written / loaded. Produces a structured QAReport (serialised to
 qa_report.json). Severity model:

   ERROR  -> the invoice is malformed; the load MUST be blocked.
   HOLD   -> well-formed but outside policy tolerance; route to manual approval.
   WARN   -> non-blocking anomaly worth surfacing.
   INFO   -> informational.

 "Bugs make me sad" — this gate is the last line of defence before EBS.
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

CENT = Decimal("0.01")

ERROR = "ERROR"
HOLD = "HOLD"
WARN = "WARN"
INFO = "INFO"

VALID_INVOICE_TYPES = {"STANDARD", "CREDIT", "DEBIT", "PREPAYMENT", "MIXED"}
VALID_LINE_TYPES = {"ITEM", "TAX", "FREIGHT", "MISCELLANEOUS"}
REQUIRED_HEADER = [
    "INVOICE_NUM", "INVOICE_DATE", "VENDOR_ID", "VENDOR_SITE_ID",
    "INVOICE_AMOUNT", "INVOICE_TYPE_LOOKUP_CODE", "ORG_ID", "SOURCE", "GROUP_ID",
]


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


@dataclass
class Finding:
    check: str
    severity: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "severity": self.severity,
            "passed": self.passed,
            "detail": self.detail,
        }


@dataclass
class QAReport:
    invoice_num: str | None
    findings: list[Finding] = field(default_factory=list)

    def add(self, check: str, severity: str, passed: bool, detail: str) -> None:
        self.findings.append(Finding(check, severity, passed, detail))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if not f.passed and f.severity == ERROR]

    @property
    def holds(self) -> list[Finding]:
        return [f for f in self.findings if not f.passed and f.severity == HOLD]

    @property
    def loadable(self) -> bool:
        """True only if there are no ERROR or HOLD findings."""
        return not self.errors and not self.holds

    @property
    def status(self) -> str:
        if self.errors:
            return "FAIL"
        if self.holds:
            return "HOLD"
        return "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "invoice_num": self.invoice_num,
            "status": self.status,
            "loadable": self.loadable,
            "error_count": len(self.errors),
            "hold_count": len(self.holds),
            "findings": [f.to_dict() for f in self.findings],
        }


def validate_invoice(
    header: dict[str, Any],
    lines: list[dict[str, Any]],
    extracted: dict[str, Any],
    matched_lines: list[dict[str, Any]],
    conn: Any | None = None,
    org_id: int = 204,
) -> QAReport:
    """Run all QA checks for one invoice. `conn` (optional EBSConnection) enables
    referential checks against live EBS."""
    report = QAReport(invoice_num=header.get("INVOICE_NUM"))

    # --- 1. required header fields --------------------------------------
    for col in REQUIRED_HEADER:
        val = header.get(col)
        report.add(
            f"header.{col}", ERROR, val not in (None, ""),
            f"{col}={val!r}",
        )

    # --- 2. lookup validity ---------------------------------------------
    inv_type = header.get("INVOICE_TYPE_LOOKUP_CODE")
    report.add("header.invoice_type_valid", ERROR,
               inv_type in VALID_INVOICE_TYPES, f"type={inv_type!r}")
    for ln in lines:
        lt = ln.get("LINE_TYPE_LOOKUP_CODE")
        report.add(f"line[{ln.get('LINE_NUMBER')}].type_valid", ERROR,
                   lt in VALID_LINE_TYPES, f"line_type={lt!r}")
        report.add(f"line[{ln.get('LINE_NUMBER')}].org_id", ERROR,
                   ln.get("ORG_ID") not in (None, ""),
                   f"org_id={ln.get('ORG_ID')!r}")

    # --- 3. per-line arithmetic (ITEM lines) ----------------------------
    for ln in lines:
        if ln.get("LINE_TYPE_LOOKUP_CODE") != "ITEM":
            continue
        try:
            qty = _d(ln["QUANTITY_INVOICED"])
            price = _d(ln["UNIT_PRICE"])
            amount = _d(ln["AMOUNT"])
        except Exception:
            report.add(f"line[{ln.get('LINE_NUMBER')}].arithmetic", ERROR,
                       False, "non-numeric qty/price/amount")
            continue
        expected = (qty * price).quantize(CENT)
        ok = abs(expected - amount.quantize(CENT)) <= CENT
        report.add(f"line[{ln.get('LINE_NUMBER')}].arithmetic", ERROR, ok,
                   f"qty*price={expected} vs amount={amount}")

    # --- 4. header balances to sum of lines -----------------------------
    line_sum = sum((_d(ln["AMOUNT"]) for ln in lines), Decimal("0")).quantize(CENT)
    hdr_amt = _d(header["INVOICE_AMOUNT"]).quantize(CENT)
    report.add("header.balances_to_lines", ERROR,
               abs(line_sum - hdr_amt) <= CENT,
               f"sum(lines)={line_sum} vs header={hdr_amt}")

    # --- 5. reconciliation vs the invoice's declared total --------------
    declared_total = extracted.get("total")
    if declared_total is not None:
        ok = abs(_d(declared_total).quantize(CENT) - hdr_amt) <= CENT
        report.add("header.reconciles_declared_total", WARN, ok,
                   f"declared={declared_total} vs computed={hdr_amt}")

    # --- 6. match status -> HOLD ----------------------------------------
    for ml in matched_lines:
        status = ml.get("match_status", "AUTO")
        if status != "AUTO":
            report.add(f"line[{ml.get('line_number')}].match_status", HOLD, False,
                       f"status={status}; exceptions={ml.get('exceptions')}")

    # --- 7. referential checks (only with a live connection) ------------
    if conn is not None:
        _referential_checks(report, header, lines, org_id, conn)

    return report


def _referential_checks(report: QAReport, header: dict[str, Any],
                        lines: list[dict[str, Any]], org_id: int,
                        conn: Any) -> None:
    """Validate FKs against live EBS: GL combinations enabled, tax codes exist,
    and the invoice is not a duplicate."""
    # distinct distribution combinations on ITEM lines
    combos = {ln.get("DIST_CODE_CONCATENATED") for ln in lines
              if ln.get("DIST_CODE_CONCATENATED")}
    for seg in combos:
        row = conn.query_one(
            "SELECT COUNT(*) AS n FROM apps.gl_code_combinations_kfv "
            "WHERE concatenated_segments = :seg AND enabled_flag = 'Y'",
            {"seg": seg},
        )
        report.add(f"gl.combination_enabled[{seg}]", ERROR,
                   bool(row and row["n"] > 0), f"{seg} enabled rows={row}")

    tax_codes = {ln.get("TAX_CLASSIFICATION_CODE") for ln in lines
                 if ln.get("TAX_CLASSIFICATION_CODE")}
    for code in tax_codes:
        row = conn.query_one(
            "SELECT COUNT(*) AS n FROM apps.zx_rates_b "
            "WHERE tax_rate_code = :c AND active_flag = 'Y'",
            {"c": code},
        )
        report.add(f"tax.code_exists[{code}]", WARN,
                   bool(row and row["n"] > 0), f"{code} active rows={row}")

    # duplicate against posted invoices
    row = conn.query_one(
        "SELECT COUNT(*) AS n FROM apps.ap_invoices_all "
        "WHERE vendor_id = :v AND invoice_num = :i AND org_id = :o",
        {"v": header.get("VENDOR_ID"), "i": header.get("INVOICE_NUM"),
         "o": org_id},
    )
    report.add("duplicate.not_already_posted", ERROR,
               not (row and row["n"] > 0),
               f"posted matches={row}")
