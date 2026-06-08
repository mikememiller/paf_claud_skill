---
name: ebs-paf-agent
description: >-
  Build an Oracle Private Agent Factory (PAF 26.4) agent end-to-end: define →
  (clone or author) a tool-bound flowGraph → package an importable `.paf` →
  import → rebind MCP + LLM → validate, with QA, tests, and Syntax-branded
  sales/design/SOW docs + OCI BOM + ROI. The domain-neutral CORE (`core/`)
  builds ANY PAF agent; Oracle E-Business Suite (EBS) is the bundled reference
  domain (any module — AP, AR, GL, PO, Order Management, Inventory, WIP, BOM,
  HR/Payroll). Use when the user wants to "create a PAF agent", "an agent like
  the Oracle PAF / contract-renewals blog", to "import an agent into Private
  Agent Factory", "monetize an EBS interface", or "another PAF agent". Covers
  Financials, HR/Payroll, Manufacturing, Supply Chain. Each build loops on QA
  until zero bugs remain.
---

# PAF Agent — build factory

Produce a new Oracle **Private Agent Factory (26.4)** agent that is
**production-correct on the first pass**: real verified logic, a hard QA gate, the
importable `.paf`, and a complete branded deliverable set. A **guided procedure**
— execute with the user in the loop; do not silently generate a black box.

**Two layers.** The **domain-neutral core** (`core/`, start at `core/README.md`)
designs → packages → imports → validates ANY PAF agent. A **domain pack** supplies
the system-specific layer; **EBS is the bundled domain** (`references/` +
`templates/`). The EBS procedure below is the worked example — for a non-EBS
agent, follow `core/README.md` with your own domain pack.

**Core (domain-neutral) — read first** (`core/`): `README.md` (the build
procedure) · `paf-import.md` (`.paf` format + packager + clone-and-mint) ·
`validation-gate.md` (post-import correctness) · `scripts/paf_packager.py` +
`scripts/list_mcp_tools.py` · `flowgraphs/` (clone-able tool-bound templates).

**EBS domain pack** (`references/`): `architecture.md` · `oracle-gotchas.md` ·
`connection.md` · `paf-platform.md` (OCI managed MCP integration) ·
`interface-catalog.md` (the 4 EBS pillars) · `qa-and-bugfixing.md` (the loop +
known-bug catalog) · `pricing-and-bom.md` · `branding.md` · `graphics-standard.md`
· `deliverables.md`.

The proven EBS engine to start from is in `templates/` (the shipped EBS AP agent,
fully tested). Reuse it; change only the variable layer (§ "What varies").

---

## Architecture (every agent, same shape)

```
document → PAF extract (LLM node) → governed EBS tools → deterministic policy
        → EBS Open Interface (read/validate via MCP; LOAD via standard import)
        + QA gate + tests + Syntax docs/deck/SOW/BOM/ROI + PAF wiring
```

**Decided platform assumptions (do not re-litigate without the user):**
- **EBS = 19c** on **OCI** (DBaaS or Exadata), NNE on. It is the **system of
  record** and the **home of all business logic** (PL/SQL in a custom `XX…`
  schema). Agent only stages rows into the standard Open Interface.
- **PAF** runs on an **ADB 26ai sidecar** that holds **zero EBS data** and is
  **not in the data path**.
- **MCP = the OCI Database Tools Managed MCP** (default): a fully managed OCI
  service, HTTPS + OAuth2/IAM, reaching EBS 19c via a **Database Tools
  Connection** (private endpoint; no broker container, no DB link, no thick-mode
  in production). Domain logic is published as **custom PL/SQL tools + SQL
  Reports** (governed, named, parameterized — the LLM never authors SQL). See
  `paf-platform.md`. Fallbacks (only if managed MCP unavailable): self-hosted
  thin SSE MCP service, or ORDS/REST→OpenAPI.
- **Writes stay off the MCP path:** the agent reads + matches + codes + QA via
  MCP; the interface **load** runs as a standard Open Interface Import / a
  governed PL/SQL job. (Only put DML on the MCP if a DML-capable custom tool is
  explicitly confirmed at install — a verify item.)
- Python (the `templates/` engine) is the **reference implementation + mock +
  test oracle + CSV/portable fallback**, not the production runtime. Production
  logic is the EBS PL/SQL package; keep them at **parity** (test it — §QA).

## What stays the same vs what varies

**Invariant (reuse from `templates/`):** module layout, connection layer
(thick/NNE for dev/test), extractor (deterministic + optional LLM), the QA gate
concept, balancing output, read-only-by-default, the test strategy, the
deliverable set, the Syntax file-header banner, the OCI-managed-MCP integration.

**Variable (the per-agent `spec.yaml`, see `spec.example.yaml`):** domain name +
narrative; source EBS tables + verified SQL; extraction schema; policy/tolerance
rules; target interface table(s) + columns + import program; the golden record;
ROI inputs. Start from `interface-catalog.md` for the target module.

---

## Procedure (phases — keep the user in the loop)

**Phase 0 — Intake.** Fill `spec.yaml` with the user (domain, EBS module, target
interface, policy, branding, ROI, rate card). Default rates: onshore $175 /
nearshore $85 / offshore $65 (see `pricing-and-bom.md`).

**Phase 1 — Live discovery & verification (MANDATORY before any code).** Connect
to the target EBS via the `oracle` MCP. Confirm every source/target table exists
— **use `COUNT(*)`, never `num_rows` (stats are stale)**. Pick a **golden
record**. Author each query and **run it live with literal binds until correct**;
capture exact column names. *Rule: never embed SQL that hasn't returned rows
live.* (`oracle-gotchas.md`, `connection.md`.)

**Phase 2 — Scaffold.** Copy `templates/` into a new git repo; rename the package
to `spec.package`; stamp the Syntax header (`templates/file_header.txt`) on every
file; `git init`. (`scripts/scaffold.py` can stamp this; guided, not silent.)

**Phase 3 — Implement the variable layer.** Repository SQL (verified Phase 1,
bind vars, org-scoped, `apps.` synonyms, ROWNUM-safe), extraction schema, policy
rules, interface columns (+ balancing/TAX line), QA referential checks, golden
record in tests. Then author the **EBS `XX…` PL/SQL** package mirroring the
Python policy/QA, and the **managed-MCP tool/SQL-Report definitions** that expose
it (`paf-platform.md`).

**Phase 4 — QA pass (hard gate, `qa-and-bugfixing.md`).** Run hermetic + live
tests; adversarial review vs the known-bug catalog; static checks; file-header
check; balancing/QA-gate proof on the golden record; **Python↔PL/SQL parity test**
(utPLSQL + compare on the golden record); clean-venv install check. Fix every bug
**and add a regression test** before moving on. Emit `QA_REPORT.md`.

**Phase 5 — Deliverables (all Syntax-branded, hero graphics).** Compute the one
pricing model (`pricing-and-bom.md`), render the hero diagram kit once
(`graphics-standard.md` — incl. the **required technical-architecture diagram**:
EBS 19c + PAF/ADB sidecar + managed MCP), then generate: sales **.pptx**,
installation **.docx**, technical-design **.docx** (with the architecture
diagram), **SOW .docx** (signable, generic legal shell, with the diagram +
12/24/36-mo managed-services pricing), OCI **BOM/estimator .xlsx**, interactive
**ROI calculator .html**, and the PAF integration package (managed-MCP tool defs
+ canvas recipe + an importable **`.paf`** minted with `core/scripts/paf_packager.py`,
password `simple4u`; after import, **rebind** MCP+LLM and run the validation
gate). The generators in `templates/deliverables/` are **spec-driven** — run
`pricing.py` (→ `output/spec.json` + `pricing.json`), then `build_diagrams.js`
(the required hero architecture/flow diagram), `build_docx.py` (install +
tech-design + SOW), `build_oci_bom_xlsx.py`, and `build_sales_deck.js`. Ready
examples live in `deliverables/samples/`; the catalog is `deliverables/DELIVERABLES.md`.
(ROI `.html` is the one roadmap generator — author per build.) (`deliverables.md`.)

**Phase 6 — Converge (iterative bug-hunt, run to zero).** Loop the QA pass over
code **and** deliverables until **two consecutive clean rounds**: full suite
green, `QA_REPORT.md` = PASS, every fix has a regression test, visual QA of all
graphics passes. Nothing ships before convergence. (`qa-and-bugfixing.md`.)

**Phase 7 — Commit & memory.** Commit (co-author trailer); write a project memory
note (golden record, test commands, gotchas hit, convergence summary).

---

## Rules (non-negotiable)

1. Verify SQL live before embedding (golden-record driven).
2. Oracle gotchas: `ROWNUM`+`ORDER BY` → inline view; **bind date objects**, not
   strings; confirm data with `COUNT(*)` (ignore `num_rows`); lookup resolution
   order id → number → exact → fuzzy. (`oracle-gotchas.md`)
3. Thick/NNE + `apps.` synonyms + org-scope + **bind variables only** (dev/test
   layer); production reaches EBS via the managed MCP / Database Tools Connection.
4. Read-only by default; never touch base tables; interface writes are gated and
   **off the MCP path** unless a DML tool is confirmed.
5. Output must **balance** (header = Σ lines incl. a TAX line where applicable).
6. Policy is deterministic & outside the LLM; extraction is pluggable.
7. **QA gate before any write; loop to zero bugs** before shipping.
8. Secrets never hard-coded; `.gitignore` creds; getpass fallback (dev).
9. Tests: hermetic default + live golden + **Python↔PL/SQL parity**.
10. Every deliverable Syntax-branded; **every file carries the Syntax
    copyright/version/build/date banner** (QA fails the build otherwise).
11. Use a **tool-capable LLM** in PAF (OCI GenAI grok-4/gpt-5, OpenAI gpt-4o).
    Deliver via **`.paf` import on PAF 26.4** (`core/scripts/paf_packager.py`, default
    password `simple4u`), then **rebind** the MCP server + LLM and run the
    **validation gate**. Bulk slate = clone a tool-bound flowGraph template
    (`clone_flowgraph`/`pack_flowgraph`). The canvas authors the first template
    and is the fallback. (`core/paf-import.md`, `core/validation-gate.md`, `references/paf-platform.md`)
12. **Honesty:** flag anything not verifiable in-environment (managed-MCP DML
    support, PAF OAuth flow, GA coverage for the target DB, slide rendering
    without LibreOffice) in `QA_REPORT.md` — never imply it passed.

## Install-time verify items (carry into `QA_REPORT.md`)
- managed MCP supports the target EBS 19c (DBaaS/Exadata) in the region/edition;
- whether a **DML-capable custom PL/SQL tool** is allowed (else load via import);
- managed-MCP pricing line for the BOM;
- PAF MCP node completes the OCI IAM OAuth flow to the managed MCP endpoint.

## Scale note
For a thorough build or many agents at once, the QA bug-hunt (Phase 6) and the
multi-deliverable generation (Phase 5) parallelize well — only escalate to a
multi-agent workflow when the user opts in.
