"""
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
--------------------------------------------------------------------------------
 Project : EBS AP PAF — Accounts Payable Invoice Automation Agent
 Module  : mcp_ebs_server.py — MCP server exposing read-only EBS lookups
 Version : 1.0.0      Build : 2026.06.02      Date : 2026-06-02
--------------------------------------------------------------------------------
 Exposes the EBSRepository methods as MCP tools so a Private-Agent-Factory agent
 can call them over stdio. The tool *signatures* are stable; the backend is
 chosen by EBS_BACKEND (live | mock). In production this runs as a sidecar
 container on the 26ai Autonomous DB VM with a service account that calls
 FND_GLOBAL.APPS_INITIALIZE before each query.

 Requires the optional `mcp` package:  pip install "ebs-ap-paf[mcp]"
================================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings
from .repository import EBSRepository, LiveEBSRepository, MockEBSRepository

_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


def build_repository(settings: Settings | None = None) -> EBSRepository:
    """Construct the repository backend selected by settings/env."""
    settings = settings or Settings.resolve()
    if settings.backend == "live":
        from .db import EBSConnection
        conn = EBSConnection(settings, interactive=True).__enter__()
        return LiveEBSRepository(conn, org_id=settings.org_id)
    return MockEBSRepository(_SAMPLE_DIR)


# ---------------------------------------------------------------------------
# Tool implementations — module-level so they are importable and testable
# without the optional `mcp` transport package. main() simply wraps these.
# ---------------------------------------------------------------------------

def _agent_for(repo: EBSRepository):
    from .extractor import DeterministicExtractor
    from .invoice_agent import InvoiceAgent
    return InvoiceAgent(repo, DeterministicExtractor(),
                        org_id=getattr(repo, "org_id", 204))


def _result(agent, trace) -> dict[str, Any]:
    return {
        "trace": trace.to_dict(),
        "interface_headers": agent.writer.headers,
        "interface_lines": agent.writer.lines,
        "qa": [r.to_dict() for r in agent.qa_reports],
    }


def run_match_code_and_validate(repo: EBSRepository, extracted: dict) -> dict[str, Any]:
    """3-way match + GL/tax coding + QA over an already-extracted invoice."""
    agent = _agent_for(repo)
    return _result(agent, agent.process_extracted(extracted))


def run_process_invoice(repo: EBSRepository, invoice_text: str) -> dict[str, Any]:
    """End-to-end: extract invoice text, then match/code/validate."""
    agent = _agent_for(repo)
    return _result(agent, agent.process(invoice_text))


def main() -> None:  # pragma: no cover - requires mcp + a transport
    from mcp.server.fastmcp import FastMCP

    repo = build_repository()
    mcp = FastMCP("ebs-ap-server")

    @mcp.tool()
    def get_supplier(vendor_name: str | None = None,
                     vendor_num: str | None = None,
                     tax_id: str | None = None) -> dict | None:
        """Look up a supplier (AP_SUPPLIERS / AP_SUPPLIER_SITES_ALL)."""
        return repo.get_supplier(vendor_name, vendor_num, tax_id)

    @mcp.tool()
    def get_purchase_order(po_number: str) -> dict | None:
        """PO header + lines + inherited distributions for 3-way match."""
        return repo.get_purchase_order(po_number)

    @mcp.tool()
    def get_receipts(po_number: str) -> list[dict]:
        """Quantity received per PO line (RCV_TRANSACTIONS)."""
        return repo.get_receipts(po_number)

    @mcp.tool()
    def get_tax_code(jurisdiction: str,
                     tax_rate_pct: float | None = None) -> dict | None:
        """Resolve an AP tax classification code (ZX_RATES_B)."""
        return repo.get_tax_code(jurisdiction, tax_rate_pct)

    @mcp.tool()
    def get_gl_segments(item_category: str, cost_center: str) -> dict | None:
        """Resolve a GL distribution combination for coding."""
        return repo.get_gl_segments(item_category, cost_center)

    @mcp.tool()
    def check_duplicate_invoice(vendor_id: int,
                                vendor_invoice_num: str) -> bool:
        """Flag duplicates against AP_INVOICES_ALL."""
        return repo.check_duplicate_invoice(vendor_id, vendor_invoice_num)

    # --- higher-level orchestration tools (ideal for a PAF flow) -----------
    @mcp.tool()
    def match_code_and_validate(extracted: dict) -> dict:
        """Given an already-extracted invoice (e.g. from a PAF LLM node), run
        3-way match + GL/tax coding + the QA gate against live EBS and return
        the agent trace, the AP interface rows, and the QA report. Does not
        write any files or rows."""
        return run_match_code_and_validate(repo, extracted)

    @mcp.tool()
    def process_invoice(invoice_text: str) -> dict:
        """End-to-end: extract the invoice text, match/code/validate against
        live EBS, and return the trace + interface rows + QA report."""
        return run_process_invoice(repo, invoice_text)

    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
