"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/hooks/bash_guard.py — PreToolUse(Bash) hook: PAF-specific guards.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Narrow, high-precision blocks only (a false block costs more than a miss —
 broader policy lives in the user's global guard hooks):
   1. num_rows read from *_TABLES dictionary views  -> COUNT(*) (gotcha #5)
   2. DROP/TRUNCATE TABLE on standard EBS schema prefixes -> Rule 4
 DML (INSERT/UPDATE/DELETE) is deliberately NOT blocked: governed interface
 loads are legitimate; that judgment belongs to QA, not a regex.
================================================================================
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _resolve import read_payload  # noqa: E402

NUM_ROWS = re.compile(r"num_rows", re.IGNORECASE)
DICT_VIEWS = re.compile(r"\b(all|dba|user)_tables\b", re.IGNORECASE)
BASE_DDL = re.compile(
    r"\b(drop|truncate)\s+table\s+(apps\.)?"
    r"(ap_|ar_|gl_|po_|rcv_|inv_|mtl_|hr_|per_|wip_|bom_|ont_|fnd_)\w*",
    re.IGNORECASE,
)


def main() -> int:
    payload = read_payload()
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = (payload.get("tool_input") or {}).get("command", "")
    if NUM_ROWS.search(cmd) and DICT_VIEWS.search(cmd):
        print("blocked: num_rows is stale statistics — confirm row counts with "
              "COUNT(*) (oracle-gotchas #5).", file=sys.stderr)
        return 2
    m = BASE_DDL.search(cmd)
    if m:
        print(f"blocked: {m.group(0)!r} — read-only by default; never touch EBS "
              "base tables (Rule 4). Interface loads run via the governed "
              "import, not ad-hoc DDL.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
