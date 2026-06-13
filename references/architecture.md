<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# Architecture

The PAF pattern, one shape per agent: **document → extract → governed EBS tools →
deterministic policy → EBS Open Interface**, with QA + branded deliverables.

## Components (templates/src/ebs_paf_agent/)
| Module | Responsibility |
|--------|----------------|
| `config.py` | settings precedence (flag > JSON > env > default); no hard-coded secrets |
| `db.py` | python-oracledb **thick/NNE** connection (dev/test + reference engine) |
| `repository.py` | `EBSRepository` protocol + Live + Mock; bind-var, org-scoped SQL |
| `extractor.py` | Deterministic parser (zero deps) + optional LLM; factory |
| `policy_engine.py` | match/tolerance/coding rules — deterministic, outside the LLM |
| `interface_writer.py` | builds **balanced** AP-style interface rows (+ TAX line) |
| `qa_checks.py` | pre-load validation gate → `PASS/HOLD/FAIL` + `loadable` |
| `interface_loader.py` | optional, gated, batch-id-cleanable INSERT (off by default) |
| `invoice_agent.py` | orchestrator; `process()` + `process_extracted()` (PAF split) |
| `mcp_ebs_server.py` | local/stdio + SSE wrappers (reference; production uses managed MCP) |
| `cli.py` | `python -m <pkg>` entry point |

## Production vs reference
- **Production runtime:** PAF (ADB sidecar) → **OCI managed MCP** → EBS 19c
  **PL/SQL** (`XX…` package). See `paf-platform.md`.
- **Reference/test:** the Python engine above — also the **test oracle** that the
  EBS PL/SQL must match (parity test, see `qa-and-bugfixing.md`).

## Monitoring planes (production — see `observability.md`)
Every production agent runs under two-plane supervision feeding CxHub:
- **Plane A — agent observability:** PAF 26.4 emits OTEL traces/spans (run, step,
  tool call, LLM call) → OTEL collector → tracing backend (Phoenix/Langfuse/Opik)
  + a metadata-only digest into OCI Logging Analytics. The differentiator.
- **Plane B — platform availability:** synthetic probes + resource collectors
  watch PAF and every dependency (host, DB 26ai, model endpoint, MCP, egress,
  tracing backend, credentials) from PAF's vantage point. Table stakes.

The full estate picture: `… EBS 19c XX… PL/SQL` (data path) **plus** `PAF → OTEL
collector → backend + CxHub` (Plane A) **plus** `probes → OCI Monitoring/Logging
Analytics → CxHub` (Plane B). Deliverable architecture diagrams should show both
planes when monitoring is in scope (`spec.observability`).

## Key design choices (carry into every agent)
- DI of repository + extractor → identical pipeline runs on mock (hermetic) or
  live EBS by swapping one constructor arg.
- Deterministic policy/QA kept out of the LLM → auditable/SOX, reproducible.
- Extraction degrades gracefully (deterministic default) → runs with only the DB.
- Read-only by default; CSV / Open Interface Import preserves AP controls.
- Output must balance; QA gate before anything leaves the agent.
