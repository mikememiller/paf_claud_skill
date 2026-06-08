<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# QA & bug-fixing — the hard gate + iterative loop

QA is the #1 priority. **No deliverable ships until the loop converges to zero
bugs.** `scripts/qa_pass.py` runs the single pass; Phase 6 loops it.

## The single QA pass (in order)
1. `pytest -m "not live"` → `EBS_RUN_LIVE=1 EBS_PASSWORD=… pytest -m live` — green.
2. **Adversarial review** of every repository query + policy rule vs the
   known-bug catalog (below) + fuzzed/edge inputs.
3. **Static checks:** `py_compile` all modules; `ruff`/`mypy` if present;
   **every file carries the Syntax copyright/version/build/date banner**.
4. **Golden-record behaviour:** output balances; QA gate returns expected
   `PASS/HOLD/FAIL`; loader insert→verify→**purge** leaves the DB clean (only
   when explicitly authorized to write).
5. **Python↔PL/SQL parity:** run the golden record through the Python engine and
   the EBS `XX…` package (utPLSQL) and assert identical output. Python is the
   **test oracle** for the production PL/SQL.
6. **Negative paths:** not-found, duplicate, out-of-tolerance, non-PO, FX,
   zero-tax, over/under-bill → correct holds.
7. **Install** in a fresh venv; **document/visual QA** (branding present; pricing
   identical across SOW/deck/ROI; render slides/docx → fresh-eyes subagent → fix
   overlap/overflow/contrast; shape-bounds check).
8. Emit `QA_REPORT.md` + an **honesty register** (env-blocked items only).

**Regression rule:** every bug found → fix **and** a test, same pass.

## Iterative bug-hunt loop (Phase 6 — run to convergence)
```
dry = 0
while dry < 2:                 # 2 consecutive clean rounds
    findings = HUNT()          # the pass above + diverse lenses
    if not findings: dry += 1; continue
    dry = 0
    for b in findings: fix(b); add_regression_test(b)
    rerun full pass            # fixes must not regress
```
HUNT lenses each round: tests; SQL (ROWNUM/binds/org-scope/NLS); policy edges;
balancing; PAF-contract (tool JSON valid; tool-capable model; managed-MCP tool
definitions match); docs/visual. Exit: 2 clean rounds + suite green +
`QA_REPORT.md` PASS + every fix tested. For large builds run HUNT as parallel
adversarial agents (different lenses), stop when all return empty twice.

## Known-bug catalog (proactively check)
1. ROWNUM+ORDER BY → inline view.
2. DATE string bind → bind date objects.
3. Loose regex over-match → anchor.
4. Unbalanced output / dropped tax → header=Σlines + TAX line.
5. Stale `num_rows` → COUNT(*).
6. Fuzzy match wrong record → resolution order.
7. FX exchange fields invalid.
8. Tolerance double-count → dual %-AND-$ gate.
9. SQL injection → bind variables only.
10. Cross-org leakage → org-scope + APPS_INITIALIZE.
11. Duplicate stub returning False → real check.
12. Python/PL-SQL drift → parity test.
13. Deliverables: branding missing, graphics overflow, pricing mismatch.
