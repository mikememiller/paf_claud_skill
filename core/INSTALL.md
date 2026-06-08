<!-- Syntax Corporation © 2026 — PAF core · core/INSTALL.md · v1.0.0 · 2026-06-08 -->
# Installing a PAF agent (generic)

Domain-neutral install for **any** PAF 26.4 agent built with this skill. The
per-engagement, branded **Installation Guide `.docx`** is generated from
`spec.install` by `templates/deliverables/build_docx.py`; this note is the
underlying procedure (the EBS specifics — DB grants, `XX…` PL/SQL — live in the
EBS domain pack `templates/INSTALL.md`).

## Prerequisites
- **Oracle AI Database 26ai** with **Private Agent Factory** enabled (PAF is a $0
  add-on; `max_string_size=EXTENDED`).
- An **MCP server** the agent will use for tools — the **OCI Database Tools
  Managed MCP** (default) or your own MCP endpoint.
- A **tool-capable LLM** available in PAF (OCI GenAI `xai.grok-4`/`openai.gpt-5`,
  or OpenAI `gpt-4o`).
- `pip install pyagentspec` to (re)build the Agent Spec content; `cryptography`
  for the `.paf` packager (`core/scripts/paf_packager.py`).

## Steps
1. **Discover the tools** on the target MCP server:
   `python core/scripts/list_mcp_tools.py --url <sse-url>` → align the agent prompt
   to tools that actually exist.
2. **Get the `.paf`** — clone a tool-bound template
   (`core/flowgraphs/*.flowgraph.json` → `clone_flowgraph` → `pack_flowgraph`) or
   author one on the canvas and Export it. (See `core/paf-import.md`.)
3. **Import** in PAF → **My Custom Flows → Import** → upload the `.paf` → enter the
   password (**`simple4u`** by default; `$PAF_PASSWORD` to override).
4. **Rebind** in Agent Builder: bind the **MCP-server node** to the registered
   server and pick an **LLM**. The `.paf` ships no bindings/secrets by design.
5. **Validate** with `core/validation-gate.md` (importing ≠ correct — run the
   ground-truth scenarios; zero unsafe actions = PASS).

## Regenerate the branded install `.docx`
```bash
python templates/deliverables/pricing.py  --spec spec.yaml --out build
python templates/deliverables/build_docx.py --spec build/spec.json \
    --pricing build/pricing.json --diagram build/architecture.png --out build
```
→ `build/Installation_Guide.docx` (+ Technical Design + SOW). See
`references/deliverables.md`.
