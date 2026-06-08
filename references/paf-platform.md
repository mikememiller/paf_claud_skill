<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# PAF platform & MCP integration (PAF 26.4 + OCI managed MCP)

## Default integration: OCI Database Tools Managed MCP
A **fully managed, multi-tenant OCI service** that exposes Oracle DBs to MCP
clients over **HTTPS**, secured by **OAuth 2.0 in IAM Identity Domains** (or
Personal Access Tokens), access governed by **application roles**, with
**auditing**. It reaches targets via **Database Tools Connections** — including
**non-Autonomous 19c on DBaaS/Exadata** (so EBS 19c qualifies). Connectivity
(wallet/secret in OCI Vault, private endpoint into the VCN) is handled by the
service — **no broker container, no DB link, no thick-mode in production.**

**Expose domain logic as governed tools (not free-form SQL):**
- **Custom PL/SQL tools** — wrap each `XX…` package function (e.g.
  `match_code_and_validate(p_json)`) as a named MCP tool returning JSON.
- **SQL Reports** — published, parameterized SELECTs surfaced as MCP tools, so
  the LLM never authors SQL. Use these for the read lookups.
- **Built-in tools** (list schemas / objects / run SELECT) exist but prefer the
  governed custom tools/SQL Reports for determinism + least privilege.
Bound the connection to a **least-privilege EBS DB user** (EXECUTE on `XX…`,
SELECT on the needed objects) — governance via DB grants.

**Writes:** keep interface **writes off the MCP path** by default (agent reads +
matches + codes + QA via MCP; the **load** runs as a standard Open Interface
Import or a governed PL/SQL job). Only put DML on the MCP if a **DML-capable
custom tool** is confirmed at install (verify item).

**Topology:** `PAF (ADB 26ai sidecar) → [HTTPS+OAuth/IAM] → OCI Managed MCP →
[Database Tools Connection, private endpoint] → EBS 19c XX… PL/SQL`. ADB hosts
PAF only and is **not in the data path**.

**Fallbacks (only if managed MCP isn't available):** a self-hosted thin SSE
FastMCP service (`mcp.run(transport="streamable-http", host="0.0.0.0")`,
TLS+bearer, python-oracledb thick → calls `XX…`); or ORDS/REST on EBS → PAF
OpenAPI tool (v2/v3 **JSON**, GET/POST).

## Importing on PAF 26.4 — the encrypted `.paf` bundle (this is how delivery scales)
PAF **26.4** imports an encrypted **`.paf`** file (My Custom Flows → Import) — NOT
a raw `.json`. Mint it with `scripts/paf_packager.py` (default password
**`simple4u`**). Format (reverse-engineered from a real 26.4 export, round-trip
verified):

```
.paf = base64( [16B salt][12B nonce][AES-256-GCM ct+tag] ),  PBKDF2-HMAC-SHA256 key
plaintext = ZIP{ metadata.json, flows/<FLOWID>_<name>.json }
envelope["data"] = Agent Spec JSON **string** (flowGraph:false, tool-free)
                 | {nodes,edges} **object**  (flowGraph:true, TOOL-BOUND: MCP node + edges)
```

`pack_paf()` = flow/string mode; `pack_flowgraph()` = tool-bound; `unpack_paf()`
inspects any `.paf`. Verified: both modes round-trip; wrong password → AES-GCM
`InvalidTag`. A tool-bound agent minted from a flowGraph template imported and
**ran live on 26.4**.

**Workflow:**
1. Build the Agent Spec content (`build_agentspec.py` → `flow.json`), **or** start
   from a known-good exported flowGraph template.
2. `python scripts/paf_packager.py pack --in flow.json --name "<Agent>"` → `.paf`
   (or `clone_flowgraph` + `pack_flowgraph` for tool-bound).
3. PAF → **My Custom Flows → Import** → upload `.paf` → password `simple4u`.
4. **Rebind** (every import + every customer install): bind the **MCP-server node**
   + pick an **OCI LLM** in Agent Builder. The `.paf` carries NO bindings/secrets
   by design. First run `scripts/list_ebsvision_tools.py` so the prompt names tools
   that actually exist.
5. **Validate** with `references/validation-gate.md` (imports ≠ correct).

**Scaling a slate (bulk-mint):** export ONE correct tool-bound flowGraph from the
canvas, then for each agent
`clone_flowgraph(template, new_instruction=…, new_agent_description=…)` (fresh node
IDs everywhere, tool wiring preserved) → `pack_flowgraph` → import. That's the
300-agent path.

### Default password `simple4u` (convention, not a secret boundary)
The `.paf` is **secret-free by design** (Instance Principal + rebind at import),
so a shared, well-known import password just makes bulk import frictionless.
Override with `$PAF_PASSWORD` or `password=` only if a bundle must ever carry a
secret — it shouldn't.

## Canvas — author the first template (and a valid fallback)
Build natively when you need to *create* the tool-bound template to clone, or as a
fallback: `Chat/File/CSV input → Prompt → Agent (tool-capable LLM + MCP Server
node → managed MCP) → Condition (route on QA status) → Email/Chat Output`.
Processing nodes: Type Convert, Parser, Combine JSON, Regex, Calculator. Test in
**Playground**; **Publish** → REST API (hook for an exception console / KPI
dashboard). Then **Export** the flow (`.paf`) to get a clone-able template.

**Register the managed MCP in PAF:** MCP Servers tab → Add → enter the managed
MCP **URL** + **OAuth** (authorization-code) or token; tools auto-discover;
default node timeout 45 s; multiple MCP servers can attach to one Agent.

## History (SUPERSEDED): import was blocked on PAF 25.3.0.0.9
On **25.3.0.0.9**, file-import rejected every tool-free Agent Spec with *"Tools
are missing to be declared,"* and the LangGraph/AutoGen adapters wrapped every
node as a ToolNode — so we concluded **canvas-only** and drafted an Oracle SR.
**That conclusion is obsolete on 26.4**, where the encrypted `.paf` path above
works (incl. tool-bound). Archived experiments live in the AP reference project
under `paf/_archive_25_3/`.

## Manual facts to honor
- **Tool-capable LLM required** (OCI GenAI `xai.grok-4`/`openai.gpt-5`, OpenAI
  `gpt-4o`). Google **Vertex** models don't support tool use — avoid.
- **PAF = $0** (no-cost add-on to **AI Database 26ai**). Prereqs:
  `max_string_size=EXTENDED`; OCI Marketplace deploy = Flex ≥8 OCPU/16 GB/120 GB
  (500 GB rec), **:8080**, **Podman**, OL8/macOS, public/private subnet,
  self-signed TLS by default; dedicated DB user with set grants.
- **26.4 DOES export flows** (`.paf`) from the UI → you CAN round-trip a template
  (export → `clone_flowgraph` → re-import). (25.3 had no export.)
- **No built-in agent monitoring or human-approval node yet** → a **KPI
  dashboard** and **exception-review console** are real add-ons (consume the
  published REST API). **Datasets/Prompt Lab** tune prompts but are not a scored
  eval harness → our pytest + golden + parity tests + the validation gate remain
  the QA mechanism.

## Install-time verify items
PAF release **≥ 26.4** (for `.paf` import) · managed-MCP support for the target
19c (region/edition) · DML-capable custom tool (else load via import) ·
managed-MCP pricing line for the BOM · PAF↔OCI OAuth flow completes · the import
password convention (`simple4u` unless the customer requires per-tenant).

Sources: OCI Database Tools MCP Server docs; PAF manual; a genuine PAF **26.4**
`.paf` export (format reverse-engineered + round-trip verified).
