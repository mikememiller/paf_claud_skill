"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/converged.py — the convergence gate. One verdict, three callers.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Reads build_state.json and answers: may this build stop?

   exit 0  → yes (converged, escalated-by-ceiling, or no PAF build here)
   exit 2  → no  (loop not converged — findings summary on stderr)

 Callers:
   * the Stop hook (.claude/paf-hooks/stop_gate.py) — exit 2 blocks the stop
   * Cowork / claude.ai (no hooks): run procedurally before claiming done
   * CI: `--strict` makes an escalation exit 1 instead of 0

 Design notes:
   * Absent build_state.json → exit 0 ALWAYS. The gate must never block
     non-PAF work just because the skill is loaded.
   * Ceiling reached → exit 0 + escalation notice. Blocking forever would
     trade one failure mode (premature "done") for a worse one (a session
     that can never end). ESCALATION.md carries the diagnosis to the human.
================================================================================
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_state import BuildState  # noqa: E402


def verdict(root: Path, strict: bool = False) -> tuple[int, str]:
    """Return (exit_code, message). Message goes to stderr on block."""
    try:
        state = BuildState.load(root)
    except RuntimeError as ex:
        return 2, f"convergence gate: {ex} — fix or delete the state file."
    if state is None:
        return 0, ""
    if state.is_converged():
        return 0, f"convergence gate: {state.summary()}"
    if state.escalated or state.at_ceiling():
        code = 1 if strict else 0
        return code, (
            f"convergence gate: {state.summary()} — ceiling reached, "
            "ESCALATION.md written; human decision required before more rounds."
        )
    top = state.open_findings[:5]
    listing = "".join(f"\n  - {f}" for f in top) or "\n  - (run qa_pass.py to enumerate)"
    more = (
        f"\n  ... and {len(state.open_findings) - 5} more"
        if len(state.open_findings) > 5
        else ""
    )
    return 2, (
        f"convergence gate BLOCKED: {state.summary()}.\n"
        f"Open findings:{listing}{more}\n"
        "Phase 6 is not done: fix each finding, add a regression test for it, "
        "then re-run `python scripts/qa/qa_pass.py`. The build may stop after "
        f"{state.required_clean} consecutive clean rounds."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    ap.add_argument("--strict", action="store_true", help="escalation exits 1")
    ap.add_argument("--report", action="store_true", help="always print verdict")
    args = ap.parse_args(argv)

    code, msg = verdict(Path(args.root).resolve(), strict=args.strict)
    if msg and (code != 0 or args.report):
        print(msg, file=sys.stderr if code == 2 else sys.stdout)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
