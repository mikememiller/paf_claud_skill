"""
================================================================================
 Syntax Corporation © 2026 — PAF Agent Factory — templates/deliverables/build_docx.py
 Version : 2.0.0   Build : 2026.06.08
--------------------------------------------------------------------------------
 SPEC-DRIVEN Word deliverables, no python-docx dependency — a minimal valid OOXML
 (.docx) writer (stdlib only). Produces, from build/spec.json + build/pricing.json:
   <prefix>Installation_Guide.docx
   <prefix>Technical_Design.docx   (embeds the architecture diagram)
   <prefix>SOW.docx                (embeds diagram + pricing + signature)

   python build_docx.py --spec build/spec.json --pricing build/pricing.json \
       --diagram build/architecture.png --out build --prefix Sample_
================================================================================
"""
from __future__ import annotations
import argparse, json, zipfile
from pathlib import Path
from xml.sax.saxutils import escape

NAVY = "0632A0"; INK = "16203A"; SLATE = "5B6577"


class Docx:
    def __init__(self):
        self.body: list[str] = []
        self.images: list[tuple[str, bytes]] = []

    def _p(self, runs_xml, spacing_after=120, align=None):
        pPr = f'<w:spacing w:after="{spacing_after}"/>' + (f'<w:jc w:val="{align}"/>' if align else '')
        self.body.append(f'<w:p><w:pPr>{pPr}</w:pPr>{runs_xml}</w:p>')

    def _run(self, text, *, sz=22, bold=False, color=INK, mono=False):
        rPr = '<w:rPr>' + ('<w:b/>' if bold else '') + f'<w:color w:val="{color}"/><w:sz w:val="{sz}"/>'
        rPr += '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>' if mono else '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
        rPr += '</w:rPr>'
        return f'<w:r>{rPr}<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>'

    def title(self, t): self._p(self._run(t, sz=44, bold=True, color=NAVY), 80)
    def subtitle(self, t): self._p(self._run(t, sz=22, color=SLATE), 240)
    def h1(self, t): self._p(self._run(t, sz=30, bold=True, color=NAVY), 120)
    def para(self, t): self._p(self._run(t))
    def code(self, t): self._p(self._run(t, sz=18, mono=True))
    def footer(self, t): self._p(self._run(t, sz=16, color=SLATE), 0, "center")
    def page_break(self): self.body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def bullet(self, t):
        self.body.append('<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
                         f'<w:spacing w:after="60"/></w:pPr>{self._run(t)}</w:p>')

    def table(self, rows, widths=None):
        n = len(rows[0]); widths = widths or [9360 // n] * n
        grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
        trs = []
        for ri, row in enumerate(rows):
            tcs = []
            for ci, cell in enumerate(row):
                hdr = ri == 0
                shd = '<w:shd w:val="clear" w:fill="0632A0"/>' if hdr else '<w:shd w:val="clear" w:fill="F4F7FC"/>'
                run = self._run(cell, sz=20, bold=hdr, color=("FFFFFF" if hdr else INK))
                tcs.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[ci]}" w:type="dxa"/>{shd}</w:tcPr>'
                           f'<w:p><w:pPr><w:spacing w:after="20"/></w:pPr>{run}</w:p></w:tc>')
            trs.append('<w:tr>' + ''.join(tcs) + '</w:tr>')
        self.body.append('<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="9360" w:type="dxa"/>'
                         '<w:tblBorders>' + ''.join(f'<w:{e} w:val="single" w:sz="4" w:color="DCE4F4"/>'
                         for e in ("top", "left", "bottom", "right", "insideH", "insideV")) +
                         f'</w:tblBorders></w:tblPr><w:tblGrid>{grid}</w:tblGrid>' + ''.join(trs) + '</w:tbl>')
        self._p('', 120)

    def image(self, png_path, max_w_in=6.2):
        data = Path(png_path).read_bytes()
        w = int.from_bytes(data[16:20], "big"); h = int.from_bytes(data[20:24], "big")
        cx = int(max_w_in * 914400); cy = int(cx * h / w)
        rid = f"rId{100 + len(self.images)}"; self.images.append((rid, data))
        self.body.append(
            '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="160"/></w:pPr>'
            '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="1" name="Architecture"/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:nvPicPr><pic:cNvPr id="1" name="Architecture"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
            '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')

    def save(self, path):
        document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
            f'<w:body>{"".join(self.body)}<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body></w:document>')
        ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        drels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for i, (rid, _) in enumerate(self.images):
            drels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image{i}.png"/>')
        drels.append('</Relationships>')
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels)
            z.writestr("word/document.xml", document); z.writestr("word/_rels/document.xml.rels", "".join(drels))
            for i, (_, data) in enumerate(self.images):
                z.writestr(f"word/media/image{i}.png", data)
        print("wrote", path)


def money(x): return f"${x:,.0f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="build/spec.json")
    ap.add_argument("--pricing", default="build/pricing.json")
    ap.add_argument("--diagram", default="build/architecture.png")
    ap.add_argument("--flow", default="build/flow.png")
    ap.add_argument("--out", default="build")
    ap.add_argument("--prefix", default="")
    a = ap.parse_args(argv)

    spec = json.loads(Path(a.spec).read_text())
    pr = json.loads(Path(a.pricing).read_text())
    meta = spec["meta"]; foot = (spec.get("branding") or {}).get("footer", "Syntax Corporation © 2026 · Confidential")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    diagram = Path(a.diagram) if Path(a.diagram).exists() else None
    flow = Path(a.flow) if Path(a.flow).exists() else None

    # 1. Installation Guide
    d = Docx(); d.title(f"{meta['agent_name']} — Installation Guide")
    d.subtitle(f"{meta['domain']} · {foot}")
    d.h1("Prerequisites")
    for b in spec["install"]["prereqs"]: d.bullet(b)
    for i, step in enumerate(spec["install"]["steps"], 1):
        d.h1(f"{i}. {step['title']}")
        if step.get("body"): d.para(step["body"])
        for c in step.get("code", []): d.code(c)
    d.footer(foot); d.save(out / f"{a.prefix}Installation_Guide.docx")

    # 2. Technical Design
    td = spec["tech_design"]
    d = Docx(); d.title(f"{meta['agent_name']} — Technical Design")
    d.subtitle(f"{meta['domain']} · Oracle Private Agent Factory")
    d.h1("Architecture")
    if diagram: d.image(diagram)
    d.para(td["intro"])
    if flow:
        d.h1("Functional flow"); d.image(flow)
    d.h1("Processing")
    for b in td["processing"]: d.bullet(b)
    d.h1("Interface contract")
    d.table([["Item", "Value"], *td["interface_contract"]], widths=[3000, 6360])
    d.h1("Assurance"); d.para(td["assurance"])
    d.footer(foot); d.save(out / f"{a.prefix}Technical_Design.docx")

    # 3. Statement of Work (comprehensive, sales-grade)
    sow = spec["sow"]; ms = pr["managed_services"]["medium"]; roi = pr["roi"]
    rs = spec.get("roi_slide", {}); co = rs.get("callout", {})
    d = Docx()
    d.title("Statement of Work")
    d.subtitle(f"{meta['agent_name']} · Syntax Corporation · {foot}")
    d.page_break()

    d.h1("1. Business problem")
    if spec.get("problem", {}).get("note"): d.para(spec["problem"]["note"])
    for c in spec.get("problem", {}).get("cards", []):
        d.bullet(f"{c.get('big','')} — {c.get('desc','')}")

    d.h1("2. Solution")
    for c in spec.get("solution", {}).get("cards", []):
        d.bullet(f"{c.get('title','')}: {c.get('desc','')}")
    if spec.get("solution", {}).get("note"): d.para(spec["solution"]["note"])

    d.h1("3. Value proposition")
    mult = f"; {co.get('multiple')} return on the agent fee" if co.get("multiple") else ""
    d.para(f"Estimated annual value ~{money(roi['gross_annual_value'])}; first-year net "
           f"~{money(roi['net_annual_savings'])}; payback ~{roi['payback_months']} months{mult}.")
    for b in rs.get("bars", []):
        d.bullet(f"{str(b.get('label','')).replace(chr(10), ' ')}: ${b.get('value_k')}K / yr")

    d.h1("4. Functional flow")
    if flow: d.image(flow)
    d.h1("5. Technical architecture")
    if diagram: d.image(diagram)

    d.h1("6. Scope & deliverables")
    for b in sow["deliverables"]: d.bullet(b)

    d.h1("7. Ongoing governance deliverables")
    for b in spec.get("governance", []): d.bullet(b)

    d.h1("8. Implementation timeline")
    tl = spec.get("timeline", {})
    d.para(f"Target duration: {tl.get('weeks','')} weeks.")
    d.table([["Phase", "Weeks", "Outcomes"],
             *[[p["name"], p["weeks"], p["outcomes"]] for p in tl.get("phases", [])]],
            widths=[2200, 1300, 5860])

    d.h1("9. RACI matrix")
    d.table(spec.get("raci_full", sow.get("raci")), widths=[5360, 2000, 2000])

    d.h1("10. Service levels (SLAs)")
    d.table(spec.get("slas", [["Metric", "Target"]]), widths=[5360, 4000])

    d.h1("11. Entitlements")
    d.table(spec.get("entitlements", [["Item", "Included"]]), widths=[3360, 6000])

    d.h1("12. Pricing")
    d.para(f"Implementation (fixed fee, blended ${pr['blended_rate']:.0f}/hr, "
           f"{spec['pricing']['implementation_hours']} hrs):")
    d.table([["Item", "Amount"],
             [f"Implementation (~{spec['pricing']['implementation_hours']} hrs @ ${pr['blended_rate']:.0f} blended)",
              money(pr["implementation_fee"])]], widths=[6360, 3000])
    d.para("Managed services (per month, by commitment term — medium tier):")
    d.table([["Term", "Monthly", "Discount"],
             ["12 months", money(ms["12_month"]["monthly"]), "—"],
             ["24 months", money(ms["24_month"]["monthly"]), f"{ms['24_month']['discount_pct']}%"],
             ["36 months", money(ms["36_month"]["monthly"]), f"{ms['36_month']['discount_pct']}%"]],
            widths=[3360, 3000, 3000])

    d.h1("13. OCI Bill of Materials")
    d.table([["Component", "Pricing model", "Notes"],
             *[[b["component"], b["pricing"], b["notes"]] for b in spec.get("bom", [])]],
            widths=[3800, 3000, 2560])

    d.h1("14. Acceptance & assumptions")
    d.para(f"Acceptance: {sow['acceptance']}.")
    if sow.get("legal_note"): d.para(sow["legal_note"])

    d.h1("15. Signatures")
    d.table([["For Customer", "For Syntax Corporation"], ["Name:", "Name:"],
             ["Title:", "Title:"], ["Signature / Date:", "Signature / Date:"]], widths=[4680, 4680])
    d.footer(foot); d.save(out / f"{a.prefix}SOW.docx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
