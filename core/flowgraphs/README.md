<!-- Syntax Corporation © 2026 — PAF core · flowgraphs -->
# Clone-able tool-bound flowGraph templates

Real PAF **26.4** flowGraphs (decrypted from genuine exports; **secret-free** —
`serverSource` is an index rebound at import, no URLs/credentials). Use them as
clone sources for the bulk-mint path (`clone_flowgraph` + `pack_flowgraph`, see
`../paf-import.md`).

| File | Agent | Shape |
|------|-------|-------|
| `ebs_ap_3way_match.flowgraph.json` | EBS AP 3-Way Match | agentStep + chatInput + mcpServer + chatOutput (4 nodes, 3 edges) |
| `month_end_close_readiness.flowgraph.json` | EBS Month-End Close Readiness | same shape |

Both are the standard tool-bound shape: a `chatInputComponent` → `agentStep`
(LLM + `tools.value=[mcpServer id]`) → `chatOutputComponent`, with a `mcpServer`
node wired to the agent.

## Use
```python
import json
from paf_packager import clone_flowgraph, pack_flowgraph     # ../scripts
tmpl = json.load(open("ebs_ap_3way_match.flowgraph.json"))
clone = clone_flowgraph(tmpl, new_instruction="<your agent's system prompt>",
                        new_agent_description="<one-liner>")
open("my_agent.paf", "wb").write(pack_flowgraph(clone, name="My Agent"))
```
Then import (password `simple4u`) and **rebind** the MCP server + LLM.

> These are EBS-domain examples, but the clone mechanism is domain-neutral — the
> structure is identical for any system; only the instruction + the bound MCP
> server change. Author a non-EBS template once on the canvas, export it, drop it
> here, and clone.
