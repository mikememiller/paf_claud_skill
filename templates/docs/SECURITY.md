<!-- Syntax Corporation © 2026 — EBS AP PAF · v1.0.0 · 2026-06-02 -->

# Security

## Database access

* **Read-only by default.** The agent only issues `SELECT`s against EBS. The
  single write path (`interface_loader.py`) is off by default, requires explicit
  confirmation, and targets **only the interface tables** — never base AP tables.
* **Least privilege.** The production service account needs `SELECT` on the AP /
  PO / RCV / ZX / GL / INV objects listed in `EBS_INTERFACE_CONTRACT.md`, plus
  `INSERT` on the two `*_INTERFACE` tables *only if* direct staging is enabled.
* **Multi-org context.** A production deployment MUST call
  `FND_GLOBAL.APPS_INITIALIZE(user_id, resp_id, resp_appl_id)` per session
  before querying, so org-based VPD policies apply. Without it the agent can read
  across operating units — both a security finding and an audit-trail problem.
  Every query in `repository.py` is additionally `org_id`-scoped in the SQL as a
  defence in depth.

## Transport

* The EBS Vision DB enforces **Oracle Native Network Encryption (NNE)**.
  python-oracledb **thin** mode fails (`DPY-3001`); the agent uses **thick**
  mode with the Instant Client so traffic is encrypted in transit.

## Secrets

* The password is **never** committed or hard-coded. Resolution order:
  explicit `--password` → `EBS_PASSWORD` env var → JSON config (warns) →
  interactive `getpass` prompt.
* `conn.json` and `.env` are git-ignored. Use a secrets manager / vault in
  production; inject `EBS_PASSWORD` at runtime.

## Auditability

* Every processed invoice carries an `AgentTrace` (run-id, extracted values,
  match results, exceptions, confidence) and a `QAReport`. The run-id and
  confidence are also stamped into interface `ATTRIBUTE1/2`, so each row is
  traceable back to the agent run that produced it.

## LLM data handling (only if the optional LLM extractor is enabled)

* Invoice text is sent to the configured model provider. For data-residency or
  PII-sensitive environments, keep the default `DeterministicExtractor` (no data
  leaves the host) or route to an in-tenant model (e.g. OCI Generative AI).

## Threat notes

* SQL injection is structurally prevented — all dynamic values are bind
  variables; no user/extracted text is concatenated into SQL.
* The loader normalises empty strings to `NULL` and refuses non-`loadable`
  invoices, preventing malformed rows from reaching the interface.
