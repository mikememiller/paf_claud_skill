"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/hooks/post_write_lint.py — PostToolUse(Write|Edit) hook: lint PAF
 artifacts the moment they are written, not at Phase 6.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 PostToolUse cannot undo a write; exit 2 surfaces stderr to the model so the
 bug is fixed in the very next turn. Lints only: *.flowgraph.json, *.paf,
 spec.yaml, and *.py under src/|scripts/|qa_checks/. Everything else: silent 0.
================================================================================
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _resolve import import_core, read_payload  # noqa: E402

LINT_PY_PARENTS = {"src", "scripts", "qa_checks"}


def lintable(path: Path) -> bool:
    if path.suffix == ".paf" or path.name in ("spec.yaml", "spec.yml"):
        return True
    if path.name.endswith(".flowgraph.json"):
        return True
    if path.suffix == ".py" and LINT_PY_PARENTS & {p.name for p in path.parents}:
        return True
    return False


def main() -> int:
    payload = read_payload()
    if payload.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return 0
    fp = (payload.get("tool_input") or {}).get("file_path")
    if not fp:
        return 0
    path = Path(fp)
    if not path.is_file() or not lintable(path):
        return 0
    if import_core() is None:
        return 0
    import lint_paf
    target = lint_paf._parse_version(os.environ.get("PAF_TARGET_VERSION", "26.4"))
    findings, _notes = lint_paf.lint_path(path, target)
    if findings:
        print("\n".join(f"FINDING: {f}" for f in findings), file=sys.stderr)
        print("fix now — this artifact fails the QA gate as written.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
