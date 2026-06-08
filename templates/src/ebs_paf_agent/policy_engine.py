"""
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
--------------------------------------------------------------------------------
 Project : EBS AP PAF — Accounts Payable Invoice Automation Agent
 Module  : policy_engine.py — 3-way match, tolerance, GL & tax coding
 Version : 1.0.0      Build : 2026.06.02      Date : 2026-06-02
--------------------------------------------------------------------------------
 The deterministic policy layer between the (probabilistic) extractor and the
 EBS interface tables. Keeping policy OUT of the LLM is what makes the agent
 auditable. Anything outside tolerance flags the line for manual approval (AME)
 — the interface row is still written but the load is held.

 Tolerances would normally come from PO_TOLERANCES / org config; here they are
 explicit module constants.
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable

PRICE_TOLERANCE_PCT = Decimal("2.0")    # invoice unit price vs PO unit price
QTY_TOLERANCE_PCT = Decimal("5.0")      # invoice qty vs received qty
LINE_AMOUNT_TOLERANCE_USD = Decimal("25.00")  # extended-amount tolerance / line


@dataclass
class MatchResult:
    line_number: int
    matched: bool
    auto_approve: bool
    exceptions: list[str] = field(default_factory=list)
    po_unit_price: Decimal | None = None
    invoice_unit_price: Decimal | None = None
    qty_received: Decimal | None = None
    qty_invoiced: Decimal | None = None


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def three_way_match(invoice_line: dict[str, Any],
                    po: dict[str, Any],
                    receipts: list[dict[str, Any]]) -> MatchResult:
    """Match one invoice line against PO + receipts.

    auto_approve is True only if every check passes inside tolerance.
    """
    result = MatchResult(line_number=invoice_line["line_number"],
                         matched=False, auto_approve=False)

    # --- 1. find the matching PO line -----------------------------------
    po_line = next(
        (l for l in po["lines"]
         if l["line_num"] == invoice_line.get("po_line_num")),
        None,
    )
    if po_line is None:  # fall back to item-number match
        po_line = next(
            (l for l in po["lines"]
             if l.get("item_number") == invoice_line.get("item_number")),
            None,
        )
    if po_line is None:
        result.exceptions.append("NO_MATCHING_PO_LINE")
        return result

    # --- 2. price check --------------------------------------------------
    # EBS-style dual tolerance: a price variance is only held when it breaches
    # BOTH the percentage tolerance AND a material absolute-dollar impact. The
    # dollar floor stops trivial cent-level variances on cheap items from
    # holding the invoice, while still catching real over-charges.
    inv_price = _d(invoice_line["unit_price"])
    po_price = _d(po_line["unit_price"])
    qty_invoiced = _d(invoice_line["quantity"])
    result.invoice_unit_price = inv_price
    result.po_unit_price = po_price

    if po_price > 0:
        price_var_pct = abs(inv_price - po_price) / po_price * 100
        dollar_impact = abs(inv_price - po_price) * qty_invoiced
        if (price_var_pct > PRICE_TOLERANCE_PCT
                and dollar_impact > LINE_AMOUNT_TOLERANCE_USD):
            result.exceptions.append(
                f"PRICE_VARIANCE_{price_var_pct:.2f}PCT_${dollar_impact:.2f}")

    # --- 3. quantity check (vs received, not vs ordered) -----------------
    qty_received = sum(
        (_d(r["quantity_received"]) for r in receipts
         if r["po_line_num"] == po_line["line_num"]),
        Decimal("0"),
    )
    result.qty_received = qty_received
    result.qty_invoiced = qty_invoiced

    if qty_received == 0:
        result.exceptions.append("NO_RECEIPT_RECORDED")
    elif qty_invoiced > qty_received:
        over_pct = (qty_invoiced - qty_received) / qty_received * 100
        over_dollar = (qty_invoiced - qty_received) * po_price
        if (over_pct > QTY_TOLERANCE_PCT
                and over_dollar > LINE_AMOUNT_TOLERANCE_USD):
            result.exceptions.append(
                f"OVER_BILLED_{over_pct:.2f}PCT_${over_dollar:.2f}")

    result.matched = True
    result.auto_approve = len(result.exceptions) == 0
    return result


# ---------------------------------------------------------------------------
# GL & tax coding
# ---------------------------------------------------------------------------

def code_distribution(po_line: dict[str, Any],
                      gl_lookup_fn: Callable[..., dict[str, Any] | None],
                      cost_center_fallback: str = "1000") -> dict[str, Any]:
    """Determine the GL distribution for a line.

    EBS rule: inherit the PO line's distribution if present (preserves project /
    task / award coding); otherwise resolve from item category + cost center.
    """
    if po_line.get("distribution_code_combination"):
        return {
            "dist_code_concatenated": po_line["distribution_code_combination"],
            "source": "PO_DISTRIBUTION",
        }
    seg = gl_lookup_fn(
        item_category=po_line.get("item_category", "DEFAULT"),
        cost_center=po_line.get("cost_center") or cost_center_fallback,
    )
    if not seg:
        return {"dist_code_concatenated": None, "source": "UNRESOLVED"}
    return {
        "dist_code_concatenated": seg["concatenated_segments"],
        "source": "DERIVED_FROM_CATEGORY",
    }


def code_tax(invoice_line: dict[str, Any],
             jurisdiction: str,
             tax_lookup_fn: Callable[..., dict[str, Any] | None]) -> str | None:
    """Resolve the AP tax classification code for a line."""
    declared_rate = invoice_line.get("tax_rate_pct")
    code = tax_lookup_fn(jurisdiction=jurisdiction, tax_rate_pct=declared_rate)
    return code["tax_classification_code"] if code else None
