"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/build_state.py — the Phase 6 convergence loop as data, not prose.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Tracks the iterative QA bug-hunt (references/qa-and-bugfixing.md) in
 build_state.json at the generated project root. qa_pass.py records each round;
 converged.py / the Stop hook read it. Convergence = `required_clean`
 consecutive clean rounds (default 2). A `ceiling` (default 5) stops thrashing:
 at the ceiling the build ESCALATES to a human instead of looping forever.

   python build_state.py init [--ceiling 5] [--required-clean 2]
   python build_state.py record --status PASS|FAIL --findings N --test-count N
   python build_state.py show
================================================================================
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

STATE_FILE = "build_state.json"
ESCALATION_FILE = "ESCALATION.md"
SCHEMA = 1


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


@dataclass
class BuildState:
    """Convergence state for one agent build (one project root)."""

    schema: int = SCHEMA
    phase: str = "qa"
    qa_round: int = 0
    consecutive_clean: int = 0
    required_clean: int = 2
    ceiling: int = 5
    last_test_count: int = 0
    last_status: str = "NONE"
    open_findings: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    escalated: bool = False
    updated_at: str = field(default_factory=_now)

    # ---------------------------------------------------------------- queries
    def is_converged(self) -> bool:
        return self.consecutive_clean >= self.required_clean

    def at_ceiling(self) -> bool:
        return self.qa_round >= self.ceiling and not self.is_converged()

    # ---------------------------------------------------------------- updates
    def record_round(self, status: str, findings: list[str], test_count: int) -> None:
        """Record one QA round. status: PASS (no findings) or FAIL."""
        if status not in ("PASS", "FAIL"):
            raise ValueError(f"status must be PASS or FAIL, got {status!r}")
        self.qa_round += 1
        self.consecutive_clean = self.consecutive_clean + 1 if status == "PASS" else 0
        self.open_findings = list(findings)
        self.history.append(
            {
                "round": self.qa_round,
                "status": status,
                "findings": len(findings),
                "test_count": test_count,
                "ts": _now(),
            }
        )
        self.last_test_count = test_count
        self.last_status = status
        self.updated_at = _now()
        if self.is_converged():
            self.phase = "converged"
        elif self.at_ceiling():
            self.escalated = True
            self.phase = "escalated"

    # ------------------------------------------------------------- persistence
    @classmethod
    def load(cls, root: Path | None = None) -> "BuildState | None":
        path = (root or Path.cwd()) / STATE_FILE
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as ex:
            raise RuntimeError(f"unreadable {path}: {ex}") from ex
        known = {f for f in cls.__dataclass_fields__}  # tolerate additive fields
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self, root: Path | None = None) -> Path:
        path = (root or Path.cwd()) / STATE_FILE
        path.write_text(json.dumps(asdict(self), indent=2) + "\n")
        if self.escalated:
            self._write_escalation(path.parent)
        return path

    def _write_escalation(self, root: Path) -> None:
        recent = self.history[-min(3, len(self.history)) :]
        lines = [
            "# ESCALATION — QA loop ceiling reached",
            "",
            f"Round {self.qa_round} of ceiling {self.ceiling}; convergence requires "
            f"{self.required_clean} consecutive clean rounds (have {self.consecutive_clean}).",
            "The loop is stopped deliberately: repeated rounds are not converging and",
            "a human decision is cheaper than more iterations.",
            "",
            "## Open findings",
            *(f"- {f}" for f in self.open_findings or ["(none recorded)"]),
            "",
            "## Last rounds",
            *(
                f"- round {h['round']}: {h['status']} "
                f"({h['findings']} findings, {h['test_count']} tests)"
                for h in recent
            ),
            "",
            "Decide: raise the ceiling, change approach, or descope — then re-run",
            "`python scripts/qa/qa_pass.py` to resume.",
        ]
        (root / ESCALATION_FILE).write_text("\n".join(lines) + "\n")

    # ------------------------------------------------------------------ report
    def summary(self) -> str:
        state = (
            "CONVERGED"
            if self.is_converged()
            else ("ESCALATED" if self.escalated else "IN PROGRESS")
        )
        return (
            f"{state}: round {self.qa_round}, "
            f"{self.consecutive_clean}/{self.required_clean} consecutive clean, "
            f"{len(self.open_findings)} open finding(s), "
            f"{self.last_test_count} tests, ceiling {self.ceiling}"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--ceiling", type=int, default=5)
    p_init.add_argument("--required-clean", type=int, default=2)

    p_rec = sub.add_parser("record")
    p_rec.add_argument("--status", required=True, choices=["PASS", "FAIL"])
    p_rec.add_argument("--findings", type=int, default=0)
    p_rec.add_argument("--test-count", type=int, default=0)

    sub.add_parser("show")
    args = ap.parse_args(argv)

    if args.cmd == "init":
        state = BuildState(ceiling=args.ceiling, required_clean=args.required_clean)
        state.save()
        print(f"{STATE_FILE} initialized: {state.summary()}")
        return 0

    state = BuildState.load()
    if args.cmd == "show":
        if state is None:
            print(f"no {STATE_FILE} in {Path.cwd()}")
            return 1
        print(state.summary())
        return 0

    # record
    if state is None:
        state = BuildState()
    placeholder = [f"finding #{i + 1} (see QA_REPORT.md)" for i in range(args.findings)]
    state.record_round(args.status, placeholder, args.test_count)
    state.save()
    print(state.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
