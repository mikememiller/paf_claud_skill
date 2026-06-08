<!-- Syntax Corporation © 2026 — PAF core (domain-neutral) -->
# PAF Core — build ANY Oracle Private Agent Factory agent

Domain-neutral kit to **design → package → import → validate** an agent on
**Oracle PAF 26.4**, independent of any specific system. EBS is the bundled
reference domain (`../references/` + `../templates/`), but nothing in `core/`
assumes EBS — point it at any system reachable via an MCP server.

## Contents
- `paf-import.md` — the `.paf` bundle format + packager + clone-and-mint + the
  import/rebind workflow (the technical reference).
- `scripts/paf_packager.py` — mint/read `.paf` bundles (`pack_paf` /
  `pack_flowgraph` / `unpack_paf` / `clone_flowgraph` / `remap_uuids` + CLI).
  Default password `simple4u`.
- `scripts/list_mcp_tools.py` — discover the real tools an MCP server exposes.
- `validation-gate.md` — the post-import correctness gate (template).
- `flowgraphs/` — real, tool-bound flowGraph templates to clone (see its README).

## The procedure (any agent)
1. **Define** the agent: name, one-line purpose, the system prompt/instruction,
   the MCP tools it needs.
2. **Discover tools** on the target MCP server:
   `python scripts/list_mcp_tools.py --url <sse-url>` → align the prompt to tools
   that actually exist.
3. **Get a flowGraph:**
   - *Tool-bound (recommended):* `clone_flowgraph()` a known-good template from
     `flowgraphs/` with your instruction/description (tool wiring preserved), OR
     author one on the PAF canvas and **Export** it.
   - *Tool-free map:* build an Agent Spec flow (pyagentspec FlowBuilder) for a
     cognitive-map import, then bind tools after.
4. **Pack** → `.paf`:
   `python scripts/paf_packager.py pack --in <flowgraph.json> --flowgraph --name "<Agent>"`
   (or `pack_flowgraph()` in code). Password `simple4u`.
5. **Import** in PAF → My Custom Flows → Import → upload `.paf` → password `simple4u`.
6. **Rebind** (the `.paf` ships no bindings/secrets): bind the MCP-server node +
   pick an LLM in Agent Builder.
7. **Validate** with `validation-gate.md` (importing ≠ correct).

## Adding a domain pack
A domain pack supplies the layer the core consumes: system prompts, the MCP tool
contracts, golden/test data, and the validation scenarios. The bundled **EBS**
pack is `../references/` (paf-platform, oracle-gotchas, interface-catalog, …) +
`../templates/` (a working EBS engine). To target a new system, write an
equivalent pack and reuse this core unchanged.

## Secret-free + `simple4u`
A `.paf` carries no secrets by design (credentials/LLM are bound at import), so
the import password is a convenience convention, not a secret boundary —
`simple4u` unless a tenant requires otherwise (`$PAF_PASSWORD` / `--password`).
