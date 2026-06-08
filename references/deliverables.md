<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# Deliverables — what to produce, in what format, generated how

Source of truth = the in-repo markdown (`docs/*.md`, `INSTALL.md`, `README.md`)
and the one pricing model (`pricing-and-bom.md`). The customer-facing files are
**generated from it** so they never drift. Generators live in
`templates/deliverables/`.

| # | Deliverable | Format | Generator / skill |
|---|-------------|--------|-------------------|
| 1 | Sales deck | `.pptx` | `build_sales_deck.js` (pptxgenjs / `anthropic-skills:pptx`) |
| 2 | Installation guide | `.docx` | `build_install_docx.py` (`anthropic-skills:docx`) |
| 3 | Technical design doc | `.docx` | `build_techdesign_docx.py` (`docx`) — embeds the architecture diagram |
| 4 | Statement of Work (signable) | `.docx` | `build_sow_docx.py` (`docx`) — diagram + RACI + 12/24/36 pricing + signature; generic legal shell |
| 5 | OCI BOM + consumption estimator | `.xlsx` | `build_oci_bom_xlsx.py` (`anthropic-skills:xlsx`) |
| 6 | Interactive ROI calculator | `.html` (+ `.xlsx`) | `build_roi_calculator` — sliders, payback, NPV; "my EBS data" mode |
| 7 | PAF integration package | sql/md/json | managed-MCP tool defs + SQL Reports + canvas recipe (`paf-platform.md`) |

Also in-repo: `docs/*.md`, `INSTALL.md`/`setup.sh`, the EBS `XX…` PL/SQL package,
the test suite, `QA_REPORT.md`.

## Rules
- Every artifact **Syntax-branded** (`branding.md`); hero graphics in #1/#3/#4
  (`graphics-standard.md`).
- **Pricing identical** across SOW / deck / ROI (all read `pricing.py` output).
- Generate deliverables **only after Phase 4 QA is green**; then visually QA them
  in Phase 6.
- The shipped `build_sales_deck.js` is the proven, working starting point; the
  docx/xlsx/roi generators are authored per build by invoking the respective
  `anthropic-skills` skill with the brand + pricing inputs (don't hand-craft
  unbranded files).
