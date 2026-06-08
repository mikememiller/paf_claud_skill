"""Syntax Corporation © 2026 — EBS AP PAF — extractor tests."""
from __future__ import annotations

import pytest

from ebs_ap_paf.extractor import (
    DeterministicExtractor,
    ExtractionError,
    make_extractor,
)


def test_parses_acme_invoice(acme_invoice_text):
    out = DeterministicExtractor().extract(acme_invoice_text)
    assert out["invoice_number"] == "INV-2026-04-7781"
    assert out["invoice_date"] == "2026-05-02"
    assert out["po_number"] == "5001234"
    assert out["currency"] == "USD"
    assert out["vendor_tax_id"] == "12-3456789"
    assert out["vendor_name"].lower().startswith("acme widgets")
    assert len(out["lines"]) == 3
    # MA sales tax detected
    assert out["jurisdiction"] == "US-MA"
    assert out["tax_total"] == pytest.approx(515.94, abs=0.01)
    assert out["lines"][0]["tax_rate_pct"] == pytest.approx(6.25)


def test_line_arithmetic_parsed(acme_invoice_text):
    out = DeterministicExtractor().extract(acme_invoice_text)
    line0 = out["lines"][0]
    assert line0["quantity"] == 500
    assert line0["unit_price"] == 12.5
    assert line0["amount"] == 6250.0


def test_parses_real_po_invoice(and_invoice_text):
    out = DeterministicExtractor().extract(and_invoice_text)
    assert out["po_number"] == "3495"
    assert out["currency"] == "USD"
    assert len(out["lines"]) == 4
    assert out["subtotal"] == pytest.approx(632500.0)
    assert out["total"] == pytest.approx(632500.0)
    assert out["tax_total"] == 0.0
    # line→PO line mapping convention
    assert [l["po_line_num"] for l in out["lines"]] == [1, 2, 3, 4]


def test_po_not_misdetected_inside_invoice_number():
    # Regression: "PO" inside an invoice number (AND-NONPO-1) must NOT be
    # parsed as a PO number; an unlabelled invoice has po_number = None.
    text = (
        "ACME CO\n"
        "Invoice Number: AND-NONPO-1\n"
        "Invoice Date: 2026-05-20\n"
        "Currency: USD\n"
        "  1   SVC  Consulting   10   150.00   1,500.00\n"
        "Subtotal: 1,500.00\n"
        "TOTAL DUE: 1,500.00\n"
    )
    out = DeterministicExtractor().extract(text)
    assert out["po_number"] is None


def test_po_box_not_detected_as_po():
    text = (
        "ACME CO\n"
        "PO BOX 4567 Boston MA\n"
        "Invoice Number: INV-9\n"
        "Invoice Date: 2026-05-20\n"
        "  1   SVC  Consulting   1   10.00   10.00\n"
        "TOTAL DUE: 10.00\n"
    )
    out = DeterministicExtractor().extract(text)
    assert out["po_number"] is None


def test_missing_invoice_number_raises():
    with pytest.raises(ExtractionError):
        DeterministicExtractor().extract("no fields here\nInvoice Date: 2026-01-01")


def test_factory_default_is_deterministic():
    assert isinstance(make_extractor("deterministic"), DeterministicExtractor)


def test_factory_auto_without_key_falls_back(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(make_extractor("auto"), DeterministicExtractor)
