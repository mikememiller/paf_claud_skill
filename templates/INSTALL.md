<!-- Syntax Corporation © 2026 — EBS AP PAF · v1.0.0 · 2026-06-02 -->

# Install & Run — the easy way

Three steps to a working agent. Copy-paste each block.

> **Just want to try it?** Do **Step 1** + **Step 2**, then run the *mock* command
> at the bottom of Step 2. No database, no password, nothing to configure.

---

## Step 1 — Install the software

You need **Python 3.10+**. From the project folder, run the one-command setup:

```bash
./setup.sh
source .venv/bin/activate
```

That creates a virtual environment and installs the agent. (`setup.sh` works
both on a normal machine and on a restricted network — if it can't reach PyPI it
reuses an already-installed `python-oracledb`.)

<details><summary>Prefer to do it by hand?</summary>

```bash
python3 -m venv .venv --system-site-packages && source .venv/bin/activate
pip install -e .            # or: pip install -e . --no-deps  (restricted network)
```
</details>

---

## Step 2 — Run it (no database needed)

```bash
ebs-ap-paf sample_data/invoice_acme_widgets.txt --backend mock
```

You'll see the match results in the terminal, and four files appear in `output/`:
`AP_INVOICES_INTERFACE.csv`, `AP_INVOICE_LINES_INTERFACE.csv`, `agent_trace.json`,
`qa_report.json`. ✅ If you got those, the install works.

---

## Step 3 — Connect to the live EBS database

The EBS database uses encrypted connections, so it needs Oracle's **Instant
Client** (a one-time download).

**3a. Get the Instant Client** (Apple Silicon Mac shown; ~80 MB):

```bash
mkdir -p ~/lib/oracle && cd ~/lib/oracle
curl -kL -o ic.dmg https://download.oracle.com/otn_software/mac/instantclient/instantclient-basic-macos-arm64.dmg
hdiutil attach ic.dmg && cp -R /Volumes/instantclient-*/ ./instantclient && hdiutil detach /Volumes/instantclient-*
xattr -dr com.apple.quarantine ~/lib/oracle/instantclient    # let macOS load it
cd -
```
*(Windows/Linux: download "Instant Client Basic" from oracle.com and unzip it;
then set `EBS_INSTANT_CLIENT_DIR` to that folder.)*

**3b. Tell it how to connect** — set the password (the only required setting;
host/SID/user already default to the Vision instance):

```bash
export EBS_PASSWORD='your-APPS-password'
```

**3c. Run against live EBS:**

```bash
ebs-ap-paf sample_data/invoice_advanced_network_3495.txt --backend live
```

Expected: supplier *Advanced Network Devices* matched, all 4 lines `AUTO`,
**QA status PASS**, totalling **$632,500.00**.

---

## Optional — check everything works

```bash
pytest -m "not live"                                   # offline checks
EBS_RUN_LIVE=1 EBS_PASSWORD='...' pytest -m live       # live EBS checks
```

## If something goes wrong

| Message | Do this |
|---------|---------|
| `Instant Client not found` | Re-check Step 3a, or `export EBS_INSTANT_CLIENT_DIR=/path/to/instantclient`. |
| `DPY-3001` | Same fix — the Instant Client must be installed (thick mode). |
| `dlopen … quarantine` (Mac) | `xattr -dr com.apple.quarantine ~/lib/oracle/instantclient` |
| asks for a password | Run `export EBS_PASSWORD='...'` (or just type it at the prompt). |
| `command not found: ebs-ap-paf` | Run `source .venv/bin/activate` first. |

Full operational detail is in [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md).
