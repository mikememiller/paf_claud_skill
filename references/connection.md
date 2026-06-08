<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# Connecting to EBS (dev/test) and discovery

## Live discovery (Phase 1) — via the `oracle` MCP
Use the session's `oracle` MCP (`connect`, `run-sql`) to author and verify every
query against the **target** EBS instance before embedding it. The MCP handles
NNE. Discovery recipes are in `scripts/discovery.sql`.

Rules: confirm tables with `COUNT(*)`; pick a golden record; run each query with
literal values until correct; record exact column names for the writer.

## Dev/test runtime — python-oracledb thick mode (NNE)
- Instant Client required (thin fails `DPY-3001`). Default
  `~/lib/oracle/instantclient`; `oracledb.init_oracle_client(lib_dir=…)`.
- macOS: strip quarantine once: `xattr -dr com.apple.quarantine <client dir>`.
- DSN via SID: `oracledb.makedsn(host, port, sid=…)`.
- Settings precedence: flag > JSON (`--config`) > env (`EBS_HOST/PORT/SID/USER/
  PASSWORD/ORG_ID/INSTANT_CLIENT_DIR`) > default. Password via env/getpass; never
  hard-coded; `conn.json` gitignored.

## Production runtime — NOT thick mode
Production reaches EBS through the **OCI Database Tools Managed MCP** over a
**Database Tools Connection** (private endpoint, secret in OCI Vault). No Instant
Client, no thick-mode, no DB link in production. See `paf-platform.md`.

## Restricted-network installs
PyPI may be blocked. `templates/setup.sh` falls back to
`--system-site-packages --no-deps` to reuse an already-installed
python-oracledb. Verify the `…` console entry point after install.
