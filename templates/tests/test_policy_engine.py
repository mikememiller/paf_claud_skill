"""Syntax Corporation © 2026 — EBS AP PAF — policy engine tests."""
from __future__ import annotations

from ebs_ap_paf.policy_engine import (
    code_distribution,
    code_tax,
    three_way_match,
)


def _po(unit_price=12.50, line_num=1, item="WGT", dist="01-5500-7421-000-000"):
    return {"po_number": "PO1", "lines": [{
        "line_num": line_num, "item_number": item, "unit_price": unit_price,
        "inventory_item_id": 1, "item_category": "ELECTRONICS",
        "cost_center": "5500", "distribution_code_combination": dist,
    }]}


def _line(qty=500, unit=12.50, po_line=1, item="WGT"):
    return {"line_number": 1, "po_line_num": po_line, "item_number": item,
            "quantity": qty, "unit_price": unit, "amount": qty * unit}


def _receipts(qty=500, po_line=1):
    return [{"po_line_num": po_line, "quantity_received": qty}]


def test_clean_match_auto_approves():
    r = three_way_match(_line(), _po(), _receipts())
    assert r.matched and r.auto_approve
    assert r.exceptions == []


def test_price_variance_over_tolerance_holds():
    # 12.50 -> 13.00 is +4% > 2% tolerance
    r = three_way_match(_line(unit=13.00), _po(unit_price=12.50), _receipts())
    assert not r.auto_approve
    assert any(e.startswith("PRICE_VARIANCE") for e in r.exceptions)


def test_price_variance_within_tolerance_passes():
    # +1.6% < 2%
    r = three_way_match(_line(unit=12.70), _po(unit_price=12.50), _receipts())
    assert r.auto_approve


def test_over_billing_quantity_holds():
    # invoiced 600 vs received 500 = +20% > 5%
    r = three_way_match(_line(qty=600), _po(), _receipts(qty=500))
    assert not r.auto_approve
    assert any(e.startswith("OVER_BILLED") for e in r.exceptions)


def test_qty_within_tolerance_passes():
    # invoiced 520 vs received 500 = +4% < 5%; same price -> within $ tolerance
    r = three_way_match(_line(qty=520), _po(), _receipts(qty=500))
    assert r.auto_approve


def test_no_receipt_holds():
    r = three_way_match(_line(), _po(), _receipts(qty=0))
    assert not r.auto_approve
    assert "NO_RECEIPT_RECORDED" in r.exceptions


def test_no_matching_po_line():
    r = three_way_match(_line(po_line=9, item="ZZZ"), _po(), _receipts())
    assert not r.matched
    assert "NO_MATCHING_PO_LINE" in r.exceptions


def test_falls_back_to_item_number_match():
    line = _line(po_line=None, item="WGT")
    r = three_way_match(line, _po(item="WGT"), _receipts())
    assert r.matched and r.auto_approve


def test_amount_tolerance_no_false_positive_when_price_clean():
    # big extended amount but price & qty match exactly -> no LINE_AMOUNT_VARIANCE
    r = three_way_match(_line(qty=500, unit=400.0), _po(unit_price=400.0),
                        _receipts(qty=500))
    assert r.auto_approve
    assert not any("LINE_AMOUNT_VARIANCE" in e for e in r.exceptions)


def test_code_distribution_inherits_po():
    out = code_distribution(_po()["lines"][0], lambda **k: None)
    assert out["source"] == "PO_DISTRIBUTION"
    assert out["dist_code_concatenated"] == "01-5500-7421-000-000"


def test_code_distribution_derives_when_no_po_dist():
    po_line = {"item_category": "OFFICE", "cost_center": "1000",
               "distribution_code_combination": None}
    out = code_distribution(
        po_line, lambda **k: {"concatenated_segments": "01-1000-7400-000-000"})
    assert out["source"] == "DERIVED_FROM_CATEGORY"


def test_code_tax_resolves():
    code = code_tax({"tax_rate_pct": 6.25}, "US-MA",
                    lambda **k: {"tax_classification_code": "MA_SALES_625"})
    assert code == "MA_SALES_625"
