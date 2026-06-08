"""
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
--------------------------------------------------------------------------------
 Project : EBS AP PAF — Accounts Payable Invoice Automation Agent
 Module  : interface_writer.py — AP Open Interface row builder + CSV writer
 Version : 1.0.0      Build : 2026.06.02      Date : 2026-06-02
--------------------------------------------------------------------------------
 Builds AP_INVOICES_INTERFACE / AP_INVOICE_LINES_INTERFACE rows in the column
 order expected by the EBS Payables Open Interface Import. Column names mirror
 the EBS data dictionary so the output drops straight into SQL*Loader / OIC
 without remapping.

 Correctness fixes vs the reference PoC:
   * The header INVOICE_AMOUNT now equals item lines + tax, and a dedicated TAX
     line is emitted, so the document BALANCES (header == sum of lines). The
     reference dropped tax entirely and would be rejected at import.
   * Foreign-currency handling is explicit: 'Corporate' rate type with a derived
     (blank) rate is valid; an explicit rate can be supplied.
================================================================================
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

HEADER_COLS = [
    "INVOICE_ID", "INVOICE_NUM", "INVOICE_TYPE_LOOKUP_CODE", "INVOICE_DATE",
    "VENDOR_ID", "VENDOR_NUM", "VENDOR_NAME", "VENDOR_SITE_ID",
    "VENDOR_SITE_CODE", "INVOICE_AMOUNT", "INVOICE_CURRENCY_CODE",
    "EXCHANGE_RATE", "EXCHANGE_RATE_TYPE", "EXCHANGE_DATE", "TERMS_NAME",
    "TERMS_ID", "DESCRIPTION", "SOURCE", "GROUP_ID", "PO_NUMBER",
    "PAYMENT_METHOD_LOOKUP_CODE", "ORG_ID", "GL_DATE", "ATTRIBUTE1",
    "ATTRIBUTE2",
]

LINE_COLS = [
    "INVOICE_ID", "INVOICE_LINE_ID", "LINE_NUMBER", "LINE_TYPE_LOOKUP_CODE",
    "AMOUNT", "DESCRIPTION", "DIST_CODE_CONCATENATED", "PO_NUMBER",
    "PO_LINE_NUMBER", "INVENTORY_ITEM_ID", "ITEM_DESCRIPTION",
    "QUANTITY_INVOICED", "UNIT_PRICE", "UNIT_OF_MEAS_LOOKUP_CODE",
    "TAX_CLASSIFICATION_CODE", "ORG_ID", "ATTRIBUTE1", "ATTRIBUTE2",
]


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


class EBSInterfaceWriter:
    """Accumulates AP interface rows and emits the two CSVs."""

    def __init__(self,
                 source: str = "EBS_AGENT_PAF",
                 group_id: str | None = None,
                 org_id: int = 204):
        self.source = source
        self.group_id = group_id or f"AGENT_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
        self.org_id = org_id
        self.headers: list[dict[str, Any]] = []
        self.lines: list[dict[str, Any]] = []
        self._next_invoice_id = 1
        self._next_line_id = 1

    # ------------------------------------------------------------------
    def add_invoice(self,
                    extracted: dict[str, Any],
                    supplier: dict[str, Any],
                    matched_lines: list[dict[str, Any]],
                    agent_run_id: str,
                    confidence: float) -> int:
        """Add one invoice (1 header + N item lines + optional TAX line)."""
        invoice_id = self._next_invoice_id
        self._next_invoice_id += 1

        item_total = sum((_d(l["amount"]) for l in matched_lines), Decimal("0"))
        tax_total = _d(extracted.get("tax_total") or 0)
        header_amount = item_total + tax_total

        currency = extracted.get("currency") or "USD"
        is_foreign = currency != "USD"

        header = {
            "INVOICE_ID": invoice_id,
            "INVOICE_NUM": extracted["invoice_number"],
            "INVOICE_TYPE_LOOKUP_CODE": "STANDARD",
            "INVOICE_DATE": extracted["invoice_date"],
            "VENDOR_ID": supplier["vendor_id"],
            "VENDOR_NUM": supplier["vendor_num"],
            "VENDOR_NAME": supplier["vendor_name"],
            "VENDOR_SITE_ID": supplier["vendor_site_id"],
            "VENDOR_SITE_CODE": supplier["vendor_site_code"],
            "INVOICE_AMOUNT": f"{header_amount:.2f}",
            "INVOICE_CURRENCY_CODE": currency,
            # 'Corporate' type → EBS derives the rate from GL daily rates, so a
            # blank EXCHANGE_RATE is valid. Only 'User' type needs an explicit one.
            "EXCHANGE_RATE": "",
            "EXCHANGE_RATE_TYPE": "Corporate" if is_foreign else "",
            "EXCHANGE_DATE": extracted["invoice_date"] if is_foreign else "",
            "TERMS_NAME": supplier.get("payment_terms") or "",
            "TERMS_ID": supplier.get("terms_id") or "",
            "DESCRIPTION": f"Auto-imported by PAF agent {agent_run_id}",
            "SOURCE": self.source,
            "GROUP_ID": self.group_id,
            "PO_NUMBER": extracted.get("po_number") or "",
            "PAYMENT_METHOD_LOOKUP_CODE": supplier.get("payment_method") or "",
            "ORG_ID": self.org_id,
            "GL_DATE": extracted["invoice_date"],
            "ATTRIBUTE1": agent_run_id,
            "ATTRIBUTE2": f"{confidence:.3f}",
        }
        self.headers.append(header)

        for ml in matched_lines:
            self.lines.append(self._item_line(invoice_id, ml, extracted))

        # Dedicated TAX line so the document balances in EBS.
        if tax_total > 0:
            self.lines.append(
                self._tax_line(invoice_id, matched_lines, tax_total)
            )

        return invoice_id

    # ------------------------------------------------------------------
    def _item_line(self, invoice_id: int, ml: dict[str, Any],
                   extracted: dict[str, Any]) -> dict[str, Any]:
        line = {
            "INVOICE_ID": invoice_id,
            "INVOICE_LINE_ID": self._next_line_id,
            "LINE_NUMBER": ml["line_number"],
            "LINE_TYPE_LOOKUP_CODE": "ITEM",
            "AMOUNT": f"{_d(ml['amount']):.2f}",
            "DESCRIPTION": (ml.get("description") or "")[:240],
            "DIST_CODE_CONCATENATED": ml.get("dist_code_concatenated") or "",
            "PO_NUMBER": extracted.get("po_number") or "",
            "PO_LINE_NUMBER": ml.get("po_line_num") or "",
            "INVENTORY_ITEM_ID": ml.get("inventory_item_id") or "",
            "ITEM_DESCRIPTION": (ml.get("description") or "")[:240],
            "QUANTITY_INVOICED": ml["quantity"],
            "UNIT_PRICE": ml["unit_price"],
            "UNIT_OF_MEAS_LOOKUP_CODE": ml.get("uom") or "EA",
            "TAX_CLASSIFICATION_CODE": ml.get("tax_classification_code") or "",
            "ORG_ID": self.org_id,
            "ATTRIBUTE1": ml.get("match_status") or "AUTO",
            "ATTRIBUTE2": ";".join(ml.get("exceptions", [])),
        }
        self._next_line_id += 1
        return line

    def _tax_line(self, invoice_id: int, matched_lines: list[dict[str, Any]],
                  tax_total: Decimal) -> dict[str, Any]:
        next_line_no = (max((m["line_number"] for m in matched_lines), default=0)
                        + 1)
        tax_code = next((m.get("tax_classification_code")
                         for m in matched_lines
                         if m.get("tax_classification_code")), "")
        line = {
            "INVOICE_ID": invoice_id,
            "INVOICE_LINE_ID": self._next_line_id,
            "LINE_NUMBER": next_line_no,
            "LINE_TYPE_LOOKUP_CODE": "TAX",
            "AMOUNT": f"{tax_total:.2f}",
            "DESCRIPTION": "Sales/VAT tax",
            "DIST_CODE_CONCATENATED": "",
            "PO_NUMBER": "",
            "PO_LINE_NUMBER": "",
            "INVENTORY_ITEM_ID": "",
            "ITEM_DESCRIPTION": "",
            "QUANTITY_INVOICED": "",
            "UNIT_PRICE": "",
            "UNIT_OF_MEAS_LOOKUP_CODE": "",
            "TAX_CLASSIFICATION_CODE": tax_code,
            "ORG_ID": self.org_id,
            "ATTRIBUTE1": "TAX",
            "ATTRIBUTE2": "",
        }
        self._next_line_id += 1
        return line

    # ------------------------------------------------------------------
    def write(self, out_dir: str | Path) -> tuple[Path, Path]:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        hdr_path = out / "AP_INVOICES_INTERFACE.csv"
        ln_path = out / "AP_INVOICE_LINES_INTERFACE.csv"

        with open(hdr_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HEADER_COLS)
            w.writeheader()
            w.writerows(self.headers)
        with open(ln_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=LINE_COLS)
            w.writeheader()
            w.writerows(self.lines)
        return hdr_path, ln_path
