<!-- Syntax Corporation © 2026 — PAF core -->
# PAF 26.4 `.paf` import — format, packager, clone-and-mint

## The `.paf` bundle (what PAF 26.4 imports)
PAF 26.4 imports an encrypted **`.paf`** file (My Custom Flows → Import) — NOT raw
JSON. Reverse-engineered from a genuine 26.4 export, round-trip verified:

```
.paf = base64( [16B salt][12B nonce][AES-256-GCM ct+tag] ),  PBKDF2-HMAC-SHA256 key
plaintext = ZIP{ metadata.json, flows/<FLOWID>_<name>.json }
envelope["data"] = Agent Spec JSON **string** (flowGraph:false, tool-free map)
                 | {nodes,edges} **object**  (flowGraph:true, TOOL-BOUND)
```

**Real flowGraph schema** (`flowGraph:true`, decrypted from a live export):
- nodes typed `agentStep` | `chatInputComponent` | `mcpServer` | `chatOutputComponent`
- the `agentStep` template carries `custom_instruction`, `agent_description`,
  `llmToUse`, `prompt`, `tools` — where `tools.value = [<mcpServer node id>]`
- the `mcpServer` template carries `serverSource` (an index/ref, rebound at import)
- edge `id`s **embed the node ids** they connect

## Packager (`scripts/paf_packager.py`)
`pack_paf` (flow/string) · `pack_flowgraph` (tool-bound object) · `unpack_paf`
(decrypt/inspect) · `clone_flowgraph` · `remap_uuids`. Default password
`simple4u` (`$PAF_PASSWORD` / `--password` to override). CLI:

```bash
python scripts/paf_packager.py pack   --in flowgraph.json --flowgraph --name "My Agent"
python scripts/paf_packager.py pack   --in flow.json                  --name "My Agent"
python scripts/paf_packager.py unpack --in agent.paf      # decrypt + summarize
```

## Clone-and-mint (bulk slate — the 300-agent path)
Export ONE correct **tool-bound** flowGraph from the canvas (or use a template in
`flowgraphs/`), then stamp variants — `clone_flowgraph` remaps **every** node id
everywhere it appears (the `tools→mcpServer` cross-ref AND the edge ids) and
injects the new instruction/description, preserving the MCP wiring:

```python
from paf_packager import clone_flowgraph, pack_flowgraph
clone = clone_flowgraph(template, new_instruction="<system prompt>",
                        new_agent_description="<one-liner>")
open("agent.paf", "wb").write(pack_flowgraph(clone, name="My Agent"))  # password simple4u
```

## Rebind after import (every import + every customer install)
A `.paf` ships **no** MCP/LLM bindings or secrets. After import, in Agent Builder:
bind the **MCP-server node** to the registered server and pick an **LLM**. First
run `scripts/list_mcp_tools.py --url <sse>` so the prompt names tools that exist.

## Verified
Round-trips both modes; wrong password → AES-GCM `InvalidTag`. `clone_flowgraph`
is locked to the real schema by a regression test (built from a decrypted export).
A tool-bound agent minted from a flowGraph template imported and **ran live** on
26.4.

> History: on PAF **25.3.0.0.9** file-import rejected every tool-free Agent Spec
> ("Tools are missing to be declared"); that is **obsolete** on 26.4 via the path
> above.
