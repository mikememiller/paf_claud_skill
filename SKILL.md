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
  until convergence — v2 ENFORCES the loop with a state machine, lifecycle
  hooks, and builder/validator subagents (see references/orchestration.md).
compatibility: "Uploadable skill (claude.ai / Cowork / Skills API) and Claude Code. In Claude Code, wire the enforcement hooks via hooks/settings.fragment.json (the P2 scaffold installs .claude/paf-hooks/); on claude.ai/Cowork the gates are binding procedurally."
---

<!-- Syntax Corporation © 2026 — EBS PAF Agent skill · SKILL.md · v2.1.0 · 2026.06.13 -->
# PAF Agent — build factory (v2: enforced)

Produce a new Oracle **Private Agent Factory (26.4)** agent that is
**production-correct on the first pass**: verified logic, a hard QA gate, the
importable `.paf`, and the complete branded deliverable set. A **guided
procedure** — execute with the user in the loop; never a silent black box.

**Two layers.** The **domain-neutral core** (`core/`, start at `core/README.md`)
designs → packages → imports → validates ANY PAF agent (`paf-import.md`,
`validation-gate.md`, `scripts/paf_packager.py`, `scripts/list_mcp_tools.py`,
clone-able `flowgraphs/`). The **EBS domain pack** is `references/` (architecture, oracle-gotchas, connection,
paf-platform, interface-catalog, qa-and-bugfixing, pricing-and-bom, branding,
graphics-standard, deliverables, observability, orchestration) + `templates/` (the shipped, fully tested EBS AP engine — reuse
it; change only the variable layer in `spec.yaml`, see `spec.example.yaml`).

## Architecture (every agent, same shape)

```
document → PAF extract (LLM node) → governed EBS tools → deterministic policy
        → EBS Open Interface (read/validate via MCP; LOAD via standard import)
```

**Decided platform assumptions (do not re-litigate without the user):**
- **EBS = 19c on OCI** (DBaaS/Exadata, NNE on) — system of record, home of all
  business logic (PL/SQL in a custom `XX…` schema); the agent only stages rows
  into the standard Open Interface.
- **PAF on an ADB 26ai sidecar** — zero EBS data, not in the data path.
- **MCP = OCI Database Tools Managed MCP** (HTTPS + OAuth2/IAM, Database Tools
  Connection, private endpoint). Domain logic = custom PL/SQL tools + SQL
  Reports — the LLM never authors SQL (`paf-platform.md`). Fallbacks only if
  managed MCP unavailable: self-hosted thin SSE MCP, or ORDS/REST→OpenAPI.
- **Writes stay off the MCP path** — read/match/code/QA via MCP; the load runs
  as a standard Open Interface Import or governed PL/SQL job (DML-capable MCP
  tool only if explicitly confirmed at install — a verify item).
- **Python engine = reference + mock + test oracle + portable fallback**;
  production logic is the EBS PL/SQL package — keep them at parity (tested).
- **Observability is native in 26.4** — PAF exports OTEL traces (run/step/tool/
  LLM) to one backend (Phoenix/Langfuse/Opik via an OTEL collector). Every
  production agent runs under the **two-plane** model — Plane A agent
  observability (the moat) + Plane B platform availability (table stakes) — with
  masking **on** by default and **one OAuth client per agent** for the audit
  chain. Design + per-agent gate live in `references/observability.md` and the
  observability checklist in `core/validation-gate.md`.

## Phases (owner · gate — details in references/orchestration.md)

| # | Phase | Owner | Gate to advance |
|---|-------|-------|-----------------|
| 0 | Intake — fill `spec.yaml` with the user | main | spec lints (`lint_paf.py spec.yaml`) |
| 1 | Live discovery & verification (MANDATORY before code) | **paf-discovery** | `discovery/dossier.md` + verified SQL written |
| 2 | Scaffold — copy `templates/` → new git repo, stamp headers, **install enforcement** | main | `scaffold_enforcement.py` manifest clean |
| 3 | Implement the variable layer + `XX…` PL/SQL + MCP tool defs | main | artifacts lint on write (hook) |
| 4 | QA pass (hard gate) | **paf-validator** | `qa_pass.py` round recorded |
| 5 | Deliverables (Syntax-branded, spec-driven) | **paf-deliverables** | manifest + `.paf` lints + visual QA |
| 6 | Converge — loop Phase 4 to **2 consecutive clean rounds** | main + paf-validator | `converged.py` exits 0 (the Stop hook enforces this) |
| 7 | Commit & memory | main | commit + project memory note |

**Phase notes (irreplaceable details):**
- **P0** default rates: onshore $175 / nearshore $85 / offshore $65
  (`pricing-and-bom.md`).
- **P1** iron rule: never embed SQL that has not returned rows live; golden
  record selected here; `COUNT(*)`, never `num_rows`.
- **P2** command: `python <skill>/scripts/scaffold_enforcement.py --target
  <repo> --init-state` — installs `scripts/qa/`, `.claude/paf-hooks/`,
  `.claude/agents/`, seeded `qa_checks/` (balancing + parity contracts).
- **P3** repository SQL: bind vars, org-scoped, `apps.` synonyms, ROWNUM-safe;
  interface columns include the balancing/TAX line.
- **P4** includes the **Python↔PL/SQL parity test** (utPLSQL on the golden
  record) — `qa_checks/parity_check.py` enforces the contract.
- **P5** generator chain (spec-driven, in order): `pricing.py` →
  `build_diagrams.js` (required architecture hero: EBS 19c + PAF/ADB sidecar +
  managed MCP) → `build_docx.py` (install/tech-design/SOW) →
  `build_oci_bom_xlsx.py` → `build_sales_deck.js`; mint `.paf` with
  `paf_packager.py` (password `simple4u`); ROI `.html` authored per build.
- **P6** convergence is data, not judgment: `build_state.json` tracks rounds;
  every fix adds a regression test (the test-count delta is enforced).

## Enforcement (v2 — see references/orchestration.md)

Hooks (wired via `hooks/settings.fragment.json`; scripts installed by P2
scaffold): **SessionStart**
injects environment ground truth · **PreToolUse(Bash)** blocks `num_rows`
stats reads and EBS base-table DDL · **PostToolUse(Write|Edit)** lints
`.flowgraph.json`/`.paf`/`spec.yaml`/banners on write · **Stop** blocks "done"
until `converged.py` exits 0 (ceiling → `ESCALATION.md`, stop allowed).
In Claude Code, merge `hooks/settings.fragment.json` into
`<project>/.claude/settings.json` after the P2 scaffold installs
`.claude/paf-hooks/` (the scaffold can also write the wiring). **Cowork /
claude.ai (no hooks): the gates are binding procedurally** — run `qa_pass.py`
then `converged.py --report` before claiming done; lint every artifact after
writing it.

## Rules (non-negotiable)

1. Verify SQL live before embedding (golden-record driven).
2. Oracle gotchas: `ROWNUM`+`ORDER BY` → inline view; **bind date objects**,
   not strings; confirm data with `COUNT(*)` (ignore `num_rows`); lookup
   resolution order id → number → exact → fuzzy. (`oracle-gotchas.md`)
3. Thick/NNE + `apps.` synonyms + org-scope + **bind variables only** (dev/test
   layer); production reaches EBS via the managed MCP / Database Tools Connection.
4. Read-only by default; never touch base tables; interface writes are gated
   and **off the MCP path** unless a DML tool is confirmed.
5. Output must **balance** (header = Σ lines incl. a TAX line where applicable).
6. Policy is deterministic & outside the LLM; extraction is pluggable.
7. **QA gate before any write; loop to convergence** before shipping.
8. Secrets never hard-coded; `.gitignore` creds; getpass fallback (dev).
9. Tests: hermetic default + live golden + **Python↔PL/SQL parity**.
10. Every deliverable Syntax-branded; **every file carries the Syntax
    copyright/version/build/date banner** (QA fails the build otherwise).
11. Use a **tool-capable LLM** in PAF (OCI GenAI grok-4/gpt-5, OpenAI gpt-4o).
    Deliver via **`.paf` import on PAF 26.4** (`paf_packager.py`, password
    `simple4u`), then **rebind** MCP + LLM and run the **validation gate**.
    Bulk slate = clone a tool-bound flowGraph template. The canvas authors the
    first template and is the fallback. (`core/paf-import.md`,
    `core/validation-gate.md`, `references/paf-platform.md`)
12. **Honesty:** flag anything not verifiable in-environment (managed-MCP DML
    support, PAF OAuth flow, GA coverage, slide rendering without LibreOffice)
    in `QA_REPORT.md` — never imply it passed.

## Install-time verify items (carry into `QA_REPORT.md`)
- managed MCP supports the target EBS 19c (DBaaS/Exadata) in the region/edition;
- whether a **DML-capable custom PL/SQL tool** is allowed (else load via import);
- managed-MCP pricing line for the BOM;
- PAF MCP node completes the OCI IAM OAuth flow to the managed MCP endpoint.
