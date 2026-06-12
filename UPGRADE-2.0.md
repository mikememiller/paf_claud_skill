<!-- Syntax Corporation © 2026 — EBS PAF Agent skill · UPGRADE-2.0.md · v2.0.0 · 2026.06.11 -->
# Upgrade to v2.0.0 — subagents, an enforced convergence loop, lifecycle hooks

v1 described discipline in prose. v2 makes the same discipline mechanical:
the build cannot claim what a script has not verified. Nothing in the v1
procedure changed — Phases 0–7 and Rules 1–12 stand, same numbering.

## What changed

**A. Deterministic core (runs anywhere, no Claude Code required)**
- `scripts/build_state.py` — Phase 6 as a state machine in `build_state.json`:
  rounds, clean streak (2 to converge), findings, full history (audit trail),
  a 5-round ceiling that writes `ESCALATION.md` instead of looping forever.
- `scripts/converged.py` — the single done-gate: exit 0 = may stop, exit 2 =
  not converged (findings on stderr). Absent state file → always 0, so the
  gate can never jam non-PAF work.
- `scripts/lint_paf.py` — artifact linter locked to the schema verified from a
  live 26.4 export: flowGraph node/edge invariants (incl. the clone-remap
  edge-id trap), tools→mcpServer cross-refs, placeholder/empty-instruction
  detection, `.paf` decrypt + envelope checks, `spec.yaml` required keys,
  Syntax banners, and the 25.3-vs-26.4 file-import version axis. Bindings
  (MCP/LLM) absent from artifacts is BY DESIGN and never a finding.
- `scripts/qa_pass.py` v2 — keeps every v1 check, plus: records each round in
  the state machine; enforces the regression rule (after a FAIL round the next
  round must collect MORE tests); lints all artifacts; runs pluggable
  `qa_checks/*.py`. The seeded checks (balancing, Python↔PL/SQL parity) FAIL
  while their fixtures are missing — wiring the golden record is enforced,
  not advised.

**B. Subagents (`agents/`, installed per-project by the scaffold)**
- `paf-discovery` (Phase 1) — live verification; returns a dossier, keeps the
  exploration noise out of the main context.
- `paf-validator` (Phases 4/6) — fresh-context adversarial QA; read-only
  tools; the builder never grades its own work.
- `paf-deliverables` (Phase 5) — generator chain with a hard file-ownership
  boundary; never touches spec/engine/tests.
Handoff contract: artifacts on disk, verdicts in conversation
(`references/orchestration.md` §2).

**C. Hooks (SKILL.md frontmatter + `scripts/hooks/`)**
- SessionStart → environment ground truth injected (PAF version, MCP endpoint,
  convergence state, invariants); silent outside PAF projects.
- PreToolUse(Bash) → blocks `num_rows` reads from `*_TABLES` and DROP/TRUNCATE
  on standard EBS schema prefixes. DML deliberately not pattern-blocked.
- PostToolUse(Write|Edit) → lints PAF artifacts the moment they are written.
- Stop → the convergence gate; honors `stop_hook_active`; subagents exempt;
  ceiling escalates instead of blocking.

**D. Orchestrator + proof**
- `SKILL.md` rewritten as a slim orchestrator (phases table with owners and
  gates; rules and verify items preserved verbatim where load-bearing).
- `references/orchestration.md` — state machine spec, handoff contract, hook
  wiring, runtime matrix, escalation protocol.
- `scripts/selftest.py` — 11 scenarios proving the loop, gates, linter,
  hooks (via stdin simulation), and scaffold. 11/11 at ship time.

## Install

```bash
cp -r ebs-paf-agent ~/.claude/skills/ebs-paf-agent   # replaces v1; nothing global
python ~/.claude/skills/ebs-paf-agent/scripts/selftest.py   # 11/11 expected
```

Per build (Phase 2, after copying `templates/` into the new repo):

```bash
python ~/.claude/skills/ebs-paf-agent/scripts/scaffold_enforcement.py \
    --target /path/to/build-repo --init-state
```

Launch Claude Code from the build-repo root (the frontmatter hook commands are
project-relative). Optional settings-level wiring instead of frontmatter:
`hooks/settings.fragment.json` — enable exactly ONE of the two.

## Decisions log (the judgment calls, so you can reverse them deliberately)

1. **Hook command resolution = project-relative via the scaffold.** Frontmatter
   commands call `.claude/paf-hooks/*.py`, which exist because Phase 2 installs
   them. Avoids depending on undocumented skill-dir path variables. Cost: the
   CLI must launch from the project root; otherwise the hooks are inert
   (non-blocking failures) — never jamming, by design.
2. **One wiring at a time.** Frontmatter hooks are primary; the settings
   fragment is the documented alternative. Both at once = every gate fires
   twice (idempotent, but wasteful).
3. **Main-session-only stop gating.** Subagents return freely mid-loop
   (`agent_id`/`agent_type` in the payload → exit 0); convergence is the
   orchestrator's responsibility.
4. **Ceiling escalates rather than blocks.** A session that can never end is
   worse than one that ends early with `ESCALATION.md` on the table.
5. **bash_guard is precision-over-recall.** Two near-certain blocks only.
   Broader policy (force-push, secrets) stays in your global guard hooks,
   which compose with these.
6. **Seeded qa_checks enforce a contract instead of shipping placeholders.**
   Missing golden/parity fixtures are findings that drive Phase 4 wiring.

## Morning smoke test (Claude Code CLI — the part a container cannot prove)

1. Install (above), `selftest.py` → 11/11.
2. Scratch project: `mkdir /tmp/paf-smoke && cd /tmp/paf-smoke`, copy
   `templates/` in, run the scaffold with `--init-state`.
3. Start `claude` in that directory; confirm the SessionStart context block
   appears and `/hooks` lists the four events.
4. Ask for something trivially "done" — the Stop gate must block with the
   round-0 message. Run a fake QA round to green
   (`python scripts/qa/build_state.py record --status PASS --findings 0
   --test-count 1`, twice) — the gate must open.
5. Ask it to run `select num_rows from all_tables` — must be blocked with the
   COUNT(*) message.
6. Then the real proof: the end-to-end AP reference build against live EBS
   with `paf-discovery` → `paf-validator` → `paf-deliverables`.

## Honesty register (what this container could not verify)

- **Frontmatter hook firing semantics** — that Claude Code fires skill-scoped
  hooks at the documented moments, and the working directory they run with, is
  only provable in a live CLI session (smoke-test steps 3–5). Everything below
  that line — the scripts' behavior on every payload shape — is proven by
  `selftest.py`. If frontmatter hooks do not fire in your CLI version, switch
  to the settings fragment (decision #2).
- **End-to-end AP reference build** — needs your CLI + live EBS; pending.
- **pyagentspec deep validation** covers the tool-free Agent Spec string mode
  (`AgentSpecDeserializer.from_json`, pyagentspec 26.1.2); tool-bound
  flowGraphs are validated structurally against the reverse-engineered schema,
  which is the stronger check for the import path we actually use.
- **bash_guard heuristics** are narrow by intent; they will not catch every
  unwise command — that remains QA's job (Rule 4 unchanged).
