"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/hooks/_resolve.py — locate the QA core from any installed location.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Hook wrappers run from two layouts:
   skill repo : <skill>/scripts/hooks/*.py   -> core in <skill>/scripts/
   scaffolded : <proj>/.claude/paf-hooks/*.py -> core in <proj>/scripts/qa/
 read_payload() parses the hook's stdin JSON tolerantly: a hook must NEVER
 crash a session — on garbage it returns {} and callers exit 0.
================================================================================
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def core_dir() -> Path | None:
    here = Path(__file__).resolve().parent
    for cand in (here.parents[1] / "scripts" / "qa",   # <proj>/.claude/paf-hooks
                 here.parent):                          # <skill>/scripts/hooks
        if (cand / "build_state.py").is_file():
            return cand
    return None


def import_core():
    cand = core_dir()
    if cand is None:
        return None
    sys.path.insert(0, str(cand))
    return cand


def read_payload() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}
