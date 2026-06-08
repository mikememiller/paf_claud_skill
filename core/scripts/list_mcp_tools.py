#!/usr/bin/env python3
# Syntax Corporation © 2026 — PAF core · core/scripts/list_mcp_tools.py · v1.0.0 · 2026-06-08
"""
list_mcp_tools.py — discover the tools an MCP server exposes (over SSE).

Step 0 of every PAF agent build / customer install: know the REAL tool names +
schemas the target MCP server exposes before you trust an agent prompt that names
tools. Align the prompt to this list, then bind the MCP-server node after `.paf`
import (the "rebind" step). Domain-neutral — point it at any MCP SSE endpoint
(EBS ERP server, a SaaS MCP, your own FastMCP service, …).

Run it where the MCP host is reachable (a cloud build env can't reach internal
IPs / private endpoints).

Setup (once):
    pip install "mcp>=1.0"
Run:
    python list_mcp_tools.py --url http://<host>:<port>/sse
Output:
    - human-readable list to the screen
    - mcp_tools.json  (full schemas -- feed back for prompt alignment)
"""
import argparse, asyncio, json, sys

DEFAULT_URL = "http://localhost:3000/sse"   # override with --url for your MCP SSE endpoint


async def discover(url: str) -> list[dict]:
    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
    except ImportError:
        sys.exit("Missing dependency. Run:  pip install \"mcp>=1.0\"")

    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resp = await session.list_tools()
            return [{"name": t.name,
                     "description": (t.description or "").strip(),
                     "input_schema": t.inputSchema} for t in resp.tools]


def main():
    ap = argparse.ArgumentParser(description="List the tools an MCP server exposes (SSE).")
    ap.add_argument("--url", default=DEFAULT_URL, help="MCP SSE endpoint")
    ap.add_argument("--out", default="mcp_tools.json")
    args = ap.parse_args()

    print(f"Connecting to {args.url} ...\n")
    try:
        tools = asyncio.run(discover(args.url))
    except Exception as e:
        sys.exit(f"Connection/handshake failed: {e!r}\n"
                 f"Check the URL, that the server is up, and that this host can reach it.")

    if not tools:
        print("Connected, but the server exposed ZERO tools.")
    else:
        print(f"Server exposes {len(tools)} tool(s):\n")
        for t in tools:
            params = list((t["input_schema"] or {}).get("properties", {}).keys())
            print(f"  - {t['name']}({', '.join(params)})")
            if t["description"]:
                print(f"      {t['description'][:100]}")
    with open(args.out, "w") as f:
        json.dump(tools, f, indent=2)
    print(f"\nFull schemas written to {args.out} -- feed back for prompt alignment.")


if __name__ == "__main__":
    main()
