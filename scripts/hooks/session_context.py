"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/hooks/session_context.py — SessionStart hook: load environment ground
 truth into context so version discipline is read, not remembered.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 SessionStart stdout becomes context the model can see. Emits ONLY inside a
 PAF build project (spec.yaml / build_state.json / conn.json present);
 otherwise stays silent so unrelated sessions get zero noise.
================================================================================
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _resolve import import_core, read_payload  # noqa: E402


def main() -> int:
    payload = read_payload()
    root = Path(payload.get("cwd") or os.getcwd())
    markers = [root / "spec.yaml", root / "build_state.json", root / "conn.json"]
    if not any(m.is_file() for m in markers):
        return 0

    lines = ["[PAF build context — injected by ebs-paf-agent skill]"]
    target = os.environ.get("PAF_TARGET_VERSION", "26.4")
    conn = {}
    for cand in (root / "conn.json", root / "templates" / "conn.example.json"):
        if cand.is_file():
            try:
                conn = json.loads(cand.read_text())
                break
            except (OSError, json.JSONDecodeError):
                pass
    paf_ver = conn.get("paf_version") or target
    lines.append(f"- Target PAF version: {paf_ver} "
                 "(file import requires 26.4; 25.3 rejects it)")
    if conn.get("mcp_url"):
        lines.append(f"- Registered MCP endpoint: {conn['mcp_url']}")

    spec_file = root / "spec.yaml"
    if spec_file.is_file():
        try:
            import yaml
            meta = (yaml.safe_load(spec_file.read_text()) or {}).get("meta", {})
            if isinstance(meta, dict) and meta:
                ident = meta.get("domain") or meta.get("name") or ""
                if ident:
                    lines.append(f"- Build: {ident}")
        except Exception:
            pass

    if import_core() is not None:
        from build_state import BuildState
        try:
            state = BuildState.load(root)
            if state is not None:
                lines.append(f"- Convergence: {state.summary()}")
        except RuntimeError as ex:
            lines.append(f"- Convergence state unreadable: {ex}")

    lines += [
        "- Invariants: bindings (MCP/LLM) never travel in any artifact — rebind "
        "after import; COUNT(*) not num_rows; artifacts lint on write; the "
        "build may not claim done until `python scripts/qa/converged.py` exits 0.",
    ]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
