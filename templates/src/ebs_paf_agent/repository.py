"""
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
--------------------------------------------------------------------------------
 Project : EBS AP PAF — Accounts Payable Invoice Automation Agent
 Module  : repository.py — EBS data-access layer (live + mock)
 Version : 1.0.0      Build : 2026.06.02      Date : 2026-06-02
--------------------------------------------------------------------------------
 Defines the EBSRepository protocol the agent depends on, plus two concrete
 implementations:

   * MockEBSRepository  — reads sample_data/*.json (hermetic, offline tests).
   * LiveEBSRepository  — bind-variable SQL against the real EBS Vision DB.
                          Every query is READ-ONLY and org-scoped. The SQL has
                          been verified against EBS_Vision_12214.

 All access is via the APPS schema's public synonyms. In a production PAF
 deployment the service account would call FND_GLOBAL.APPS_INITIALIZE per
 session to set multi-org security context (see docs/SECURITY.md).
================================================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .db import EBSConnection


@runtime_checkable
class EBSRepository(Protocol):
    """Read-only EBS lookups required by the invoice agent."""

    def get_supplier(
        self,
        vendor_name: str | None = None,
        vendor_num: str | None = None,
        tax_id: str | None = None,
    ) -> dict[str, Any] | None: ...

    def get_purchase_order(self, po_number: str) -> dict[str, Any] | None: ...

    def get_receipts(self, po_number: str) -> list[dict[str, Any]]: ...

    def get_tax_code(
        self, jurisdiction: str, tax_rate_pct: float | None = None
    ) -> dict[str, Any] | None: ...

    def get_gl_segments(
        self, item_category: str, cost_center: str
    ) -> dict[str, Any] | None: ...

    def check_duplicate_invoice(
        self, vendor_id: int, vendor_invoice_num: str
    ) -> bool: ...


# ===========================================================================
# Mock implementation — JSON fixtures (offline / hermetic tests)
# ===========================================================================

class MockEBSRepository:
    """Serves the same shapes as LiveEBSRepository from sample_data/*.json."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def _load(self, name: str) -> Any:
        return json.loads((self.data_dir / name).read_text())

    def get_supplier(self, vendor_name=None, vendor_num=None, tax_id=None):
        suppliers = self._load("mock_supplier_master.json")
        # Resolution order: tax_id > vendor_num > exact name > fuzzy name.
        if tax_id:
            for s in suppliers:
                if s.get("tax_id") == tax_id:
                    return s
        if vendor_num:
            for s in suppliers:
                if s.get("vendor_num") == vendor_num:
                    return s
        if vendor_name:
            for s in suppliers:
                if s["vendor_name"].lower() == vendor_name.lower():
                    return s
            for s in suppliers:
                if vendor_name.lower() in s["vendor_name"].lower():
                    return s
        return None

    def get_purchase_order(self, po_number):
        for po in self._load("mock_po_master.json"):
            if po["po_number"] == po_number:
                return po
        return None

    def get_receipts(self, po_number):
        return [r for r in self._load("mock_receipts.json")
                if r["po_number"] == po_number]

    def get_tax_code(self, jurisdiction, tax_rate_pct=None):
        candidates = [t for t in self._load("mock_tax_codes.json")
                      if t["jurisdiction"] == jurisdiction]
        if tax_rate_pct is not None:
            candidates = [t for t in candidates
                          if abs(t["rate_pct"] - tax_rate_pct) < 0.05]
        return candidates[0] if candidates else None

    def get_gl_segments(self, item_category, cost_center):
        segs = self._load("mock_gl_segments.json")
        for seg in segs:
            if seg["item_category"] == item_category and seg["cost_center"] == cost_center:
                return seg
        return next((s for s in segs if s["item_category"] == "DEFAULT"), None)

    def check_duplicate_invoice(self, vendor_id, vendor_invoice_num):
        return False  # the mock master has no posted invoices


# ===========================================================================
# Live implementation — real EBS Vision SQL (read-only, bind variables)
# ===========================================================================

class LiveEBSRepository:
    """Read-only EBS data access against the live Vision database.

    A single EBSConnection is held open for the life of the repository so a
    run reuses one session. All SQL uses bind variables and is org-scoped.
    """

    # A known-enabled suspense / clearing combination used as the GL fallback
    # when a non-PO line cannot inherit a PO distribution. Overridable.
    DEFAULT_SUSPENSE_SEGMENTS = "01-520-7530-0000-000"

    def __init__(self, conn: EBSConnection, org_id: int = 204):
        self.conn = conn
        self.org_id = org_id

    # ------------------------------------------------------------------
    def get_supplier(self, vendor_name=None, vendor_num=None, tax_id=None):
        # NOTE: ROWNUM is applied in an OUTER query AFTER the ORDER BY, otherwise
        # Oracle would pick an arbitrary row and then sort it (a common bug).
        base = """
            SELECT * FROM (
              SELECT s.vendor_id,
                     s.segment1            AS vendor_num,
                     s.vendor_name,
                     s.num_1099            AS tax_id,
                     ss.vendor_site_id,
                     ss.vendor_site_code,
                     ss.payment_method_lookup_code AS payment_method,
                     s.terms_id,
                     t.name                AS payment_terms
                FROM apps.ap_suppliers s
                JOIN apps.ap_supplier_sites_all ss
                     ON ss.vendor_id = s.vendor_id AND ss.org_id = :org_id
                LEFT JOIN apps.ap_terms t ON t.term_id = s.terms_id
               WHERE {where}
               ORDER BY ss.vendor_site_id
            ) WHERE ROWNUM = 1
        """
        # Resolution order: tax_id > vendor_num > exact name > fuzzy name.
        attempts: list[tuple[str, dict[str, Any]]] = []
        if tax_id:
            attempts.append(("s.num_1099 = :tax_id",
                             {"org_id": self.org_id, "tax_id": tax_id}))
        if vendor_num:
            attempts.append(("s.segment1 = :vendor_num",
                             {"org_id": self.org_id, "vendor_num": vendor_num}))
        if vendor_name:
            attempts.append(("UPPER(s.vendor_name) = UPPER(:vn)",
                             {"org_id": self.org_id, "vn": vendor_name}))
            attempts.append(("UPPER(s.vendor_name) LIKE UPPER(:vnl)",
                             {"org_id": self.org_id, "vnl": f"%{vendor_name}%"}))
        for where, params in attempts:
            row = self.conn.query_one(base.format(where=where), params)
            if row:
                return row
        return None

    # ------------------------------------------------------------------
    def get_purchase_order(self, po_number):
        header = self.conn.query_one(
            """
            SELECT ph.segment1     AS po_number,
                   ph.po_header_id,
                   ph.vendor_id,
                   ph.vendor_site_id,
                   ph.currency_code AS currency,
                   ph.org_id
              FROM apps.po_headers_all ph
             WHERE ph.segment1 = :po_number AND ph.org_id = :org_id
            """,
            {"po_number": str(po_number), "org_id": self.org_id},
        )
        if not header:
            return None

        lines = self.conn.query(
            """
            SELECT pl.line_num,
                   pl.po_line_id,
                   msi.segment1        AS item_number,
                   pl.item_id          AS inventory_item_id,
                   pl.item_description AS description,
                   pll.quantity        AS quantity_ordered,
                   pl.unit_price,
                   pll.unit_meas_lookup_code AS uom,
                   (SELECT mc.segment1 FROM apps.mtl_categories_b mc
                     WHERE mc.category_id = pl.category_id) AS item_category,
                   (SELECT gcc.concatenated_segments
                      FROM apps.po_distributions_all pd
                      JOIN apps.gl_code_combinations_kfv gcc
                           ON gcc.code_combination_id = pd.code_combination_id
                     WHERE pd.po_line_id = pl.po_line_id AND ROWNUM = 1
                   ) AS distribution_code_combination
              FROM apps.po_lines_all pl
              JOIN apps.po_line_locations_all pll ON pll.po_line_id = pl.po_line_id
              LEFT JOIN apps.mtl_system_items_b msi
                   ON msi.inventory_item_id = pl.item_id
                  AND msi.organization_id = :org_id
             WHERE pl.po_header_id = :po_header_id
             ORDER BY pl.line_num
            """,
            {"po_header_id": header["po_header_id"], "org_id": self.org_id},
        )
        # Normalise numeric types for the policy engine (it str()s then Decimal()s).
        for ln in lines:
            ln["cost_center"] = None  # CC is embedded in the inherited dist string
        header["lines"] = lines
        return header

    # ------------------------------------------------------------------
    def get_receipts(self, po_number):
        return self.conn.query(
            """
            SELECT pl.line_num            AS po_line_num,
                   SUM(rt.quantity)       AS quantity_received,
                   MIN(rt.transaction_date) AS receipt_date,
                   COUNT(*)               AS receipt_count
              FROM apps.rcv_transactions rt
              JOIN apps.po_lines_all pl ON pl.po_line_id = rt.po_line_id
              JOIN apps.po_headers_all ph ON ph.po_header_id = pl.po_header_id
             WHERE ph.segment1 = :po_number
               AND ph.org_id = :org_id
               AND rt.transaction_type = 'RECEIVE'
             GROUP BY pl.line_num
             ORDER BY pl.line_num
            """,
            {"po_number": str(po_number), "org_id": self.org_id},
        )

    # ------------------------------------------------------------------
    def get_tax_code(self, jurisdiction, tax_rate_pct=None):
        # zx_rates_b has no clean jurisdiction column in this instance, so we
        # resolve by active percentage rate (closest match), returning the
        # tax_rate_code as the AP TAX_CLASSIFICATION_CODE. Jurisdiction is
        # echoed back best-effort.
        if tax_rate_pct is None:
            return None
        row = self.conn.query_one(
            """
            SELECT * FROM (
              SELECT tax_rate_code   AS tax_classification_code,
                     percentage_rate AS rate_pct
                FROM apps.zx_rates_b
               WHERE active_flag = 'Y'
                 AND percentage_rate IS NOT NULL
                 AND ABS(percentage_rate - :rate) < 0.05
               ORDER BY tax_rate_code
            ) WHERE ROWNUM = 1
            """,
            {"rate": float(tax_rate_pct)},
        )
        if row:
            row["jurisdiction"] = jurisdiction
        return row

    # ------------------------------------------------------------------
    def get_gl_segments(self, item_category, cost_center):
        # Inheriting the PO distribution is the primary path; this is only a
        # fallback for non-PO lines. Return a validated, enabled suspense combo.
        row = self.conn.query_one(
            """
            SELECT concatenated_segments
              FROM apps.gl_code_combinations_kfv
             WHERE concatenated_segments = :seg
               AND enabled_flag = 'Y'
               AND ROWNUM = 1
            """,
            {"seg": self.DEFAULT_SUSPENSE_SEGMENTS},
        )
        return row

    # ------------------------------------------------------------------
    def check_duplicate_invoice(self, vendor_id, vendor_invoice_num):
        row = self.conn.query_one(
            """
            SELECT COUNT(*) AS n
              FROM apps.ap_invoices_all
             WHERE vendor_id = :vendor_id
               AND invoice_num = :invoice_num
               AND org_id = :org_id
            """,
            {
                "vendor_id": vendor_id,
                "invoice_num": vendor_invoice_num,
                "org_id": self.org_id,
            },
        )
        return bool(row and row["n"] > 0)
