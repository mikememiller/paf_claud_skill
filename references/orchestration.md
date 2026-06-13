<!-- Syntax Corporation © 2026 — EBS PAF Agent skill · references/orchestration.md · v2.0.0 · 2026.06.11 -->
# Orchestration — subagents, the convergence loop, and the hooks that enforce it

The v1 skill *described* discipline; v2 *enforces* it. Three mechanisms, one
principle: the build may not claim what a script has not verified.

---

## 1. The convergence loop as data (`build_state.json`)

`scripts/build_state.py` owns the state; `qa_pass.py` records each round;
`converged.py` renders the only verdict that matters.

| Field | Meaning |
|---|---|
| `qa_round` | rounds run so far |
| `consecutive_clean` | current clean streak (PASS rounds) |
| `required_clean` | streak needed to converge (default **2**) |
| `ceiling` | max rounds before forced escalation (default **5**) |
| `last_test_count` | collected tests last round (regression-rule currency) |
| `open_findings` / `history` | current findings; full round log (the audit trail) |
| `escalated` | ceiling hit without convergence |

Transitions: every `qa_pass.py` run records one round. PASS → streak+1;
FAIL → streak reset to 0. Streak ≥ `required_clean` → **CONVERGED** (phase
`converged`). Round ≥ `ceiling` without convergence → **ESCALATED**:
`ESCALATION.md` is written with the open findings and last rounds, and the
loop stops on purpose — past the ceiling, a human decision (raise ceiling,
change approach, descope) is cheaper than more iterations.

**Regression-test-delta rule (enforced):** after a FAIL round, the next round
must collect *more* tests than the failing round had — every fix carries a
regression test, or `qa_pass.py` raises it as a new finding. Green-but-untested
fixes no longer count as progress.

**Gate semantics (`converged.py`):**

| State | Exit | Effect at the Stop hook |
|---|---|---|
| no `build_state.json` | 0 | never blocks non-PAF work |
| converged | 0 | stop allowed |
| escalated / at ceiling | 0 (`--strict`: 1) | stop allowed; escalation notice |
| otherwise | **2** | **stop blocked**; findings on stderr |

---

## 2. Subagents (installed to `<project>/.claude/agents/` by the scaffold)

| Agent | Phase | Tools | Writes | Returns |
|---|---|---|---|---|
| `paf-discovery` | 1 | inherits all (needs the oracle MCP) | `discovery/dossier.md`, `discovery/verified_sql/*.sql` | ≤20-line summary |
| `paf-validator` | 4 & every round of 6 | Read, Grep, Glob, Bash | nothing (qa_pass writes `QA_REPORT.md` + state) | ≤15-line verdict |
| `paf-deliverables` | 5 | Read, Write, Edit, Bash, Glob | `output/`, generated docs/deck/BOM/ROI/`.paf` only | ≤12-line manifest |

**Why fresh contexts.** The validator has no investment in the code passing —
self-review bias is the failure mode the v1 loop could not see. Discovery's
hundreds of exploratory queries stay out of the main window; only the dossier
returns. Deliverable generation fans out safely because ownership is disjoint.

**Handoff contract.** Artifacts live on disk; conversations carry verdicts.
Every subagent reads the spec and writes only inside its ownership column
above. A subagent needing a change outside its column STOPS and reports — the
main session owns the spec and the engine.

**Stop-gating scope.** Only the **main session** is convergence-gated; the
stop gate exits 0 whenever `agent_id`/`agent_type` is present, so subagents
return freely mid-loop. Convergence is the orchestrator's responsibility.

---

## 3. Hooks (entry scripts installed to `<project>/.claude/paf-hooks/`)

| Event | Script | Effect |
|---|---|---|
| `SessionStart` | `session_context.py` | injects PAF version, MCP endpoint, build identity, convergence state, invariants — silent outside a PAF project |
| `PreToolUse` (Bash) | `bash_guard.py` | blocks `num_rows` reads from `*_TABLES` views and DROP/TRUNCATE on standard EBS schema prefixes (exit 2 + reason) |
| `PostToolUse` (Write\|Edit) | `post_write_lint.py` | lints `*.flowgraph.json`, `*.paf`, `spec.yaml`, banner on build `.py` the moment they are written; findings reach the model immediately |
| `Stop` / `SubagentStop` | `stop_gate.py` | the convergence gate (table above); honors `stop_hook_active`; skips subagents |

**Wiring (Claude Code):** merge `hooks/settings.fragment.json` into
`<project>/.claude/settings.json` (uses `$CLAUDE_PROJECT_DIR`) after Phase 2's
`scaffold_enforcement.py` installs `.claude/paf-hooks/`. The hook commands are
project-relative (`python3 .claude/paf-hooks/…`), so launch Claude Code from the
project root. SKILL.md frontmatter no longer carries a `hooks:` block — that key
is invalid for claude.ai / Cowork / Skills API upload, so the settings-fragment
is the single wiring path. On claude.ai / Cowork no hooks fire; the gates are
binding procedurally (run `qa_pass.py` then `converged.py --report`). If the
scripts are absent (non-PAF project, scaffold not run), the commands fail
non-blocking and the hooks are inert — by design, the skill must never jam
unrelated work.

**Precision over recall.** `bash_guard.py` blocks only what is near-certainly
wrong. DML is deliberately not pattern-blocked: governed interface loads are
legitimate, and that judgment belongs to QA, not a regex. Broader policy
(force-push, secrets) belongs in the user's global guard hooks, which compose
with these.

---

## 4. Runtime matrix — where enforcement is mechanical vs. procedural

| Runtime | Hooks | Subagents | Discipline |
|---|---|---|---|
| Claude Code CLI | fire | available | mechanical — gates block |
| Cowork | **do not fire** | not available | procedural — see below |
| claude.ai chat | do not fire | not available | procedural — see below |

**Procedural fallback (binding everywhere):** the same scripts, run by hand.
Before claiming any phase done: `python scripts/qa/qa_pass.py` then
`python scripts/qa/converged.py --report` — done means exit 0, nothing else.
After writing any artifact: `python scripts/qa/lint_paf.py <file>`. Without
subagents, run the validator's HUNT lenses sequentially in the main session
and hold its evidence standard: a finding cites file, observed, expected.

---

## 5. Escalation protocol

`ESCALATION.md` appears when the ceiling is hit. It is not a failure report;
it is a decision request: the open findings, the last rounds, and the three
options (raise ceiling / change approach / descope). Resuming = make the
decision, then run `qa_pass.py` again; the state machine continues counting.
