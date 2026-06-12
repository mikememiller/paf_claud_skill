"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/selftest.py — executable proof of the v2 enforcement layer.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Exercises the state machine, the convergence gate, the artifact linter, the
 hook entry scripts (via simulated stdin payloads), and the scaffold — in a
 throwaway sandbox, with no live EBS and no Claude Code runtime required.

   python scripts/selftest.py        # exit 0 = all scenarios pass

 What it CANNOT prove (the honesty register lives in UPGRADE-2.0.md):
 that Claude Code actually fires frontmatter hooks at the right moments —
 only a live CLI session proves that. Everything below the hook-firing line
 IS proven here.
================================================================================
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
HOOKS = SCRIPTS / "hooks"
FIXTURE_FG = SKILL / "core" / "flowgraphs" / "ebs_ap_3way_match.flowgraph.json"
FIXTURE_FG2 = SKILL / "core" / "flowgraphs" / "month_end_close_readiness.flowgraph.json"

PY = sys.executable
BANNER = (
    '"""\n'
    "================================================================================\n"
    " Syntax Corporation © 2026 — selftest fixture\n"
    " Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11\n"
    "================================================================================\n"
    '"""\n'
)


def run(cmd: list[str], cwd: Path | None = None, stdin: str | None = None,
        env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(cmd, cwd=cwd, input=stdin, env=full_env,
                          capture_output=True, text=True, timeout=300)


def hook(name: str, payload: dict, cwd: Path | None = None,
         script_dir: Path = HOOKS, env: dict | None = None) -> subprocess.CompletedProcess:
    return run([PY, str(script_dir / name)], cwd=cwd,
               stdin=json.dumps(payload), env=env)


def expect(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ----------------------------------------------------------------- scenarios
def s01_state_machine(sandbox: Path) -> str:
    """FAIL→PASS→(blocked)→PASS→converged→(allowed), via CLI + stop hook."""
    proj = sandbox / "s01"
    proj.mkdir()
    r = run([PY, str(SCRIPTS / "build_state.py"), "init"], cwd=proj)
    expect(r.returncode == 0, f"init failed: {r.stdout}{r.stderr}")
    run([PY, str(SCRIPTS / "build_state.py"), "record", "--status", "FAIL",
         "--findings", "2", "--test-count", "10"], cwd=proj)
    run([PY, str(SCRIPTS / "build_state.py"), "record", "--status", "PASS",
         "--findings", "0", "--test-count", "11"], cwd=proj)
    g = hook("stop_gate.py", {"cwd": str(proj)})
    expect(g.returncode == 2, f"streak 1/2 must block, got {g.returncode}")
    expect("round 2" in g.stderr, f"block message lacks round: {g.stderr}")
    run([PY, str(SCRIPTS / "build_state.py"), "record", "--status", "PASS",
         "--findings", "0", "--test-count", "11"], cwd=proj)
    g = hook("stop_gate.py", {"cwd": str(proj)})
    expect(g.returncode == 0, f"converged must allow stop, got {g.returncode}: {g.stderr}")
    state = json.loads((proj / "build_state.json").read_text())
    expect(state["phase"] == "converged" and state["consecutive_clean"] == 2,
           f"state wrong: {state}")
    return "FAIL→PASS→blocked(2)→PASS→converged→allowed(0)"


def s02_qa_pass_loop(sandbox: Path) -> str:
    """The real qa_pass.py drives the loop: banner finding → delta rule → green."""
    proj = sandbox / "s02"
    (proj / "src").mkdir(parents=True)
    (proj / "tests").mkdir()
    (proj / "src" / "ok.py").write_text(BANNER + "X = 1\n")
    (proj / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    assert 1 + 1 == 2\n")
    qa = str(SCRIPTS / "qa_pass.py")

    # round 1: seeded banner violation -> FAIL
    (proj / "src" / "bad.py").write_text("Y = 2\n")
    r1 = run([PY, qa], cwd=proj)
    expect(r1.returncode == 3, f"round 1 must FAIL(3): {r1.returncode}\n{r1.stdout}")
    expect("banner" in (proj / "QA_REPORT.md").read_text(),
           "round 1 report lacks the banner finding")

    # round 2: fix the banner but add NO test -> regression-delta finding
    (proj / "src" / "bad.py").write_text(BANNER + "Y = 2\n")
    r2 = run([PY, qa], cwd=proj)
    expect(r2.returncode == 3, f"round 2 must FAIL on delta rule: {r2.returncode}")
    expect("regression-test rule violated" in (proj / "QA_REPORT.md").read_text(),
           "round 2 report lacks the delta finding")

    # round 3: add the regression test -> PASS (streak 1)
    (proj / "tests" / "test_banner.py").write_text(
        "from pathlib import Path\n"
        "def test_banner_present():\n"
        "    assert 'Syntax Corporation' in Path('src/bad.py').read_text()\n")
    r3 = run([PY, qa], cwd=proj)
    expect(r3.returncode == 0, f"round 3 must PASS: {r3.returncode}\n{r3.stdout}")
    g = hook("stop_gate.py", {"cwd": str(proj)})
    expect(g.returncode == 2, "streak 1/2 after round 3 must still block")

    # round 4: PASS again -> converged -> gate opens
    r4 = run([PY, qa], cwd=proj)
    expect(r4.returncode == 0, f"round 4 must PASS: {r4.returncode}")
    g = hook("stop_gate.py", {"cwd": str(proj)})
    expect(g.returncode == 0, f"converged gate must open: {g.stderr}")
    hist = json.loads((proj / "build_state.json").read_text())["history"]
    expect([h["status"] for h in hist] == ["FAIL", "FAIL", "PASS", "PASS"],
           f"history wrong: {hist}")
    expect(hist[2]["test_count"] == 2 and hist[0]["test_count"] == 1,
           f"test counts wrong: {hist}")
    return "qa_pass loop: banner FAIL → delta FAIL → +test PASS → PASS → converged"


def s03_ceiling_escalation(sandbox: Path) -> str:
    proj = sandbox / "s03"
    proj.mkdir()
    run([PY, str(SCRIPTS / "build_state.py"), "init", "--ceiling", "3"], cwd=proj)
    for _ in range(3):
        run([PY, str(SCRIPTS / "build_state.py"), "record", "--status", "FAIL",
             "--findings", "1", "--test-count", "5"], cwd=proj)
    expect((proj / "ESCALATION.md").is_file(), "ESCALATION.md not written")
    esc = (proj / "ESCALATION.md").read_text()
    expect("ceiling" in esc and "Open findings" in esc, f"escalation thin: {esc[:200]}")
    g = hook("stop_gate.py", {"cwd": str(proj)})
    expect(g.returncode == 0, f"escalated build must be allowed to stop: {g.returncode}")
    expect("ceiling" in g.stdout, f"escalation notice missing: {g.stdout!r}")
    strict = run([PY, str(SCRIPTS / "converged.py"), "--strict"], cwd=proj)
    expect(strict.returncode == 1, f"--strict must exit 1 on escalation: {strict.returncode}")
    return "3 FAILs @ ceiling 3 → ESCALATION.md, stop allowed, --strict exits 1"


def s04_lint_clean_fixtures(sandbox: Path) -> str:
    r = run([PY, str(SCRIPTS / "lint_paf.py"), str(FIXTURE_FG), str(FIXTURE_FG2)])
    expect(r.returncode == 0, f"clean fixtures must lint PASS: {r.stderr}")
    return "both shipped flowGraph templates lint clean"


def s05_lint_mutations(sandbox: Path) -> str:
    base = json.loads(FIXTURE_FG.read_text())
    muts: list[tuple[str, dict]] = []

    m = json.loads(json.dumps(base))
    e = m["edges"][1]
    e["id"] = e["id"].replace(e["target"], "node-BROKEN")
    muts.append(("edge id missing target (clone remap bug)", m))

    m = json.loads(json.dumps(base))
    step = next(n for n in m["nodes"] if n["data"]["type"] == "agentStep")
    step["data"]["template"]["tools"]["value"] = ["node-DOESNOTEXIST"]
    muts.append(("tools.value -> nonexistent mcpServer", m))

    m = json.loads(json.dumps(base))
    step = next(n for n in m["nodes"] if n["data"]["type"] == "agentStep")
    step["data"]["template"]["custom_instruction"]["value"] = "   "
    muts.append(("empty custom_instruction", m))

    m = json.loads(json.dumps(base))
    m["nodes"][1]["data"]["type"] = "weirdKind"
    muts.append(("unknown data.type", m))

    m = json.loads(json.dumps(base))
    m["edges"][0]["sourceHandle"] = "user_provided_input-node-WRONG"
    muts.append(("sourceHandle suffix mismatch", m))

    caught = 0
    for i, (label, mut) in enumerate(muts):
        p = sandbox / f"s05_mut{i}.flowgraph.json"
        p.write_text(json.dumps(mut))
        r = run([PY, str(SCRIPTS / "lint_paf.py"), str(p)])
        expect(r.returncode == 2, f"mutation NOT caught: {label}\n{r.stdout}{r.stderr}")
        caught += 1

    r = run([PY, str(SCRIPTS / "lint_paf.py"), str(FIXTURE_FG),
             "--target-version", "25.3.0.0.9"])
    expect(r.returncode == 2 and "26.4" in r.stderr,
           f"25.3 target must fail file-import lint: {r.stderr}")
    caught += 1
    return f"{caught}/6 seeded violations caught (5 schema mutations + 25.3 target)"


def s06_paf_roundtrip(sandbox: Path) -> str:
    sys.path.insert(0, str(SKILL / "core" / "scripts"))
    import importlib
    pk = importlib.import_module("paf_packager")
    fg = json.loads(FIXTURE_FG.read_text())
    paf = sandbox / "selftest_agent.paf"
    paf.write_bytes(pk.pack_flowgraph(fg, name="Selftest Agent"))
    r = run([PY, str(SCRIPTS / "lint_paf.py"), str(paf)])
    expect(r.returncode == 0, f"minted .paf must lint PASS: {r.stdout}{r.stderr}")
    expect("BY DESIGN" in r.stdout, "bindings-never-travel note missing")
    r = run([PY, str(SCRIPTS / "lint_paf.py"), str(paf)],
            env={"PAF_PASSWORD": "wrong-password"})
    expect(r.returncode == 2 and "decrypt" in r.stderr,
           f"wrong password must be a finding: {r.stderr}")
    return ".paf mint → lint PASS; wrong password → decrypt finding"


def s07_hook_simulations(sandbox: Path) -> str:
    proj = sandbox / "s07"
    proj.mkdir()
    run([PY, str(SCRIPTS / "build_state.py"), "init"], cwd=proj)
    run([PY, str(SCRIPTS / "build_state.py"), "record", "--status", "FAIL",
         "--findings", "1", "--test-count", "1"], cwd=proj)
    checks = 0

    g = hook("stop_gate.py", {"cwd": str(proj), "stop_hook_active": True})
    expect(g.returncode == 0, "stop_hook_active must short-circuit to 0")
    checks += 1
    g = hook("stop_gate.py", {"cwd": str(proj), "agent_type": "paf-validator"})
    expect(g.returncode == 0, "subagent stop must not be gated")
    checks += 1
    g = hook("stop_gate.py", {"cwd": str(sandbox)})  # no state file here
    expect(g.returncode == 0, "no build_state.json must never block")
    checks += 1
    g = hook("stop_gate.py", {}, cwd=proj)  # empty payload, cwd fallback
    expect(g.returncode == 2, "cwd-fallback gating failed")
    checks += 1
    g = run([PY, str(HOOKS / "stop_gate.py")], stdin="this is not json", cwd=proj)
    expect(g.returncode in (0, 2), f"garbage stdin crashed the hook: {g.stderr}")
    checks += 1

    mut = sandbox / "s05_mut0.flowgraph.json"  # from s05
    g = hook("post_write_lint.py",
             {"tool_name": "Write", "tool_input": {"file_path": str(mut)}})
    expect(g.returncode == 2 and "FINDING" in g.stderr,
           f"post-write lint must block on a bad flowgraph: {g.stderr}")
    checks += 1
    txt = sandbox / "notes.txt"
    txt.write_text("hello")
    g = hook("post_write_lint.py",
             {"tool_name": "Write", "tool_input": {"file_path": str(txt)}})
    expect(g.returncode == 0, "non-lintable file must pass silently")
    checks += 1

    g = hook("bash_guard.py", {"tool_name": "Bash", "tool_input":
             {"command": "echo 'select table_name, num_rows from all_tables;' | sql apps/x"}})
    expect(g.returncode == 2 and "COUNT(*)" in g.stderr, "num_rows guard failed")
    checks += 1
    g = hook("bash_guard.py", {"tool_name": "Bash", "tool_input":
             {"command": "echo 'select count(*) from ap_invoices_all;' | sql apps/x"}})
    expect(g.returncode == 0, "COUNT(*) must not be blocked")
    checks += 1
    g = hook("bash_guard.py", {"tool_name": "Bash", "tool_input":
             {"command": "sql apps/x <<< 'DROP TABLE AP_INVOICES_ALL;'"}})
    expect(g.returncode == 2 and "Rule 4" in g.stderr, "base-table DDL guard failed")
    checks += 1
    g = hook("bash_guard.py", {"tool_name": "Bash", "tool_input":
             {"command": "sql apps/x <<< 'TRUNCATE TABLE XXSYN_STAGING;'"}})
    expect(g.returncode == 0, "XX% custom schema must not be blocked")
    checks += 1

    (proj / "conn.json").write_text(json.dumps(
        {"paf_version": "26.4.0.0.0", "mcp_url": "http://192.0.2.10:3000/sse"}))
    g = hook("session_context.py", {"cwd": str(proj)})
    expect(g.returncode == 0 and "26.4" in g.stdout and "converged.py" in g.stdout,
           f"session context thin: {g.stdout!r}")
    checks += 1
    g = hook("session_context.py", {"cwd": str(sandbox)})  # not a PAF project
    expect(g.returncode == 0 and g.stdout.strip() == "",
           "session context must stay silent outside PAF projects")
    checks += 1
    return f"{checks}/13 hook stdin simulations behaved"


def s08_scaffold(sandbox: Path) -> str:
    proj = sandbox / "s08_project"
    proj.mkdir()
    r = run([PY, str(SCRIPTS / "scaffold_enforcement.py"), "--target", str(proj),
             "--init-state", "--ceiling", "4"])
    expect(r.returncode == 0, f"scaffold failed: {r.stderr}")
    for rel in ("scripts/qa/build_state.py", "scripts/qa/converged.py",
                "scripts/qa/lint_paf.py", "scripts/qa/qa_pass.py",
                "scripts/qa/paf_packager.py",
                ".claude/paf-hooks/stop_gate.py", ".claude/paf-hooks/_resolve.py",
                ".claude/paf-hooks/post_write_lint.py",
                ".claude/paf-hooks/bash_guard.py",
                ".claude/paf-hooks/session_context.py",
                ".claude/agents/paf-validator.md",
                ".claude/agents/paf-deliverables.md",
                ".claude/agents/paf-discovery.md",
                "qa_checks/balancing_check.py", "qa_checks/parity_check.py",
                "build_state.json"):
        expect((proj / rel).is_file(), f"scaffold missing {rel}")
    state = json.loads((proj / "build_state.json").read_text())
    expect(state["ceiling"] == 4, f"ceiling not applied: {state}")

    # the scaffolded stop gate must resolve the core from ITS location
    g = hook("stop_gate.py", {"cwd": str(proj)},
             script_dir=proj / ".claude" / "paf-hooks")
    expect(g.returncode == 2 and "qa_pass.py" in g.stderr,
           f"scaffolded stop gate broken: rc={g.returncode} {g.stderr}")

    # refusal guard: never scaffold into the skill itself
    r = run([PY, str(SCRIPTS / "scaffold_enforcement.py"), "--target", str(SKILL)])
    expect(r.returncode == 1 and "refusing" in r.stderr, "self-scaffold not refused")

    # seeded checks are real: missing fixtures are findings
    sys.path.insert(0, str(proj / "qa_checks"))
    import importlib
    os.chdir(proj)
    try:
        bal = importlib.import_module("balancing_check")
        res = bal.check()
        expect(len(res) == 1 and "missing" in res[0], f"balancing seed wrong: {res}")
        (proj / "output").mkdir()
        (proj / "output" / "golden_output.json").write_text(json.dumps({
            "header_total": 632500.00,
            "lines": [{"amount": 600000.00, "type": "ITEM"},
                      {"amount": 32500.00, "type": "TAX"}]}))
        expect(bal.check() == [], "balanced golden output must pass")
        (proj / "output" / "golden_output.json").write_text(json.dumps({
            "header_total": 632500.00,
            "lines": [{"amount": 600000.00, "type": "ITEM"}]}))
        res = bal.check()
        expect(any("UNBALANCED" in f for f in res) and any("TAX" in f for f in res),
               f"unbalanced/no-tax must be findings: {res}")
    finally:
        os.chdir(sandbox)
        sys.path.pop(0)
    return "scaffold tree complete; relocated gate works; seeds enforce; self-install refused"


def s09_agent_frontmatter(sandbox: Path) -> str:
    import yaml
    names = []
    for f in sorted((SKILL / "agents").glob("*.md")):
        parts = f.read_text().split("---")
        expect(len(parts) >= 3, f"{f.name}: no frontmatter block")
        fm = yaml.safe_load(parts[1])
        expect(bool(fm.get("name")) and bool(fm.get("description")),
               f"{f.name}: name/description missing")
        names.append(fm["name"])
    expect(names == ["paf-deliverables", "paf-discovery", "paf-validator"],
           f"unexpected agent set: {names}")
    fm = yaml.safe_load((SKILL / "agents" / "paf-validator.md").read_text().split("---")[1])
    expect("Write" not in fm.get("tools", ""), "validator must not have Write")
    return "3 agents parse; validator is write-restricted; discovery inherits all"


def s10_skill_frontmatter(sandbox: Path) -> str:
    import yaml
    text = (SKILL / "SKILL.md").read_text()
    parts = text.split("---")
    fm = yaml.safe_load(parts[1])
    expect(bool(fm.get("name")) and bool(fm.get("description")),
           "SKILL.md name/description missing")
    hooks_block = fm.get("hooks")
    expect(isinstance(hooks_block, dict), "SKILL.md frontmatter has no hooks block")
    for event in ("SessionStart", "PreToolUse", "PostToolUse", "Stop"):
        expect(event in hooks_block, f"hooks block missing {event}")
        for entry in hooks_block[event]:
            for h in entry["hooks"]:
                expect(h["type"] == "command" and ".claude/paf-hooks/" in h["command"],
                       f"{event} hook command malformed: {h}")
    pre = hooks_block["PreToolUse"][0]
    expect(pre.get("matcher") == "Bash", "PreToolUse matcher must be Bash")
    post = hooks_block["PostToolUse"][0]
    expect(post.get("matcher") == "Write|Edit", "PostToolUse matcher must be Write|Edit")
    return "SKILL.md frontmatter + 4-event hooks block parse and point at .claude/paf-hooks/"


def s11_dogfood_banners(sandbox: Path) -> str:
    targets = sorted(str(p) for p in SCRIPTS.rglob("*.py"))
    r = run([PY, str(SCRIPTS / "lint_paf.py"), *targets])
    expect(r.returncode == 0, f"skill's own scripts fail banner lint: {r.stderr}")
    return f"{len(targets)} skill scripts carry the Syntax banner (lint PASS)"


SCENARIOS = [
    ("S01 state machine + stop gate", s01_state_machine),
    ("S02 qa_pass convergence loop + delta rule", s02_qa_pass_loop),
    ("S03 ceiling escalation", s03_ceiling_escalation),
    ("S04 lint: clean fixtures", s04_lint_clean_fixtures),
    ("S05 lint: seeded violations", s05_lint_mutations),
    ("S06 .paf mint + lint round-trip", s06_paf_roundtrip),
    ("S07 hook stdin simulations", s07_hook_simulations),
    ("S08 scaffold into a project", s08_scaffold),
    ("S09 agent frontmatter", s09_agent_frontmatter),
    ("S10 SKILL.md frontmatter hooks", s10_skill_frontmatter),
    ("S11 dogfood: banners on skill scripts", s11_dogfood_banners),
]


def main() -> int:
    sandbox = Path(tempfile.mkdtemp(prefix="paf_selftest_"))
    print(f"selftest sandbox: {sandbox}")
    failures = 0
    for name, fn in SCENARIOS:
        try:
            detail = fn(sandbox)
            print(f"PASS  {name} — {detail}")
        except AssertionError as ex:
            failures += 1
            print(f"FAIL  {name} — {ex}")
        except Exception:
            failures += 1
            print(f"FAIL  {name} — crashed:")
            traceback.print_exc()
    total = len(SCENARIOS)
    print(f"\nselftest: {total - failures}/{total} scenarios passed")
    if failures == 0:
        shutil.rmtree(sandbox, ignore_errors=True)
    else:
        print(f"sandbox kept for inspection: {sandbox}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
