"""
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
--------------------------------------------------------------------------------
 Project : EBS AP PAF — Accounts Payable Invoice Automation Agent
 Module  : invoice_agent.py — orchestrator
 Version : 1.0.0      Build : 2026.06.02      Date : 2026-06-02
--------------------------------------------------------------------------------
 Mirrors the PAF flow, with the repository and extractor injected so the same
 orchestrator runs against mock fixtures or the live EBS database:

   1. extract            -> header + line items from the invoice text
   2. EBS lookups (repo) -> supplier, duplicate, PO, receipts, tax, GL
   3. policy             -> 3-way match + GL/tax coding
   4. build + QA         -> AP interface rows + qa_report
================================================================================
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from .extractor import InvoiceExtractor
from .interface_writer import EBSInterfaceWriter
from .policy_engine import code_distribution, code_tax, three_way_match
from .qa_checks import QAReport, validate_invoice
from .repository import EBSRepository


@dataclass
class AgentTrace:
    """Explainability log — required for SOX-relevant AP automation."""

    run_id: str
    invoice_number: str | None = None
    extracted: dict[str, Any] | None = None
    supplier_match: dict[str, Any] | None = None
    po_match: dict[str, Any] | None = None
    line_matches: list[dict[str, Any]] = field(default_factory=list)
    duplicate_check: bool = False
    auto_approved: bool = False
    exceptions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    qa: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "invoice_number": self.invoice_number,
            "extracted": self.extracted,
            "supplier_match": self.supplier_match,
            "po_match": ({k: v for k, v in self.po_match.items() if k != "lines"}
                         if self.po_match else None),
            "line_matches": self.line_matches,
            "duplicate_check": self.duplicate_check,
            "auto_approved": self.auto_approved,
            "exceptions": self.exceptions,
            "confidence": self.confidence,
            "qa": self.qa,
        }


class InvoiceAgent:
    """Processes invoices using an injected repository + extractor."""

    def __init__(self,
                 repository: EBSRepository,
                 extractor: InvoiceExtractor,
                 org_id: int = 204,
                 qa_conn: Any | None = None):
        self.repo = repository
        self.extractor = extractor
        self.org_id = org_id
        self.qa_conn = qa_conn  # optional EBSConnection for referential QA
        self.writer = EBSInterfaceWriter(org_id=org_id)
        self.qa_reports: list[QAReport] = []

    # ------------------------------------------------------------------
    def process(self, invoice_text: str) -> AgentTrace:
        """Full pipeline: extract the invoice text, then process it."""
        extracted = self.extractor.extract(invoice_text)
        return self.process_extracted(extracted)

    def process_extracted(self, extracted: dict[str, Any]) -> AgentTrace:
        """Process an already-extracted invoice dict (steps 2-7).

        Split out from process() so a PAF flow can perform extraction in its own
        LLM node and hand the structured invoice to a single policy/QA tool.
        """
        run_id = f"AGT-{uuid.uuid4().hex[:10].upper()}"
        trace = AgentTrace(run_id=run_id)
        trace.extracted = extracted
        trace.invoice_number = extracted.get("invoice_number")

        # supplier lookup
        supplier = self.repo.get_supplier(
            vendor_name=extracted.get("vendor_name"),
            tax_id=extracted.get("vendor_tax_id"),
        )
        if supplier is None:
            trace.exceptions.append("SUPPLIER_NOT_FOUND")
            return trace
        trace.supplier_match = supplier

        # duplicate check
        if self.repo.check_duplicate_invoice(supplier["vendor_id"],
                                             extracted["invoice_number"]):
            trace.exceptions.append("DUPLICATE_INVOICE")
            trace.duplicate_check = True
            return trace

        # PO + receipts
        po = None
        receipts: list[dict[str, Any]] = []
        if extracted.get("po_number"):
            po = self.repo.get_purchase_order(extracted["po_number"])
            if po:
                trace.po_match = po
                receipts = self.repo.get_receipts(extracted["po_number"])
            else:
                trace.exceptions.append(f"PO_NOT_FOUND_{extracted['po_number']}")
                return trace
        else:
            trace.exceptions.append("NON_PO_INVOICE")

        # line-by-line match + coding
        matched_lines: list[dict[str, Any]] = []
        all_auto = True
        for line in extracted["lines"]:
            if po is not None:
                match = three_way_match(line, po, receipts)
                trace.line_matches.append({
                    "line_number": match.line_number,
                    "matched": match.matched,
                    "auto_approve": match.auto_approve,
                    "exceptions": match.exceptions,
                    "po_unit_price": _s(match.po_unit_price),
                    "invoice_unit_price": _s(match.invoice_unit_price),
                    "qty_received": _s(match.qty_received),
                    "qty_invoiced": _s(match.qty_invoiced),
                })
                if not match.auto_approve:
                    all_auto = False

                po_line = next((l for l in po["lines"]
                                if l["line_num"] == line.get("po_line_num")), {})
                dist = code_distribution(po_line, self.repo.get_gl_segments)
                tax_code = code_tax(line, extracted["jurisdiction"],
                                    self.repo.get_tax_code)
                matched_lines.append({
                    **line,
                    "dist_code_concatenated": dist["dist_code_concatenated"],
                    "tax_classification_code": tax_code,
                    "inventory_item_id": po_line.get("inventory_item_id"),
                    "match_status": "AUTO" if match.auto_approve else "HOLD",
                    "exceptions": match.exceptions,
                })
            else:
                tax_code = code_tax(line, extracted["jurisdiction"],
                                    self.repo.get_tax_code)
                matched_lines.append({
                    **line,
                    "dist_code_concatenated": None,
                    "tax_classification_code": tax_code,
                    "inventory_item_id": None,
                    "match_status": "NON_PO_REVIEW",
                    "exceptions": ["NON_PO_INVOICE"],
                })
                all_auto = False

        trace.auto_approved = all_auto
        trace.confidence = self._confidence(extracted, matched_lines)

        # build interface rows
        invoice_id = self.writer.add_invoice(
            extracted=extracted, supplier=supplier,
            matched_lines=matched_lines, agent_run_id=run_id,
            confidence=trace.confidence,
        )

        # QA gate over the just-built rows for this invoice
        header = next(h for h in self.writer.headers
                      if h["INVOICE_ID"] == invoice_id)
        inv_lines = [l for l in self.writer.lines
                     if l["INVOICE_ID"] == invoice_id]
        report = validate_invoice(header, inv_lines, extracted, matched_lines,
                                  conn=self.qa_conn, org_id=self.org_id)
        self.qa_reports.append(report)
        trace.qa = report.to_dict()
        return trace

    # ------------------------------------------------------------------
    @staticmethod
    def _confidence(extracted: dict[str, Any],
                    matched: list[dict[str, Any]]) -> float:
        if not matched:
            return 0.0
        clean = sum(1 for m in matched if m.get("match_status") == "AUTO")
        line_score = clean / len(matched)
        line_sum = sum(Decimal(str(m["amount"])) for m in matched)
        declared = Decimal(str(extracted.get("subtotal") or extracted["total"]))
        recon = (max(0.0, 1.0 - float(abs(line_sum - declared) / declared))
                 if declared > 0 else 0.0)
        return round((line_score * 0.7) + (recon * 0.3), 3)

    # ------------------------------------------------------------------
    def flush(self, out_dir: str | Path) -> tuple[Path, Path]:
        return self.writer.write(out_dir)


def _s(value: Any) -> str | None:
    return str(value) if value is not None else None
