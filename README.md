<!-- Syntax Corporation © 2026 — paf_claud_skill · README.md · v1.0.0 · 2026-06-08 -->
# PAF Agent Factory — a Claude skill

Build an **Oracle Private Agent Factory (PAF 26.4)** agent end-to-end:
**define → (clone or author) a tool-bound flowGraph → package an importable
`.paf` → import → rebind MCP + LLM → validate**, with QA, tests, and
Syntax-branded sales / design / SOW docs + OCI BOM + ROI.

This is a [Claude](https://claude.com/claude-code) **skill** (`SKILL.md` is the
entry point). It is built in two layers:

| Layer | What | Where |
|-------|------|-------|
| **Domain-neutral core** | builds/packages/imports/validates **ANY** PAF agent | [`core/`](core/) |
| **EBS domain pack** | the bundled worked example (Oracle E-Business Suite) | [`references/`](references/) + [`templates/`](templates/) |

> **Why this exists.** PAF **26.4** imports an encrypted **`.paf`** bundle (not raw
> JSON). This repo ships a reverse-engineered, round-trip-verified packager plus a
> guided factory for producing correct, branded, importable agents at scale.

## Quick start (the core packager)

```bash
# 1) discover the REAL tool names on your MCP server
python core/scripts/list_mcp_tools.py --url http://<host>:<port>/sse

# 2) clone a tool-bound template + mint an importable .paf
python core/scripts/paf_packager.py pack \
  --in core/flowgraphs/ebs_ap_3way_match.flowgraph.json --flowgraph \
  --name "My Agent"            # default password: simple4u

# 3) PAF -> My Custom Flows -> Import -> upload my_agent.paf -> password simple4u
# 4) rebind the MCP-server node + an LLM in Agent Builder
# 5) validate (core/validation-gate.md)
```

Bulk slate (the 300-agent path): clone one good flowGraph per agent —
`clone_flowgraph(template, new_instruction=…, new_agent_description=…)` →
`pack_flowgraph()`. See [`core/paf-import.md`](core/paf-import.md).

## Using it as a Claude skill
Install under `~/.claude/skills/` (this directory). In Claude Code it triggers on
asks like *"create a PAF agent"*, *"an agent like the Oracle PAF / contract-renewals
blog"*, *"import an agent into Private Agent Factory"*, or *"monetize an EBS
interface"*. The guided 7-phase procedure is in [`SKILL.md`](SKILL.md).

## Repository layout
```
SKILL.md                  guided build procedure (skill entry point)
core/                     DOMAIN-NEUTRAL PAF kit
  README.md               the build procedure + how to add a domain pack
  paf-import.md           .paf format + packager + clone-and-mint + rebind
  validation-gate.md      post-import correctness gate (template)
  scripts/                paf_packager.py · list_mcp_tools.py
  flowgraphs/             real, tool-bound, secret-free clone templates
references/               EBS DOMAIN PACK (architecture, oracle-gotchas,
                          paf-platform, interface-catalog, qa, pricing, branding…)
templates/                EBS reference engine (a working, tested EBS AP agent)
deliverables/             DELIVERABLES.md + the wow-graphics showcase deck + generators
assets/                   brand.json + logo (single brand source)
spec.example.yaml         per-agent variable layer
```

## Deliverables
Every engagement ships a consistent, branded, QA-gated set (sales `.pptx`,
install / tech-design / SOW `.docx`, OCI BOM `.xlsx`, ROI `.html`, and the
importable `.paf`). Full catalog + a hero-graphics showcase deck:
[`deliverables/DELIVERABLES.md`](deliverables/DELIVERABLES.md).

## Notes
- A `.paf` is **secret-free by design** (credentials/LLM are bound at import), so
  the import password is a convention (`simple4u`), overridable via `$PAF_PASSWORD`.
- One brand source ([`assets/brand.json`](assets/brand.json)); deliverables are
  generated from in-repo markdown + one pricing model, so they never drift.
- History: on PAF **25.3** file-import was blocked; that is **obsolete** on 26.4
  via the `.paf` path above.

---
Syntax Corporation © 2026 · Confidential. The bundled legal/SOW shells are generic
templates — have counsel review before use.
