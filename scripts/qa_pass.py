"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/qa_pass.py — one QA pass over a generated agent project.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Runs the deterministic, repeatable checks from references/qa-and-bugfixing.md,
 writes QA_REPORT.md, and RECORDS THE ROUND in build_state.json (the Phase 6
 loop is data — see build_state.py / converged.py). Run from the generated
 project root.

   python qa_pass.py                 # hermetic checks
   EBS_RUN_LIVE=1 EBS_PASSWORD=... python qa_pass.py --live
   python qa_pass.py --json          # machine-readable summary
   python qa_pass.py --no-state      # do not record the round

 v2 adds:
   * build_state.json round recording (convergence = 2 consecutive clean)
   * regression-test-delta rule: after a FAIL round, the next round must
     ADD tests (every fix carries a regression test) — enforced, not advised
   * artifact lint (lint_paf.py) over *.flowgraph.json, *.paf, spec.yaml
   * pluggable per-build checks: qa_checks/*.py exposing check() -> list[str]
     (the scaffold seeds balancing + parity checks wired to the golden record)
================================================================================
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_state import BuildState  # noqa: E402
import lint_paf  # noqa: E402

ROOT = Path.cwd()
BANNER_RE = re.compile(r"Syntax Corporation .* 2026")
COLLECTED_RE = re.compile(r"(\d+)\s+tests?\s+collected")


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def check_headers() -> list[str]:
    """Every source/script file must carry the Syntax banner."""
    missing = []
    for f in list(ROOT.rglob("src/**/*.py")) + list(ROOT.rglob("scripts/**/*.py")):
        if BANNER_RE.search(f.read_text(errors="ignore")) is None:
            missing.append(str(f.relative_to(ROOT)))
    return missing


def count_tests() -> int:
    """Collected-test count — the regression-rule currency."""
    rc, out = run([sys.executable, "-m", "pytest", "-q", "--collect-only"])
    m = COLLECTED_RE.search(out)
    if m:
        return int(m.group(1))
    return sum(1 for line in out.splitlines() if "::" in line)


def lint_artifacts() -> tuple[list[str], list[str]]:
    """Run lint_paf over every PAF artifact in the project."""
    findings: list[str] = []
    notes: list[str] = []
    targets = (
        sorted(ROOT.rglob("*.flowgraph.json"))
        + sorted(ROOT.rglob("*.paf"))
        + [p for p in (ROOT / "spec.yaml", ROOT / "spec.yml") if p.is_file()]
    )
    import os
    target_ver = lint_paf._parse_version(os.environ.get("PAF_TARGET_VERSION", "26.4"))
    for t in targets:
        f, n = lint_paf.lint_path(t, target_ver)
        findings += f
        notes += n
    return findings, notes


def run_pluggable_checks() -> list[str]:
    """qa_checks/*.py — per-build checks (balancing, parity, ...)."""
    findings: list[str] = []
    for mod_path in sorted(ROOT.glob("qa_checks/*.py")):
        if mod_path.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(mod_path.stem, mod_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            check = getattr(mod, "check", None)
            if check is None:
                findings.append(f"qa_checks/{mod_path.name}: no check() function")
                continue
            result = check()
            if not isinstance(result, list):
                findings.append(f"qa_checks/{mod_path.name}: check() must return "
                                f"list[str], got {type(result).__name__}")
                continue
            findings += [f"qa_checks/{mod_path.name}: {msg}" for msg in result]
        except Exception as ex:  # a broken check is itself a finding
            findings.append(f"qa_checks/{mod_path.name}: crashed — "
                            f"{type(ex).__name__}: {str(ex)[:200]}")
    return findings


def enforce_test_delta(state: BuildState | None, current_count: int) -> list[str]:
    """After a FAIL round, the next round must add tests (regression rule)."""
    if state is None or not state.history:
        return []
    prev = state.history[-1]
    if prev["status"] == "FAIL" and current_count <= prev["test_count"]:
        return [
            "regression-test rule violated: previous round FAILED with "
            f"{prev['test_count']} tests; this round has {current_count}. "
            "Every fix must add a regression test (qa-and-bugfixing.md)."
        ]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--no-state", action="store_true",
                    help="do not record this round in build_state.json")
    args = ap.parse_args()

    findings: list[str] = []
    notes: list[str] = []

    prior_state = BuildState.load(ROOT)
    test_count = count_tests()

    rc, out = run([sys.executable, "-m", "pytest", "-q", "-m", "not live"])
    if rc != 0:
        findings.append("hermetic tests FAILED:\n" + out[-2000:])

    if args.live:
        rc, out = run([sys.executable, "-m", "pytest", "-q", "-m", "live"])
        if rc != 0:
            findings.append("live tests FAILED:\n" + out[-2000:])

    py_files = [str(p) for p in ROOT.rglob("src/**/*.py")]
    if py_files:
        rc, out = run([sys.executable, "-m", "py_compile", *py_files])
        if rc != 0:
            findings.append("py_compile FAILED:\n" + out[-1000:])

    missing = check_headers()
    if missing:
        findings.append("missing Syntax file-header banner: " + ", ".join(missing))

    lint_f, lint_n = lint_artifacts()
    findings += lint_f
    notes += lint_n

    findings += run_pluggable_checks()
    findings += enforce_test_delta(prior_state, test_count)

    status = "PASS" if not findings else "FAIL"

    report = [f"# QA_REPORT — {status}", ""]
    if findings:
        report += [f"## Finding {i + 1}\n{f}\n" for i, f in enumerate(findings)]
    else:
        report.append("All automated checks passed this round.")
    if notes:
        report += ["", "## Notes (informational)", *(f"- {n}" for n in notes)]
    report += ["", "## Honesty register",
               "- List here anything not verifiable in-environment "
               "(managed-MCP DML, PAF OAuth, GA coverage, slide rendering)."]
    Path("QA_REPORT.md").write_text("\n".join(report) + "\n")

    state_line = ""
    if not args.no_state:
        state = prior_state or BuildState()
        state.record_round(status, findings, test_count)
        state.save(ROOT)
        state_line = state.summary()

    if args.as_json:
        print(json.dumps({"status": status, "findings": len(findings),
                          "test_count": test_count, "state": state_line}))
    else:
        print(f"QA_REPORT.md written: {status} ({len(findings)} findings, "
              f"{test_count} tests collected)")
        if state_line:
            print(f"build_state: {state_line}")
    return 0 if status == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
