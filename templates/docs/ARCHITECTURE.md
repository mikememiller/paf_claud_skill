<!-- Syntax Corporation © 2026 — EBS AP PAF · v1.0.0 · 2026-06-02 -->

# Architecture

## Overview

The agent follows the PAF pattern: **document → extract → MCP-mediated EBS
lookups → deterministic policy overlay → interface tables**. Each stage is a
swappable component behind a narrow interface, so the same orchestrator runs
against mock fixtures (offline tests) or the live EBS Vision database.

```
            ┌──────────────────────────────────────────────────────┐
            │                  InvoiceAgent (orchestrator)           │
            │                                                        │
 invoice ─▶ │  Extractor ─▶ EBSRepository ─▶ policy_engine ─▶ Writer │ ─▶ CSV
   text     │   (DI)          (DI)            (3-way match)    │      │
            │                                                  ▼      │
            │                                            qa_checks    │ ─▶ qa_report.json
            └──────────────────────────────────────────────────────┘
                                   │ (optional, gated)
                                   ▼
                          interface_loader ─▶ AP_*_INTERFACE
```

## Components

| Module | Responsibility | Key types |
|--------|----------------|-----------|
| `config.py` | Resolve settings (flag > JSON > env > default); password handling | `Settings` |
| `db.py` | python-oracledb **thick-mode** connection (NNE), bind-only queries | `EBSConnection` |
| `repository.py` | Read-only EBS lookups | `EBSRepository` (Protocol), `LiveEBSRepository`, `MockEBSRepository` |
| `extractor.py` | Invoice → structured dict | `DeterministicExtractor`, `LLMExtractor`, `make_extractor()` |
| `policy_engine.py` | 3-way match, tolerances, GL/tax coding | `three_way_match`, `code_distribution`, `code_tax` |
| `interface_writer.py` | Build balanced AP interface rows + CSV | `EBSInterfaceWriter` |
| `qa_checks.py` | Pre-load validation gate | `validate_invoice`, `QAReport` |
| `interface_loader.py` | Optional gated INSERT into interface tables | `load_invoices` |
| `invoice_agent.py` | Orchestrate the flow + assemble the trace | `InvoiceAgent`, `AgentTrace` |
| `mcp_ebs_server.py` | Expose repository as MCP tools for PAF | `build_repository`, `main` |

## Design decisions

**Dependency injection of repository + extractor.** `InvoiceAgent` receives an
`EBSRepository` and an `InvoiceExtractor`. This is why the identical pipeline is
fully testable offline (mock JSON) yet runs against live EBS by swapping one
constructor argument — and why the live SQL can be validated independently.

**Policy is deterministic, kept out of the LLM.** Extraction may be
probabilistic; matching, tolerances and coding are pure Python. This is what
makes the output auditable (SOX) and reproducible.

**Extraction degrades gracefully.** The default `DeterministicExtractor` is
pure standard library, so the pipeline runs with **only the database** as a live
dependency. The `LLMExtractor` (Anthropic) is opt-in for messy/scanned invoices.

**Read-only by default; CSV is the contract.** The faithful path emits the two
interface CSVs for the standard *Payables Open Interface Import*, preserving all
AP controls. A direct INSERT into the interface tables exists but is off by
default and requires explicit confirmation (`--load-to-ebs --yes`).

**QA gate before anything leaves the agent.** Every invoice is validated
(arithmetic, header-balances-to-lines, lookup validity, required fields, FK
existence, duplicates, tolerance holds) and assigned `PASS` / `HOLD` / `FAIL`.
Only `loadable` invoices (no ERROR, no HOLD) are auto-loaded.

## Data shapes

`EBSRepository` returns plain dicts with stable keys (see `repository.py`
docstrings). The deterministic extractor emits the shape documented in
`extractor.py`'s prompt (header fields + `lines[]` + `subtotal/tax_total/total`).

## Productionising on PAF

1. Deploy `mcp_ebs_server.py` as a sidecar on the 26ai Autonomous DB VM with a
   service account that calls `FND_GLOBAL.APPS_INITIALIZE` per session.
2. Rebuild the flow in PAF Agent Builder: document input → extract node → MCP
   tool nodes → policy node → CSV/interface node.
3. Schedule the CSVs into `$APPLCSF/inbound/` and trigger the import program.
4. Route `HOLD` invoices to AME (or a PAF approval node).
