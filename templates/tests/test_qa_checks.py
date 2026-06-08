"""Syntax Corporation © 2026 — EBS AP PAF — QA gate tests."""
from __future__ import annotations

from ebs_ap_paf.qa_checks import validate_invoice


def _header(amount="8770.94"):
    return {"INVOICE_NUM": "INV-1", "INVOICE_DATE": "2026-05-02",
            "VENDOR_ID": 10042, "VENDOR_SITE_ID": 28011,
            "INVOICE_AMOUNT": amount, "INVOICE_TYPE_LOOKUP_CODE": "STANDARD",
            "ORG_ID": 204, "SOURCE": "EBS_AGENT_PAF", "GROUP_ID": "G1"}


def _lines():
    return [
        {"LINE_NUMBER": 1, "LINE_TYPE_LOOKUP_CODE": "ITEM", "AMOUNT": "6250.00",
         "QUANTITY_INVOICED": 500, "UNIT_PRICE": 12.5, "ORG_ID": 204},
        {"LINE_NUMBER": 2, "LINE_TYPE_LOOKUP_CODE": "ITEM", "AMOUNT": "2005.00",
         "QUANTITY_INVOICED": 1, "UNIT_PRICE": 2005.0, "ORG_ID": 204},
        {"LINE_NUMBER": 3, "LINE_TYPE_LOOKUP_CODE": "TAX", "AMOUNT": "515.94",
         "QUANTITY_INVOICED": "", "UNIT_PRICE": "", "ORG_ID": 204},
    ]


def _matched(status="AUTO"):
    return [{"line_number": 1, "match_status": status, "exceptions": []}]


def test_clean_invoice_passes():
    rpt = validate_invoice(_header(), _lines(), {"total": 8770.94}, _matched())
    assert rpt.status == "PASS"
    assert rpt.loadable


def test_unbalanced_header_fails():
    rpt = validate_invoice(_header(amount="9999.99"), _lines(),
                           {"total": 9999.99}, _matched())
    assert rpt.status == "FAIL"
    assert not rpt.loadable
    assert any(f.check == "header.balances_to_lines" for f in rpt.errors)


def test_line_arithmetic_defect_fails():
    bad = _lines()
    bad[0]["AMOUNT"] = "6000.00"  # 500*12.5 = 6250, not 6000
    # rebalance header so only the arithmetic check trips
    rpt = validate_invoice(_header(amount="8520.94"), bad, {"total": 8520.94},
                           _matched())
    assert not rpt.loadable
    assert any("arithmetic" in f.check for f in rpt.errors)


def test_missing_required_field_fails():
    h = _header()
    h["VENDOR_ID"] = ""
    rpt = validate_invoice(h, _lines(), {"total": 8770.94}, _matched())
    assert not rpt.loadable
    assert any(f.check == "header.VENDOR_ID" for f in rpt.errors)


def test_bad_line_type_fails():
    bad = _lines()
    bad[0]["LINE_TYPE_LOOKUP_CODE"] = "BOGUS"
    rpt = validate_invoice(_header(), bad, {"total": 8770.94}, _matched())
    assert not rpt.loadable


def test_hold_match_status_blocks_load_but_not_error():
    rpt = validate_invoice(_header(), _lines(), {"total": 8770.94},
                           _matched(status="HOLD"))
    assert rpt.status == "HOLD"
    assert not rpt.loadable
    assert not rpt.errors  # it's a HOLD, not an ERROR


def test_declared_total_mismatch_is_warning_only():
    rpt = validate_invoice(_header(), _lines(), {"total": 9999.0}, _matched())
    # WARN does not block loading
    assert rpt.loadable
    assert any(f.check == "header.reconciles_declared_total" and not f.passed
               for f in rpt.findings)
