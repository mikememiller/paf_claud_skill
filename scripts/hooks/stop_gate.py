"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/hooks/stop_gate.py — Stop/SubagentStop hook: the build may not claim
 "done" before the convergence gate clears.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Exit 0 = allow stop. Exit 2 = block (stderr is fed back to the model).
 Never blocks when: stop_hook_active is set (anti-loop guard), the caller is a
 subagent (main session owns convergence), no build_state.json exists (not a
 PAF build), or the ceiling escalated (a session that can never end is worse
 than one that ends early — ESCALATION.md carries the diagnosis).
================================================================================
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _resolve import import_core, read_payload  # noqa: E402


def main() -> int:
    payload = read_payload()
    if payload.get("stop_hook_active"):
        return 0
    if payload.get("agent_id") or payload.get("agent_type"):
        return 0
    if import_core() is None:
        return 0
    from converged import verdict
    root = Path(payload.get("cwd") or os.getcwd())
    code, msg = verdict(root)
    if code == 2:
        print(msg, file=sys.stderr)
        return 2
    if msg:
        print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
