"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/scaffold_enforcement.py — install the enforcement layer into a build.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Run once in Phase 2 (after copying templates/ into the new project repo):

   python <skill>/scripts/scaffold_enforcement.py --target /path/to/project
          [--settings-hooks] [--init-state] [--ceiling 5]

 Installs (idempotent — overwrites only its own managed copies):
   <proj>/scripts/qa/        build_state, converged, lint_paf, qa_pass,
                             paf_packager (self-contained QA core)
   <proj>/.claude/paf-hooks/ the hook entry scripts (project-relative — the
                             SKILL.md frontmatter hooks call these)
   <proj>/.claude/agents/    paf-validator, paf-deliverables, paf-discovery
                             (project subagents take precedence — by design)
   <proj>/qa_checks/         balancing_check, parity_check (seeded only if
                             absent: builds customize these)
   --settings-hooks          .claude/settings.paf.json (the settings-level
                             alternative; never clobbers an existing
                             settings.json — merge by hand, enable ONE wiring)
   --init-state              build_state.json (ceiling configurable)
================================================================================
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent

QA_CORE = ["build_state.py", "converged.py", "lint_paf.py", "qa_pass.py"]
HOOK_FILES = ["_resolve.py", "stop_gate.py", "post_write_lint.py",
              "bash_guard.py", "session_context.py"]
AGENT_FILES = ["paf-validator.md", "paf-deliverables.md", "paf-discovery.md"]
SEED_CHECKS = ["balancing_check.py", "parity_check.py"]


def _copy(src: Path, dst: Path, written: list[str]) -> None:
    if not src.is_file():
        raise FileNotFoundError(f"skill is incomplete: missing {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    written.append(str(dst))


def install(target: Path, settings_hooks: bool, init_state: bool,
            ceiling: int) -> list[str]:
    target = target.resolve()
    if target == SKILL or SKILL in target.parents:
        raise ValueError("refusing to scaffold into the skill directory itself")
    if not target.is_dir():
        raise FileNotFoundError(f"target project does not exist: {target}")

    written: list[str] = []
    for name in QA_CORE:
        _copy(SKILL / "scripts" / name, target / "scripts" / "qa" / name, written)
    _copy(SKILL / "core" / "scripts" / "paf_packager.py",
          target / "scripts" / "qa" / "paf_packager.py", written)
    for name in HOOK_FILES:
        _copy(SKILL / "scripts" / "hooks" / name,
              target / ".claude" / "paf-hooks" / name, written)
    for name in AGENT_FILES:
        _copy(SKILL / "agents" / name,
              target / ".claude" / "agents" / name, written)
    for name in SEED_CHECKS:
        dst = target / "qa_checks" / name
        if dst.is_file():
            continue  # builds customize these — never overwrite
        _copy(SKILL / "templates" / "qa_checks" / name, dst, written)

    if settings_hooks:
        frag_src = SKILL / "hooks" / "settings.fragment.json"
        existing = target / ".claude" / "settings.json"
        dst = (target / ".claude" / "settings.paf.json"
               if existing.is_file() else existing)
        _copy(frag_src, dst, written)
        if dst.name == "settings.paf.json":
            print("note: .claude/settings.json already exists — wrote "
                  "settings.paf.json; merge the 'hooks' object by hand. "
                  "Enable settings-level OR frontmatter hooks, not both.")

    if init_state:
        sys.path.insert(0, str(SKILL / "scripts"))
        from build_state import BuildState
        state = BuildState(ceiling=ceiling)
        state.save(target)
        written.append(str(target / "build_state.json"))

    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", required=True)
    ap.add_argument("--settings-hooks", action="store_true")
    ap.add_argument("--init-state", action="store_true")
    ap.add_argument("--ceiling", type=int, default=5)
    args = ap.parse_args(argv)
    try:
        written = install(Path(args.target), args.settings_hooks,
                          args.init_state, args.ceiling)
    except (ValueError, FileNotFoundError) as ex:
        print(f"scaffold_enforcement: {ex}", file=sys.stderr)
        return 1
    print(f"scaffold_enforcement: {len(written)} file(s) installed into "
          f"{Path(args.target).resolve()}")
    for w in written:
        print(f"  + {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
