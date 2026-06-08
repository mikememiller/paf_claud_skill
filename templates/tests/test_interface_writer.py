"""Syntax Corporation © 2026 — EBS AP PAF — interface writer tests."""
from __future__ import annotations

import csv
from decimal import Decimal

from ebs_ap_paf.interface_writer import HEADER_COLS, LINE_COLS, EBSInterfaceWriter


def _supplier():
    return {"vendor_id": 10042, "vendor_num": "V-100042",
            "vendor_name": "Acme Widgets, Inc.", "vendor_site_id": 28011,
            "vendor_site_code": "BOSTON-MAIN", "payment_terms": "NET 30",
            "terms_id": 10001, "payment_method": "EFT"}


def _extracted(tax_total=515.94, total=8770.94):
    return {"invoice_number": "INV-1", "invoice_date": "2026-05-02",
            "currency": "USD", "po_number": "5001234",
            "tax_total": tax_total, "total": total}


def _matched_lines():
    return [
        {"line_number": 1, "description": "XP9000", "amount": 6250.0,
         "quantity": 500, "unit_price": 12.5, "uom": "EA",
         "dist_code_concatenated": "01-5500-7421-000-000",
         "tax_classification_code": "MA_SALES_625", "po_line_num": 1,
         "inventory_item_id": 88142, "match_status": "AUTO", "exceptions": []},
        {"line_number": 2, "description": "Case", "amount": 1755.0,
         "quantity": 540, "unit_price": 3.25, "uom": "EA",
         "dist_code_concatenated": "01-5500-7421-000-000",
         "tax_classification_code": "MA_SALES_625", "po_line_num": 2,
         "inventory_item_id": 88143, "match_status": "AUTO", "exceptions": []},
        {"line_number": 3, "description": "Freight", "amount": 250.0,
         "quantity": 1, "unit_price": 250.0, "uom": "EA",
         "dist_code_concatenated": "01-5500-7910-000-000",
         "tax_classification_code": None, "po_line_num": 3,
         "inventory_item_id": None, "match_status": "AUTO", "exceptions": []},
    ]


def test_header_balances_with_tax_line():
    w = EBSInterfaceWriter()
    w.add_invoice(_extracted(), _supplier(), _matched_lines(), "AGT-X", 0.99)
    hdr = w.headers[0]
    line_sum = sum(Decimal(l["AMOUNT"]) for l in w.lines)
    # item subtotal 8255 + tax 515.94 = 8770.94
    assert Decimal(hdr["INVOICE_AMOUNT"]) == Decimal("8770.94")
    assert line_sum == Decimal(hdr["INVOICE_AMOUNT"])


def test_tax_line_emitted():
    w = EBSInterfaceWriter()
    w.add_invoice(_extracted(), _supplier(), _matched_lines(), "AGT-X", 0.99)
    tax_lines = [l for l in w.lines if l["LINE_TYPE_LOOKUP_CODE"] == "TAX"]
    assert len(tax_lines) == 1
    assert Decimal(tax_lines[0]["AMOUNT"]) == Decimal("515.94")
    assert tax_lines[0]["LINE_NUMBER"] == 4  # after the 3 item lines


def test_no_tax_line_when_zero_tax():
    w = EBSInterfaceWriter()
    w.add_invoice(_extracted(tax_total=0, total=8255.0), _supplier(),
                  _matched_lines(), "AGT-X", 0.99)
    assert not [l for l in w.lines if l["LINE_TYPE_LOOKUP_CODE"] == "TAX"]
    assert Decimal(w.headers[0]["INVOICE_AMOUNT"]) == Decimal("8255.00")


def test_csv_column_order(tmp_path):
    w = EBSInterfaceWriter()
    w.add_invoice(_extracted(), _supplier(), _matched_lines(), "AGT-X", 0.99)
    hdr_csv, ln_csv = w.write(tmp_path)
    with open(hdr_csv) as f:
        assert next(csv.reader(f)) == HEADER_COLS
    with open(ln_csv) as f:
        assert next(csv.reader(f)) == LINE_COLS


def test_foreign_currency_rate_type(tmp_path):
    w = EBSInterfaceWriter()
    ex = _extracted(tax_total=0, total=6250.0)
    ex["currency"] = "EUR"
    w.add_invoice(ex, _supplier(), _matched_lines()[:1], "AGT-X", 0.99)
    hdr = w.headers[0]
    assert hdr["INVOICE_CURRENCY_CODE"] == "EUR"
    assert hdr["EXCHANGE_RATE_TYPE"] == "Corporate"
    assert hdr["EXCHANGE_DATE"] == "2026-05-02"
