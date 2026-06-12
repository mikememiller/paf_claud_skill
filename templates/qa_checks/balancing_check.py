"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 qa_checks/balancing_check.py — Rule 5: output must balance.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Contract: Phase 4 runs the golden record through the engine and writes
   output/golden_output.json = {"header_total": <num>,
                                "lines": [{"amount": <num>, "type": "ITEM|TAX"}, ...]}
 This check FAILS while that fixture is missing — wiring the golden record is
 part of the build, not optional. Override path: $QA_GOLDEN_OUTPUT.
================================================================================
"""
from __future__ import annotations

import json
import os
from pathlib import Path

TOLERANCE = 0.005  # currency rounding


def check() -> list[str]:
    path = Path(os.environ.get("QA_GOLDEN_OUTPUT", "output/golden_output.json"))
    if not path.is_file():
        return [f"golden output fixture missing ({path}) — run the golden record "
                "through the engine in Phase 4 before convergence (Rule 5)."]
    try:
        data = json.loads(path.read_text())
        header = float(data["header_total"])
        lines = data["lines"]
        amounts = [float(ln["amount"]) for ln in lines]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as ex:
        return [f"{path}: unreadable balancing fixture — "
                f"{type(ex).__name__}: {ex}"]
    findings: list[str] = []
    total = sum(amounts)
    if abs(header - total) > TOLERANCE:
        findings.append(f"UNBALANCED: header_total {header:,.2f} != Σ lines "
                        f"{total:,.2f} (Δ {header - total:+,.2f}) — Rule 5.")
    if not any(str(ln.get("type", "")).upper() == "TAX" for ln in lines):
        findings.append("no TAX line in golden output — known-bug #4 "
                        "(dropped tax). If the golden record is genuinely "
                        "tax-exempt, record that in the honesty register and "
                        "set a zero-amount TAX line.")
    return findings
