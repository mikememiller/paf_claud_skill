<!-- Syntax Corporation © 2026 — PAF Agent Factory · deliverables/samples -->
# Sample deliverables (illustrative)

These are **illustrative samples** generated **from `../../spec.example.yaml`** (the
bundled EBS-AP worked example) by the spec-driven generators in
`../../templates/deliverables/`. They show exactly what every engagement ships.
For a real engagement, fill your own `spec.yaml` and regenerate — the
per-engagement files belong in that agent's own repo, not here.

| File | Deliverable | Generator |
|------|-------------|-----------|
| `architecture.png` | Hero **technical-architecture** diagram | `build_diagrams.js --kind architecture` |
| `flow.png` | Hero **functional-flow** diagram | `build_diagrams.js --kind flow` |
| `Sample_Sales_Deck.pptx` | Sales / exec deck (problem · solution · value · architecture · trust · proof · ROI · why · next) | `build_sales_deck.js` |
| `Sample_Technical_Design.docx` | Technical design (embeds both diagrams) | `build_docx.py` |
| `Sample_Installation_Guide.docx` | Installation guide | `build_docx.py` |
| `Sample_SOW.docx` | **Comprehensive SOW** — problem · solution · value · functional-flow + architecture diagrams · governance · timeline · RACI · SLAs · entitlements · pricing · OCI BOM · signature | `build_docx.py` |
| `Sample_OCI_BOM.xlsx` | OCI Bill of Materials + consumption estimator | `build_oci_bom_xlsx.py` |
| `spec.json` · `pricing.json` | the inputs used (spec + computed pricing) | `pricing.py` |

## Regenerate
```bash
cd <skill root>
NM=<path to a pptxgenjs+sharp node install>   # e.g. an EBS agent repo's slides/node_modules
D=deliverables/samples
python templates/deliverables/pricing.py            --spec spec.example.yaml --out $D
NODE_PATH=$NM node templates/deliverables/build_diagrams.js --kind architecture --spec $D/spec.json --out $D/architecture.png
NODE_PATH=$NM node templates/deliverables/build_diagrams.js --kind flow         --spec $D/spec.json --out $D/flow.png
python templates/deliverables/build_docx.py         --spec $D/spec.json --pricing $D/pricing.json --diagram $D/architecture.png --flow $D/flow.png --out $D --prefix Sample_
python templates/deliverables/build_oci_bom_xlsx.py --spec $D/spec.json --out $D --prefix Sample_
NODE_PATH=$NM node templates/deliverables/build_sales_deck.js --spec $D/spec.json --pricing $D/pricing.json --diagram $D/architecture.png --out $D/Sample_Sales_Deck.pptx
```
Toolchain: `.docx` = stdlib (no deps); `.xlsx` = openpyxl; `.png`/`.pptx` = Node
`pptxgenjs` + `sharp` + `react` + `react-icons`. `pricing.py` needs PyYAML.

> Office files (`.docx`/`.pptx`) were structurally validated (zip + XML parse —
> the SOW embeds 2 images, 8 tables, 15 sections); the **architecture + flow PNGs
> are the visual proof** (no LibreOffice in the build env).
