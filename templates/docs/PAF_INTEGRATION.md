<!-- Syntax Corporation © 2026 — EBS AP PAF · v1.0.0 · 2026-06-02 -->

# Importing the agent into Oracle Private Agent Factory (PAF)

PAF builds agents from the **Open Agent Spec** (open source) and connects to
tools via **MCP servers** and OpenAPI. This project ships both halves:

| Artifact | Role |
|----------|------|
| [`paf/ebs_ap_mcp_server.json`](../paf/ebs_ap_mcp_server.json) | Registers our EBS tools as an **MCP Server** in PAF |
| [`paf/ebs_ap_agent.agentspec.yaml`](../paf/ebs_ap_agent.agentspec.yaml) | The **Open Agent Spec** agent (readable reference) |
| [`paf/build_agentspec.py`](../paf/build_agentspec.py) | Generates a **version-exact** spec via the PyAgentSpec SDK |

> **Version-exact spec:** the `.yaml` above is a readable reference. To emit a
> spec that matches your PAF's agent-spec release, run
> `pip install pyagentspec && python paf/build_agentspec.py` in the PAF
> environment — it writes `paf/ebs_ap_agent.generated.yaml`. The MCP tool
> contracts are stable either way.
>
> The MCP tool surface (`process_invoice`, `match_code_and_validate`, and the
> six EBS reads) has been **verified live against EBS Vision** (PO 3495 → QA
> PASS, balanced $632,500.00, JSON-serializable results).

The deterministic logic (3-way match, tolerances, GL/tax coding, QA gate) stays
in our code behind the MCP tools, so PAF only does the LLM **extraction** — the
auditable parts remain reproducible.

## Two ways to run it on PAF

**A. Import the Agent Spec (fastest).**
1. Deploy this package where PAF can launch it (sidecar container on the 26ai
   Autonomous DB VM is the Oracle-recommended spot). Install with the MCP extra:
   `pip install -e ".[mcp]"`.
2. In PAF, add a **tool source → MCP Server** using `paf/ebs_ap_mcp_server.json`
   (command `python -m ebs_ap_paf.mcp_ebs_server`, transport stdio). Supply
   `EBS_PASSWORD` from PAF's secret store.
3. In PAF, **Import Agent Spec** and select `paf/ebs_ap_agent.agentspec.yaml`.
   Pick an enabled `llm_config` model (OCI Gen AI, etc.).
4. Map the agent input `invoice_text` to your document/email source and run.

**B. Rebuild on the no-code canvas (full PAF-native flow).**
Register the same MCP server, then drag: **Document/CSV input → LLM extract node
→ MCP tool node `match_code_and_validate` → Output node** (CSV / interface).
Add an approval node (AME) on `qa.status == "HOLD"`. The single
`process_invoice` tool can also do extract+match+QA in one call for a minimal
flow.

## Tools the MCP server exposes

Granular EBS reads: `get_supplier`, `get_purchase_order`, `get_receipts`,
`get_tax_code`, `get_gl_segments`, `check_duplicate_invoice`.
Orchestration: `match_code_and_validate(extracted)` and
`process_invoice(invoice_text)` — each returns the interface rows, the QA report
and the explainability trace.

## Production notes

- **Security:** the DB service account should call `FND_GLOBAL.APPS_INITIALIZE`
  per session for multi-org context; supply `EBS_PASSWORD` via PAF secrets, never
  plaintext. See [SECURITY.md](SECURITY.md).
- **Loading to EBS:** keep the read-only + CSV path and let the standard
  *Payables Open Interface Import* load the files (preserves AP controls). The
  optional direct interface INSERT is also available if you prefer staging.
- **Portability:** because it's Open Agent Spec, the same definition runs on the
  WayFlow runtime and can be exported to / imported from LangGraph, CrewAI, etc.

## Honest caveat

Agent Spec is evolving and PAF's importer may use slightly different field names
than this YAML (e.g. `llm_config` provider keys, tool reference style). The MCP
server and tool contracts are stable; if the importer rejects a field, align the
spec to your PAF/agent-spec release — the tool wiring does not change. Verify the
agent end-to-end with `sample_data/invoice_advanced_network_3495.txt` (PO 3495),
which produces a clean PASS.

Sources: [Open Agent Spec](https://github.com/oracle/agent-spec) ·
[PAF announcement](https://blogs.oracle.com/database/introducing-private-agent-factory-unlocking-the-agentic-ai-potential-in-enterprises-with-oracle-ai-database-26ai) ·
[Agent Factory](https://www.oracle.com/database/agent-factory/)
