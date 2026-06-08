<!--
 Syntax Corporation © 2026 — EBS AP PAF
 Version 1.0.0  ·  Build 2026.06.02  ·  2026-06-02
-->

# EBS AP PAF — Accounts Payable Invoice Automation Agent

A Private-Agent-Factory (PAF)-style agent for Oracle E-Business Suite that turns
supplier invoices into **balanced, QA-validated AP Open Interface files**, ready
for the standard *Payables Open Interface Import*. It runs against the **live EBS
Vision database** and is designed so the whole pipeline executes end-to-end with
**only the database as a live dependency** — no API key or OCR service required.

> Same architecture as Oracle's *"Simplifying Contract Renewals: an AI Agent for
> EBS with Private Agent Factory"* blog — pointed at the much larger AP revenue
> pool. The agent **never writes to the base AP tables**; it produces interface
> files (or, optionally and explicitly, stages interface rows), preserving every
> existing AP control, approval and audit trail.

## Pipeline

```
 supplier invoice ──▶ extract ──▶ EBS lookups ──▶ 3-way match + GL/tax coding
   (text/PDF)          │            (repository)        (policy engine)
                       │                                      │
                       ▼                                      ▼
                 deterministic                         build AP interface rows
                 or optional LLM                              │
                                                              ▼
                                                   QA gate  ──▶ CSV  (+ optional
                                              (balances, FKs,      direct INSERT)
                                               duplicates, holds)
```

## Quick start (mock backend — no DB needed)

```bash
./setup.sh && source .venv/bin/activate
ebs-ap-paf sample_data/invoice_acme_widgets.txt --backend mock
# → output/AP_INVOICES_INTERFACE.csv, AP_INVOICE_LINES_INTERFACE.csv,
#   agent_trace.json, qa_report.json
```

New here? Follow the 3-step **[INSTALL.md](INSTALL.md)** — it's copy-paste simple.

## Live backend (EBS Vision)

Requires the Oracle Instant Client (thick mode — the DB uses Native Network
Encryption) and the APPS password. See [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md).

```bash
export EBS_PASSWORD='********'
python -m ebs_ap_paf sample_data/invoice_advanced_network_3495.txt --backend live
```

This invoice is built from real Vision PO **3495** (vendor *Advanced Network
Devices*); it produces a clean 3-way match and a **PASS** QA report.

### Optional: stage rows directly into the AP interface tables (off by default)

```bash
python -m ebs_ap_paf <invoice> --backend live --load-to-ebs --yes
```

Only QA-`loadable` invoices are written, and only to `AP_INVOICES_INTERFACE` /
`AP_INVOICE_LINES_INTERFACE` — never the base tables.

## Tests

```bash
pytest -m "not live"                      # hermetic unit/integration (no DB)
EBS_RUN_LIVE=1 EBS_PASSWORD=... pytest -m live   # live EBS assertions (PO 3495)
```

## Configuration

Settings resolve by precedence **CLI flag > JSON (`--config`) > env var > default**.
Key env vars: `EBS_HOST EBS_PORT EBS_SID EBS_USER EBS_PASSWORD EBS_ORG_ID
EBS_BACKEND EBS_EXTRACTOR EBS_INSTANT_CLIENT_DIR`. The password is never
hard-coded; if absent it is prompted via `getpass`. Copy `conn.example.json` to
`conn.json` (gitignored) for file-based config.

## Layout

| Path | Purpose |
|------|---------|
| `src/ebs_ap_paf/repository.py` | live + mock EBS data access (the core) |
| `src/ebs_ap_paf/extractor.py` | deterministic + optional LLM extraction |
| `src/ebs_ap_paf/policy_engine.py` | 3-way match, tolerances, GL/tax coding |
| `src/ebs_ap_paf/interface_writer.py` | balanced AP interface CSV builder |
| `src/ebs_ap_paf/qa_checks.py` | pre-load data-quality gate |
| `src/ebs_ap_paf/invoice_agent.py` | orchestrator |
| `src/ebs_ap_paf/mcp_ebs_server.py` | MCP server (PAF integration) |
| `docs/` | architecture, interface contract, security, runbook |
| `files/` | original reference PoC (kept for provenance) |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design, and
[docs/PAF_INTEGRATION.md](docs/PAF_INTEGRATION.md) to import the agent into
Oracle Private Agent Factory (Open Agent Spec + MCP server in `paf/`).
