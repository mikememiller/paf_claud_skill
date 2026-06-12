"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 qa_checks/parity_check.py — known-bug #12: Python↔PL/SQL drift.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Contract: Phase 4 writes the golden record's result from BOTH engines:
   output/parity_python.json  (the Python reference engine)
   output/parity_plsql.json   (the EBS XX… package via utPLSQL export)
 This check FAILS while either side is missing — parity is the test oracle
 for the production PL/SQL, not a nice-to-have.
================================================================================
"""
from __future__ import annotations

import json
from pathlib import Path

PY_OUT = Path("output/parity_python.json")
PLSQL_OUT = Path("output/parity_plsql.json")
FLOAT_TOL = 0.005


def _diff(a: object, b: object, path: str, out: list[str]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: only in PL/SQL output")
            elif k not in b:
                out.append(f"{path}.{k}: only in Python output")
            else:
                _diff(a[k], b[k], f"{path}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} (py) != {len(b)} (plsql)")
        for i, (x, y) in enumerate(zip(a, b)):
            _diff(x, y, f"{path}[{i}]", out)
    else:
        try:
            if abs(float(a) - float(b)) <= FLOAT_TOL:
                return
        except (TypeError, ValueError):
            pass
        if a != b:
            out.append(f"{path}: {a!r} (py) != {b!r} (plsql)")


def check() -> list[str]:
    missing = [str(p) for p in (PY_OUT, PLSQL_OUT) if not p.is_file()]
    if missing:
        return [f"parity outputs missing ({', '.join(missing)}) — run the "
                "Python↔PL/SQL parity step on the golden record "
                "(qa-and-bugfixing #5/#12) before convergence."]
    try:
        py = json.loads(PY_OUT.read_text())
        pl = json.loads(PLSQL_OUT.read_text())
    except (OSError, json.JSONDecodeError) as ex:
        return [f"parity fixtures unreadable — {type(ex).__name__}: {ex}"]
    diffs: list[str] = []
    _diff(py, pl, "$", diffs)
    return [f"Python↔PL/SQL DRIFT at {d}" for d in diffs[:20]] + (
        [f"... and {len(diffs) - 20} more drift points"] if len(diffs) > 20 else []
    )
