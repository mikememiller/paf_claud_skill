"""Syntax Corporation © 2026 — EBS AP PAF — live EBS integration tests.

These require a live connection to EBS_Vision_12214 and are opt-in:
    EBS_RUN_LIVE=1 EBS_PASSWORD=... pytest -m live
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from conftest import requires_live  # type: ignore

pytestmark = pytest.mark.live


@pytest.fixture
def live_conn(live_settings):
    from ebs_ap_paf.db import EBSConnection
    with EBSConnection(live_settings, interactive=False) as conn:
        yield conn


@pytest.fixture
def live_repo(live_conn, live_settings):
    from ebs_ap_paf.repository import LiveEBSRepository
    return LiveEBSRepository(live_conn, org_id=live_settings.org_id)


@requires_live
def test_dialtone(live_settings):
    from ebs_ap_paf.db import dialtone
    assert dialtone(live_settings, interactive=False) is True


@requires_live
def test_get_supplier_advanced_network(live_repo):
    s = live_repo.get_supplier(vendor_name="Advanced Network Devices")
    assert s is not None
    assert s["vendor_id"] == 21
    assert "Advanced Network Devices" in s["vendor_name"]
    assert s["vendor_site_id"] is not None


@requires_live
def test_get_purchase_order_3495(live_repo):
    po = live_repo.get_purchase_order("3495")
    assert po is not None
    assert po["vendor_id"] == 21
    assert len(po["lines"]) == 4
    items = {l["item_number"] for l in po["lines"]}
    assert {"KB15138", "CM08512", "CM41420", "CM41520"} <= items
    for l in po["lines"]:
        assert l["distribution_code_combination"] == "01-520-7530-0000-000"


@requires_live
def test_get_receipts_3495_fully_received(live_repo):
    receipts = live_repo.get_receipts("3495")
    by_line = {r["po_line_num"]: r["quantity_received"] for r in receipts}
    assert by_line == {1: 500, 2: 500, 3: 500, 4: 500}


@requires_live
def test_duplicate_check_behaviour(live_repo):
    # a clearly-fake invoice number must not be flagged a duplicate
    assert live_repo.check_duplicate_invoice(21, "AND-2026-3495-A") is False


@requires_live
def test_gl_combination_fallback_enabled(live_repo):
    seg = live_repo.get_gl_segments("MISC", "520")
    assert seg and seg["concatenated_segments"] == "01-520-7530-0000-000"


@requires_live
def test_loader_round_trip_inserts_and_purges(live_conn, live_repo,
                                              and_invoice_text, live_settings):
    """Insert a PO-3495 batch into the AP interface tables, verify it persisted,
    then purge it — leaving the database exactly as it was."""
    from ebs_ap_paf.extractor import DeterministicExtractor
    from ebs_ap_paf.invoice_agent import InvoiceAgent
    from ebs_ap_paf.interface_loader import load_invoices

    agent = InvoiceAgent(live_repo, DeterministicExtractor(),
                         org_id=live_settings.org_id, qa_conn=live_conn)
    agent.process(and_invoice_text)
    g = agent.writer.headers[0]["GROUP_ID"]
    idlist = ",".join(str(h["INVOICE_ID"]) for h in agent.writer.headers)

    def counts():
        h = live_conn.query_one(
            "SELECT COUNT(*) n FROM apps.ap_invoices_interface WHERE group_id=:g",
            {"g": g})["n"]
        l = live_conn.query_one(
            f"SELECT COUNT(*) n FROM apps.ap_invoice_lines_interface "
            f"WHERE invoice_id IN ({idlist})")["n"]
        return h, l

    assert counts() == (0, 0)
    try:
        res = load_invoices(live_conn, agent.writer.headers, agent.writer.lines,
                            agent.qa_reports, confirm=True)
        assert res == {"headers": 1, "lines": 4, "skipped": 0}
        assert counts() == (1, 4)
    finally:
        with live_conn._cursor() as cur:
            cur.execute(f"DELETE FROM apps.ap_invoice_lines_interface "
                        f"WHERE invoice_id IN ({idlist})")
            cur.execute("DELETE FROM apps.ap_invoices_interface "
                        "WHERE group_id=:g AND source='EBS_AGENT_PAF'", {"g": g})
            live_conn.connection.commit()
    assert counts() == (0, 0)


@requires_live
def test_loader_skips_non_loadable(live_conn, live_repo, and_invoice_text,
                                   live_settings):
    """A held (out-of-tolerance) invoice must never reach the interface tables."""
    from ebs_ap_paf.extractor import DeterministicExtractor
    from ebs_ap_paf.invoice_agent import InvoiceAgent
    from ebs_ap_paf.interface_loader import load_invoices

    bad = and_invoice_text.replace("475.00   237,500.00", "600.00   300,000.00") \
                          .replace("632,500.00", "695,000.00")
    agent = InvoiceAgent(live_repo, DeterministicExtractor(),
                         org_id=live_settings.org_id, qa_conn=live_conn)
    agent.process(bad)
    assert agent.qa_reports[0].status == "HOLD"
    res = load_invoices(live_conn, agent.writer.headers, agent.writer.lines,
                        agent.qa_reports, confirm=True)
    assert res["headers"] == 0 and res["skipped"] == 1


@requires_live
def test_end_to_end_live_po3495(live_conn, live_repo, and_invoice_text,
                                live_settings):
    from ebs_ap_paf.extractor import DeterministicExtractor
    from ebs_ap_paf.invoice_agent import InvoiceAgent

    agent = InvoiceAgent(live_repo, DeterministicExtractor(),
                         org_id=live_settings.org_id, qa_conn=live_conn)
    trace = agent.process(and_invoice_text)

    assert trace.supplier_match["vendor_id"] == 21
    assert trace.auto_approved is True            # clean 3-way match
    assert all(lm["auto_approve"] for lm in trace.line_matches)

    rpt = agent.qa_reports[0]
    assert rpt.status == "PASS", rpt.to_dict()
    assert rpt.loadable

    hdr = agent.writer.headers[0]
    line_sum = sum(Decimal(l["AMOUNT"]) for l in agent.writer.lines)
    assert Decimal(hdr["INVOICE_AMOUNT"]) == line_sum == Decimal("632500.00")
