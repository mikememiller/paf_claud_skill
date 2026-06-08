<!-- Syntax Corporation © 2026 — EBS AP PAF · v1.0.0 · 2026-06-02 -->

# Operations Runbook

## 1. Prerequisites

* Python 3.10+
* Oracle Instant Client (arm64 for Apple Silicon) at `~/lib/oracle/instantclient`
  (thick mode is mandatory — the DB uses NNE). On macOS, strip Gatekeeper
  quarantine once: `xattr -dr com.apple.quarantine ~/lib/oracle/instantclient`.
* Network reachability to the EBS DB (`172.16.3.44:1521`, SID `EBSDB`).
* The APPS (or read service-account) password.

```bash
pip install -e .            # installs python-oracledb
# optional extras:
pip install -e ".[llm]"     # Anthropic extractor
pip install -e ".[mcp]"     # MCP server transport
pip install -e ".[dev]"     # pytest/ruff/mypy
```

## 2. Configure

Pick one (precedence: flag > JSON > env > default):

```bash
# env
export EBS_HOST=172.16.3.44 EBS_PORT=1521 EBS_SID=EBSDB EBS_USER=APPS
export EBS_ORG_ID=204 EBS_BACKEND=live
export EBS_PASSWORD='********'
export EBS_INSTANT_CLIENT_DIR=~/lib/oracle/instantclient
```
or copy `conn.example.json` → `conn.json` and pass `--config conn.json`.

## 3. Run

```bash
# hermetic mock run (no DB)
python -m ebs_ap_paf sample_data/invoice_acme_widgets.txt --backend mock

# live run against EBS Vision
python -m ebs_ap_paf sample_data/invoice_advanced_network_3495.txt \
    --backend live --out output/

# stage straight into the AP interface tables (explicit, optional)
python -m ebs_ap_paf <invoice> --backend live --load-to-ebs --yes
```

Exit code `0` = no QA failures; `3` = at least one invoice has QA status `FAIL`
(useful for scheduling/CI).

## 4. Outputs

| File | Meaning |
|------|---------|
| `output/AP_INVOICES_INTERFACE.csv` | invoice headers (balanced) |
| `output/AP_INVOICE_LINES_INTERFACE.csv` | item + tax lines |
| `output/agent_trace.json` | full explainability log per invoice |
| `output/qa_report.json` | QA findings; check `status` and `loadable` |

## 5. Reading the QA report

* `status: PASS` + `loadable: true` → safe to import.
* `status: HOLD` → well-formed but a line is outside tolerance; route to AME.
* `status: FAIL` → malformed (unbalanced, bad arithmetic, missing FK,
  duplicate); **do not import** — inspect `findings[].detail`.

## 6. Tests

```bash
pytest -m "not live"                              # offline suite
EBS_RUN_LIVE=1 EBS_PASSWORD=... pytest -m live    # live PO-3495 assertions
```

## 7. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `DPY-3001` | Thin mode against an NNE DB. Ensure Instant Client present + `EBS_INSTANT_CLIENT_DIR` set (thick mode). |
| `Instant Client not found` | Set `EBS_INSTANT_CLIENT_DIR` to the client dir. |
| `dlopen ... quarantine` (macOS) | `xattr -dr com.apple.quarantine <client dir>`. |
| `SUPPLIER_NOT_FOUND` | Vendor name/tax-id on the invoice doesn't resolve; check `ap_suppliers`. |
| `PO_NOT_FOUND_*` | PO number not in the target org; verify `--org-id`. |
| QA `FAIL` balances | Extraction mis-read amounts; inspect `agent_trace.json.extracted`. |
| No password | Set `EBS_PASSWORD` or respond to the `getpass` prompt. |
