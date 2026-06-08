"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/qa_pass.py — one QA pass over a generated agent project.
 Version : 1.0.0   Build : 2026.06.03   Date : 2026-06-03
--------------------------------------------------------------------------------
 Runs the deterministic, repeatable checks from references/qa-and-bugfixing.md
 and writes QA_REPORT.md. Phase 6 calls this in a loop until two consecutive
 clean rounds. Designed to run from a generated project root.

   python qa_pass.py            # hermetic checks
   EBS_RUN_LIVE=1 EBS_PASSWORD=... python qa_pass.py --live
================================================================================
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
BANNER_RE = re.compile(r"Syntax Corporation .* 2026")


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()

    findings: list[str] = []

    rc, out = run([sys.executable, "-m", "pytest", "-q", "-m", "not live"])
    if rc != 0:
        findings.append("hermetic tests FAILED:\n" + out[-2000:])

    if args.live:
        rc, out = run([sys.executable, "-m", "pytest", "-q", "-m", "live"])
        if rc != 0:
            findings.append("live tests FAILED:\n" + out[-2000:])

    rc, out = run([sys.executable, "-m", "py_compile",
                   *[str(p) for p in ROOT.rglob("src/**/*.py")]])
    if rc != 0:
        findings.append("py_compile FAILED:\n" + out[-1000:])

    missing = check_headers()
    if missing:
        findings.append("missing Syntax file-header banner: " + ", ".join(missing))

    # NOTE: extend with — golden-record balancing, Python<->PL/SQL parity,
    # negative paths, clean-venv install, document/visual QA (see
    # references/qa-and-bugfixing.md). These need the generated project's
    # fixtures + a live connection, so are wired per build.

    status = "PASS" if not findings else "FAIL"
    report = [f"# QA_REPORT — {status}", ""]
    if findings:
        report += [f"## Finding {i+1}\n{f}\n" for i, f in enumerate(findings)]
    else:
        report.append("All automated checks passed this round.")
    report += ["", "## Honesty register",
               "- List here anything not verifiable in-environment "
               "(managed-MCP DML, PAF OAuth, GA coverage, slide rendering)."]
    Path("QA_REPORT.md").write_text("\n".join(report))
    print(f"QA_REPORT.md written: {status} ({len(findings)} findings)")
    return 0 if status == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
