<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# Hero-graphics standard ("wow / jump off the page")

Graphics in the **SOW, sales deck, and technical-design doc must be hero-grade**.
`templates/deliverables/build_diagrams.js` (`--kind architecture` and
`--kind flow`) renders the shared high-res visual kit **once**; every artifact
embeds the same assets (consistency = polish). Both are **spec-driven** (from
`spec.architecture` and `spec.flow_diagram`).

## The kit
- **REQUIRED: technical-architecture / deployment diagram** (in the tech-design
  doc AND the SOW). Shows the assumptions explicitly:
  **(1) EBS 19c transactional DB** (OCI DBaaS/Exadata, NNE — system of record +
  `XX…` PL/SQL), **(2) PAF on the ADB 26ai sidecar** (label "no EBS data — not in
  the data path"), **(3) OCI Database Tools Managed MCP** (HTTPS+OAuth) reaching
  EBS via a Database Tools Connection. Draw the flow on top: document → PAF
  extract → managed-MCP tool → `XX…` PL/SQL → interface tables → standard import.
- **REQUIRED: functional-flow / process sequence** hero (`build_diagrams.js
  --kind flow` from `spec.flow_diagram`) — in the SOW + tech-design doc.
- **ROI waterfall** + **tiered TCO** charts (brand palette).
- **OCI BOM** consumption chart; **timeline / RACI** graphic for the SOW.
- Dark branded title/section dividers; tri-color motif throughout.

## Standards
150+ dpi raster or SVG; brand palette only; strong contrast (icons in colored
circles on dark); ≥0.5" margins; no AI-slop accent bars; never overflow a shape.

## Visual QA (mandatory, part of the gate)
Render each artifact to images (LibreOffice/`soffice` + `pdftoppm` when
available; else structural/XML bounds check) → **fresh-eyes subagent** review →
fix overlap/overflow/contrast/branding. If no renderer is present, say so in the
honesty register and do the XML shape-bounds check instead.

## Tools
`pptxgenjs` + `react-icons` + `sharp` for icons/diagrams (see the proven
`build_sales_deck.js`); `anthropic-skills:pptx`/`docx`/`xlsx` for the documents.
