"""Syntax Corporation © 2026 — EBS AP PAF — mock repo + end-to-end agent tests."""
from __future__ import annotations

from decimal import Decimal

from ebs_ap_paf.extractor import DeterministicExtractor
from ebs_ap_paf.invoice_agent import InvoiceAgent


def test_mock_repo_supplier_resolution(mock_repo):
    by_tax = mock_repo.get_supplier(tax_id="12-3456789")
    assert by_tax and by_tax["vendor_id"] == 10042
    by_name = mock_repo.get_supplier(vendor_name="acme widgets")
    assert by_name and by_name["vendor_id"] == 10042
    assert mock_repo.get_supplier(vendor_name="No Such Co") is None


def test_mock_repo_po_and_receipts(mock_repo):
    po = mock_repo.get_purchase_order("5001234")
    assert po and len(po["lines"]) == 3
    receipts = mock_repo.get_receipts("5001234")
    assert sum(r["quantity_received"] for r in receipts) == 1001


def test_end_to_end_acme_mock(mock_repo, acme_invoice_text):
    agent = InvoiceAgent(mock_repo, DeterministicExtractor(), org_id=204)
    trace = agent.process(acme_invoice_text)

    assert trace.supplier_match["vendor_id"] == 10042
    assert not trace.duplicate_check
    # line 2 over-bills (540 invoiced vs 500 received = +8% > 5%) -> HOLD
    holds = [lm for lm in trace.line_matches if not lm["auto_approve"]]
    assert any(lm["line_number"] == 2 for lm in holds)
    assert not trace.auto_approved

    # interface rows balance, even with a HOLD line present
    hdr = agent.writer.headers[0]
    line_sum = sum(Decimal(l["AMOUNT"]) for l in agent.writer.lines)
    assert Decimal(hdr["INVOICE_AMOUNT"]) == line_sum

    # QA: well-formed but on HOLD (not loadable, no hard errors)
    rpt = agent.qa_reports[0]
    assert rpt.status == "HOLD"
    assert not rpt.errors


def test_process_extracted_matches_full_process(mock_repo, acme_invoice_text):
    # process() and extract()+process_extracted() must agree (PAF flow path)
    from ebs_ap_paf.extractor import DeterministicExtractor
    ex = DeterministicExtractor()
    extracted = ex.extract(acme_invoice_text)

    a_full = InvoiceAgent(mock_repo, ex)
    t_full = a_full.process(acme_invoice_text)

    a_split = InvoiceAgent(mock_repo, ex)
    t_split = a_split.process_extracted(extracted)

    assert t_full.supplier_match["vendor_id"] == t_split.supplier_match["vendor_id"]
    assert t_full.auto_approved == t_split.auto_approved
    assert a_full.qa_reports[0].status == a_split.qa_reports[0].status
    assert len(a_full.writer.lines) == len(a_split.writer.lines)


def test_mcp_tool_functions_json_serializable(mock_repo, acme_invoice_text):
    # The MCP server's orchestration tools must return JSON-serializable dicts.
    import json
    from ebs_ap_paf.mcp_ebs_server import (
        run_process_invoice, run_match_code_and_validate,
    )
    from ebs_ap_paf.extractor import DeterministicExtractor

    out = run_process_invoice(mock_repo, acme_invoice_text)
    json.dumps(out, default=str)
    assert set(out) == {"trace", "interface_headers", "interface_lines", "qa"}
    assert out["trace"]["supplier_match"]["vendor_id"] == 10042
    assert out["qa"][0]["status"] == "HOLD"  # ACME line 2 over-bills

    extracted = DeterministicExtractor().extract(acme_invoice_text)
    out2 = run_match_code_and_validate(mock_repo, extracted)
    json.dumps(out2, default=str)
    assert len(out2["interface_lines"]) == len(out["interface_lines"])


def test_end_to_end_writes_csvs(mock_repo, acme_invoice_text, tmp_path):
    agent = InvoiceAgent(mock_repo, DeterministicExtractor())
    agent.process(acme_invoice_text)
    hdr_csv, ln_csv = agent.flush(tmp_path)
    assert hdr_csv.exists() and ln_csv.exists()
    assert hdr_csv.read_text().count("\n") >= 2  # header + 1 row
