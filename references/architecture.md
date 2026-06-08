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

## Key design choices (carry into every agent)
- DI of repository + extractor → identical pipeline runs on mock (hermetic) or
  live EBS by swapping one constructor arg.
- Deterministic policy/QA kept out of the LLM → auditable/SOX, reproducible.
- Extraction degrades gracefully (deterministic default) → runs with only the DB.
- Read-only by default; CSV / Open Interface Import preserves AP controls.
- Output must balance; QA gate before anything leaves the agent.
