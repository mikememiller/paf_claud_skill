<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# Deliverables — what to produce, in what format, generated how

Source of truth = the in-repo markdown (`docs/*.md`, `INSTALL.md`, `README.md`)
and the one pricing model (`pricing-and-bom.md`). The customer-facing files are
**generated from it** so they never drift. The generators in
`templates/deliverables/` are **spec-driven** (read `spec.yaml` via `pricing.py`'s
`output/spec.json` + `pricing.json`, plus `assets/brand.json`); ready samples are
in [`../deliverables/samples/`](../deliverables/samples/).

> **Full generic catalog + showcase deck:** [`../deliverables/DELIVERABLES.md`](../deliverables/DELIVERABLES.md)
> documents every deliverable in detail (domain-neutral); `../deliverables/PAF_Factory_Deliverables.pptx`
> is the wow-graphics deck describing them (regen: `node ../deliverables/build_diagram.js
> && node ../deliverables/build_deck.js`).

| # | Deliverable | Format | Generator / skill |
|---|-------------|--------|-------------------|
| 0 | Hero architecture/flow diagram | `.png` | `build_diagrams.js` (from `spec.architecture`) |
| 1 | Sales deck | `.pptx` | `build_sales_deck.js` (pptxgenjs) — embeds the diagram |
| 2 | Installation guide | `.docx` | `build_docx.py` (stdlib OOXML, no deps) |
| 3 | Technical design doc | `.docx` | `build_docx.py` — embeds the architecture diagram |
| 4 | Statement of Work (signable) | `.docx` | `build_docx.py` — diagram + RACI + 12/24/36 pricing + signature; generic legal shell |
| 5 | OCI BOM + consumption estimator | `.xlsx` | `build_oci_bom_xlsx.py` (openpyxl) |
| 6 | Interactive ROI calculator | `.html` (+ `.xlsx`) | roadmap — author per build; pricing from `pricing.json` |
| 7 | PAF integration package | `.paf` + sql/md/json | `core/scripts/paf_packager.py` + managed-MCP tool defs + canvas recipe (`paf-platform.md`) |
| – | Pricing model | `.json` | `pricing.py` (one model → all docs match) |

Also in-repo: `docs/*.md`, `INSTALL.md`/`setup.sh`, the EBS `XX…` PL/SQL package,
the test suite, `QA_REPORT.md`.

## Rules
- Every artifact **Syntax-branded** (`branding.md`); hero graphics in #1/#3/#4
  (`graphics-standard.md`).
- **Pricing identical** across SOW / deck / ROI (all read `pricing.py` output).
- Generate deliverables **only after Phase 4 QA is green**; then visually QA them
  in Phase 6.
- The generators are **shipped + spec-driven** — run `pricing.py` (→ spec.json +
  pricing.json), then `build_diagrams.js`, `build_docx.py`, `build_oci_bom_xlsx.py`,
  `build_sales_deck.js`. See [`../deliverables/samples/README.md`](../deliverables/samples/README.md)
  for the run order + ready examples. (ROI `.html` is the one roadmap item.)
