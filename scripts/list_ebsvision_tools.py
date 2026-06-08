#!/usr/bin/env python3
# Syntax Corporation © 2026 — EBS AP PAF · paf/list_ebsvision_tools.py · v1.2.0 · 2026-06-08
"""
list_ebsvision_tools.py
Connect to an MCP server over SSE and print every tool it exposes (name,
description, input schema). Run this LOCALLY, where the EBSVision host
(10.193.1.36) is reachable -- the cloud build env cannot reach internal IPs.

This is step 0 of the validation gate AND of every customer install: you must
know what the ERP MCP server actually exposes before you can trust an agent's
prompt that names tools like `query_ap_invoices` or `execute_stage_to_payables`.

Setup (once):
    pip install "mcp>=1.0"
Run:
    python list_ebsvision_tools.py
    python list_ebsvision_tools.py --url http://10.193.1.36:3000/sse
Output:
    - human-readable list to the screen
    - ebsvision_tools.json  (full schemas -- send this back for prompt alignment)
"""
import argparse, asyncio, json, sys

DEFAULT_URL = "http://10.193.1.36:3000/sse"


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
            tools = []
            for t in resp.tools:
                tools.append({
                    "name": t.name,
                    "description": (t.description or "").strip(),
                    "input_schema": t.inputSchema,
                })
            return tools


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL, help="MCP SSE endpoint")
    ap.add_argument("--out", default="ebsvision_tools.json")
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
        print(f"EBSVision exposes {len(tools)} tool(s):\n")
        for t in tools:
            params = list((t["input_schema"] or {}).get("properties", {}).keys())
            print(f"  - {t['name']}({', '.join(params)})")
            if t["description"]:
                print(f"      {t['description'][:100]}")
    with open(args.out, "w") as f:
        json.dump(tools, f, indent=2)
    print(f"\nFull schemas written to {args.out} -- send that file back for prompt alignment.")


if __name__ == "__main__":
    main()
