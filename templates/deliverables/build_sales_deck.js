/*
 * Syntax Corporation (c) 2026 — PAF Agent Factory
 * build_sales_deck.js — SPEC-DRIVEN Syntax-branded sales/exec deck (pptxgenjs):
 * Problem · Solution · Architecture (hero diagram) · Trust · Monitoring · Proof ·
 * ROI · Why · Next steps. All content from build/spec.json + build/pricing.json;
 * the architecture image from build/architecture.png. v2.1.0 / 2026.06.13.
 * (Monitoring slide is optional — renders when spec.monitoring is present; it is
 *  the "adult supervision" two-plane message: Plane A observability + Plane B
 *  availability. See references/observability.md.)
 *   node build_sales_deck.js --spec build/spec.json --pricing build/pricing.json \
 *        --diagram build/architecture.png --out build/Sample_Sales_Deck.pptx
 *   (needs pptxgenjs + react + react-dom + react-icons + sharp; reuse via NODE_PATH)
 */
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const FA = require("react-icons/fa6");
const fs = require("fs");
const path = require("path");

const NAVY = "0632A0", NAVY_DK = "041F66", GREEN = "3CC85A", CYAN = "1EB4E6",
      GOLD = "F1D488", INK = "16203A", SLATE = "5B6577", PAPER = "FFFFFF",
      MIST = "F4F7FC", LINE = "DCE4F4", MUTE = "CADCFC";
const HEAD = "Georgia", BODY = "Calibri";
const LOGO = path.join(__dirname, "..", "..", "assets", "syntax-logo.png");

function arg(n, d) { const i = process.argv.indexOf("--" + n); return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : d; }
const ICONS = {
  file: FA.FaFileInvoiceDollar, gauge: FA.FaGaugeHigh, magnify: FA.FaMagnifyingGlassDollar,
  robot: FA.FaRobot, database: FA.FaDatabase, scale: FA.FaScaleBalanced, check: FA.FaCircleCheck,
  lock: FA.FaLock, shield: FA.FaShieldHalved, bolt: FA.FaBolt, handshake: FA.FaHandshake,
  gear: FA.FaGears, chart: FA.FaChartLine, clock: FA.FaClock, cloud: FA.FaCloud,
};
async function iconPng(key, color = "#FFFFFF", size = 256) {
  const C = ICONS[key] || FA.FaCircleCheck;
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(C, { color, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

const spec = JSON.parse(fs.readFileSync(arg("spec", "build/spec.json"), "utf8"));
const pr = JSON.parse(fs.readFileSync(arg("pricing", "build/pricing.json"), "utf8"));
const diagram = arg("diagram", "build/architecture.png");
const outFile = arg("out", "build/Sample_Sales_Deck.pptx");
const meta = spec.meta;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; const W = 13.3, H = 7.5;
pres.author = "Syntax Corporation"; pres.title = meta.agent_name;

function triMark(s, x, y, sz, o) { o = o == null ? 1 : o; const t = (1 - o) * 100;
  s.addShape(pres.shapes.LINE, { x, y: y + sz, w: sz, h: 0, line: { color: GREEN, width: 3, transparency: t } });
  s.addShape(pres.shapes.LINE, { x, y: y + sz, w: sz / 2, h: -sz, line: { color: NAVY, width: 3, transparency: t } });
  s.addShape(pres.shapes.LINE, { x: x + sz, y: y + sz, w: -sz / 2, h: -sz, line: { color: CYAN, width: 3, transparency: t } });
}
const shadow = () => ({ type: "outer", color: "0A1A40", blur: 9, offset: 3, angle: 135, opacity: 0.14 });
function footer(s, n) {
  s.addText((spec.branding && spec.branding.footer) || "Syntax Corporation · Confidential",
    { x: 0.6, y: H - 0.42, w: 8, h: 0.3, fontFace: BODY, fontSize: 9, color: SLATE });
  s.addText(String(n), { x: W - 1.0, y: H - 0.42, w: 0.4, h: 0.3, fontFace: BODY, fontSize: 9, color: SLATE, align: "right" });
}
function kicker(s, t) { triMark(s, 0.62, 0.55, 0.22, 1);
  s.addText((t || "").toUpperCase(), { x: 1.0, y: 0.5, w: 11, h: 0.35, fontFace: BODY, fontSize: 12, bold: true, color: NAVY, charSpacing: 3, margin: 0 }); }
function title(s, t) { s.addText(t, { x: 0.6, y: 0.92, w: 12.1, h: 0.9, fontFace: HEAD, fontSize: 28, bold: true, color: INK, margin: 0 }); }

async function build() {
  const keys = new Set(["check"]);
  for (const sec of ["problem", "solution", "controls", "why_us"])
    for (const c of (spec[sec] && spec[sec].cards) || []) if (c.icon) keys.add(c.icon);
  if (spec.monitoring) {
    keys.add(spec.monitoring.plane_a_icon || "gauge");
    keys.add(spec.monitoring.plane_b_icon || "shield");
  }
  const I = {}; for (const k of keys) I[k] = await iconPng(k);

  // 1 TITLE
  let s = pres.addSlide(); s.background = { color: NAVY_DK };
  triMark(s, 9.7, 1.2, 3.1, 0.22);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 0.5, w: 2.5, h: 1.36, rectRadius: 0.1, fill: { color: PAPER }, shadow: shadow() });
  s.addImage({ path: LOGO, x: 0.85, y: 0.66, w: 2.0, h: 2.0 * 0.528 });
  s.addText(meta.kicker || "", { x: 0.62, y: 2.55, w: 11, h: 0.4, fontFace: BODY, fontSize: 13, bold: true, color: CYAN, charSpacing: 3, margin: 0 });
  s.addText(meta.headline, { x: 0.6, y: 2.95, w: 12, h: 1.2, fontFace: HEAD, fontSize: 44, bold: true, color: PAPER, margin: 0 });
  s.addText(meta.subhead, { x: 0.62, y: 4.25, w: 9.4, h: 1.0, fontFace: BODY, fontSize: 16, color: MUTE, margin: 0, lineSpacingMultiple: 1.15 });
  (meta.title_stats || []).forEach((st, i) => { const x = 0.62 + i * 3.0;
    s.addText(st.big, { x, y: 5.55, w: 2.85, h: 0.6, fontFace: HEAD, fontSize: 30, bold: true, color: GREEN, margin: 0 });
    s.addText(st.label, { x, y: 6.15, w: 2.85, h: 0.5, fontFace: BODY, fontSize: 12, color: MUTE, margin: 0 }); });
  s.addText((spec.branding && spec.branding.footer) || "Syntax Corporation © 2026", { x: W - 4.6, y: H - 0.5, w: 4, h: 0.3, align: "right", fontFace: BODY, fontSize: 10, color: "8FA6D8" });

  // 2 PROBLEM
  s = pres.addSlide(); s.background = { color: PAPER };
  kicker(s, "The problem"); title(s, spec.problem.title);
  spec.problem.cards.forEach((c, i) => { const x = 0.6 + i * 4.15;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.0, w: 3.85, h: 3.0, fill: { color: MIST }, line: { color: LINE, width: 1 }, shadow: shadow() });
    s.addShape(pres.shapes.OVAL, { x: x + 0.35, y: 2.4, w: 0.95, h: 0.95, fill: { color: NAVY } });
    s.addImage({ data: I[c.icon] || I.check, x: x + 0.59, y: 2.64, w: 0.47, h: 0.47 });
    s.addText(c.big, { x: x + 0.35, y: 3.55, w: 3.2, h: 0.7, fontFace: HEAD, fontSize: 28, bold: true, color: NAVY, margin: 0 });
    s.addText(c.desc, { x: x + 0.35, y: 4.25, w: 3.2, h: 0.7, fontFace: BODY, fontSize: 13.5, color: INK, margin: 0, lineSpacingMultiple: 1.1 }); });
  if (spec.problem.note) s.addText(spec.problem.note, { x: 0.6, y: 5.4, w: 12.1, h: 0.8, fontFace: BODY, fontSize: 14, color: SLATE, margin: 0, lineSpacingMultiple: 1.15 });
  footer(s, 2);

  // 3 SOLUTION
  s = pres.addSlide(); s.background = { color: PAPER };
  kicker(s, "The solution"); title(s, spec.solution.title);
  spec.solution.cards.forEach((c, i) => { const col = i % 2, row = Math.floor(i / 2), x = 0.6 + col * 6.15, y = 2.05 + row * 1.55;
    s.addShape(pres.shapes.OVAL, { x, y, w: 0.95, h: 0.95, fill: { color: col ? CYAN : NAVY } });
    s.addImage({ data: I[c.icon] || I.check, x: x + 0.24, y: y + 0.24, w: 0.47, h: 0.47 });
    s.addText(c.title, { x: x + 1.15, y: y - 0.05, w: 4.9, h: 0.45, fontFace: HEAD, fontSize: 18, bold: true, color: INK, margin: 0 });
    s.addText(c.desc, { x: x + 1.15, y: y + 0.42, w: 4.9, h: 1.0, fontFace: BODY, fontSize: 12.5, color: SLATE, margin: 0, lineSpacingMultiple: 1.1 }); });
  if (spec.solution.note) s.addText(spec.solution.note, { x: 0.6, y: 5.5, w: 12.1, h: 0.5, fontFace: BODY, fontSize: 13, italic: true, color: NAVY, margin: 0 });
  footer(s, 3);

  // 4 ARCHITECTURE
  s = pres.addSlide(); s.background = { color: PAPER };
  kicker(s, "Architecture"); title(s, spec.architecture.title);
  if (fs.existsSync(diagram)) s.addImage({ path: diagram, x: 1.35, y: 1.6, w: 10.6, h: 10.6 * (900 / 1600) });
  footer(s, 4);

  // 5 TRUST / CONTROLS
  if (spec.controls) {
    s = pres.addSlide(); s.background = { color: PAPER };
    kicker(s, "Trust & control"); title(s, spec.controls.title);
    spec.controls.cards.forEach((c, i) => { const row = Math.floor(i / 2), col = i % 2, x = 0.6 + col * 6.15, y = 2.1 + row * 1.6;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 5.9, h: 1.4, fill: { color: MIST }, line: { color: LINE, width: 1 } });
      s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.32, w: 0.78, h: 0.78, fill: { color: GREEN } });
      s.addImage({ data: I[c.icon] || I.check, x: x + 0.49, y: y + 0.51, w: 0.4, h: 0.4 });
      s.addText(c.title, { x: x + 1.3, y: y + 0.2, w: 4.4, h: 0.4, fontFace: HEAD, fontSize: 15.5, bold: true, color: INK, margin: 0 });
      s.addText(c.desc, { x: x + 1.3, y: y + 0.6, w: 4.45, h: 0.75, fontFace: BODY, fontSize: 11.5, color: SLATE, margin: 0, lineSpacingMultiple: 1.08 }); });
    if (spec.controls.note) s.addText(spec.controls.note, { x: 0.6, y: 5.55, w: 12.1, h: 0.5, fontFace: BODY, fontSize: 13, italic: true, color: NAVY, margin: 0 });
    footer(s, 5);
  }

  // 6 MONITORING / OBSERVABILITY (optional) — "adult supervision"
  let n = spec.controls ? 6 : 5;
  if (spec.monitoring) {
    const m = spec.monitoring;
    s = pres.addSlide(); s.background = { color: PAPER };
    kicker(s, m.kicker || "Adult supervision"); title(s, m.title);
    const planes = [
      { d: m.plane_a, accent: CYAN,  tag: "PLANE A",
        role: m.plane_a_role || "Agent observability — the differentiator", icon: m.plane_a_icon || "gauge" },
      { d: m.plane_b, accent: GREEN, tag: "PLANE B",
        role: m.plane_b_role || "Platform availability — table stakes",     icon: m.plane_b_icon || "shield" },
    ];
    planes.forEach((pl, i) => {
      if (!pl.d) return;
      const x = 0.6 + i * 6.15, y = 2.0, w = 5.9, hh = 3.25;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: hh, fill: { color: MIST }, line: { color: LINE, width: 1 }, shadow: shadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.62, fill: { color: pl.accent } });
      s.addShape(pres.shapes.OVAL, { x: x + 0.22, y: y + 0.13, w: 0.36, h: 0.36, fill: { color: PAPER } });
      s.addImage({ data: I[pl.icon] || I.check, x: x + 0.285, y: y + 0.195, w: 0.23, h: 0.23 });
      s.addText(pl.tag, { x: x + 0.72, y: y + 0.12, w: 1.6, h: 0.38, fontFace: BODY, fontSize: 12, bold: true, color: PAPER, charSpacing: 2, valign: "middle", margin: 0 });
      s.addText(pl.role, { x: x + 2.1, y: y + 0.12, w: w - 2.25, h: 0.38, fontFace: BODY, fontSize: 10.5, color: PAPER, valign: "middle", align: "right", margin: 0 });
      const bullets = (pl.d.points || []).map(t => ({ text: t, options: { bullet: { code: "2022", indent: 14 }, breakLine: true, paraSpaceAfter: 7 } }));
      s.addText(bullets, { x: x + 0.4, y: y + 0.82, w: w - 0.78, h: hh - 1.0, fontFace: BODY, fontSize: 12.5, color: INK, margin: 0, lineSpacingMultiple: 1.08, valign: "top" });
    });
    const chips = m.chips || ["Masking on by default", "One OAuth client per agent", "Correlated in OCI Logging Analytics"];
    chips.slice(0, 3).forEach((c, i) => { const x = 0.6 + i * 4.1;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.5, w: 3.85, h: 0.55, rectRadius: 0.06, fill: { color: NAVY } });
      s.addText(c, { x: x + 0.12, y: 5.5, w: 3.61, h: 0.55, fontFace: BODY, fontSize: 11.5, bold: true, color: PAPER, valign: "middle", align: "center", margin: 0 }); });
    if (m.note) s.addText(m.note, { x: 0.6, y: 6.22, w: 12.1, h: 0.5, fontFace: BODY, fontSize: 13, italic: true, color: NAVY, margin: 0, lineSpacingMultiple: 1.1 });
    footer(s, n); n++;
  }

  // 7 PROOF (optional)
  if (spec.proof) {
    const p = spec.proof;
    s = pres.addSlide(); s.background = { color: NAVY_DK };
    triMark(s, 11.4, 0.5, 1.4, 0.25);
    s.addText((p.kicker || "").toUpperCase(), { x: 0.6, y: 0.55, w: 11, h: 0.35, fontFace: BODY, fontSize: 12, bold: true, color: CYAN, charSpacing: 3, margin: 0 });
    s.addText(p.title, { x: 0.6, y: 0.95, w: 12, h: 0.8, fontFace: HEAD, fontSize: 28, bold: true, color: PAPER, margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 2.05, w: 6.0, h: 4.4, fill: { color: "0B2A78" } });
    s.addText(p.scenario_title, { x: 0.95, y: 2.3, w: 5.4, h: 0.5, fontFace: HEAD, fontSize: 19, bold: true, color: PAPER, margin: 0 });
    s.addText(p.scenario_sub, { x: 0.95, y: 2.78, w: 5.4, h: 0.4, fontFace: BODY, fontSize: 12, color: CYAN, margin: 0 });
    (p.rows || []).forEach((r, i) => { const y = 3.35 + i * 0.78;
      s.addImage({ data: I.check, x: 0.95, y: y + 0.04, w: 0.34, h: 0.34 });
      s.addText(r.a, { x: 1.45, y, w: 5.0, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true, color: PAPER, margin: 0 });
      s.addText(r.b, { x: 1.45, y: y + 0.34, w: 5.0, h: 0.32, fontFace: BODY, fontSize: 11, color: "B9CCF2", margin: 0 }); });
    s.addShape(pres.shapes.RECTANGLE, { x: 6.95, y: 2.05, w: 5.75, h: 4.4, fill: { color: PAPER }, shadow: shadow() });
    s.addShape(pres.shapes.OVAL, { x: 9.35, y: 2.45, w: 1.0, h: 1.0, fill: { color: GREEN } });
    s.addImage({ data: I.check, x: 9.59, y: 2.69, w: 0.52, h: 0.52 });
    s.addText("QA STATUS", { x: 7.2, y: 3.6, w: 5.25, h: 0.35, align: "center", fontFace: BODY, fontSize: 12, bold: true, color: SLATE, charSpacing: 3, margin: 0 });
    s.addText(p.status || "PASS", { x: 7.2, y: 3.92, w: 5.25, h: 0.9, align: "center", fontFace: HEAD, fontSize: 54, bold: true, color: GREEN, margin: 0 });
    if (p.status_note) s.addText(p.status_note, { x: 7.2, y: 4.95, w: 5.25, h: 0.4, align: "center", fontFace: BODY, fontSize: 13, color: INK, margin: 0 });
    if (p.caption) s.addText(p.caption, { x: 7.2, y: 5.5, w: 5.25, h: 0.7, align: "center", fontFace: BODY, fontSize: 11.5, italic: true, color: SLATE, margin: 0, lineSpacingMultiple: 1.1 });
    s.addText((spec.branding && spec.branding.footer) || "Syntax Corporation · Confidential", { x: 0.6, y: H - 0.42, w: 6, h: 0.3, fontFace: BODY, fontSize: 9, color: "8FA6D8" });
    n++;
  }

  // 7 ROI
  const rs = spec.roi_slide;
  s = pres.addSlide(); s.background = { color: PAPER };
  kicker(s, "Business case"); title(s, rs.title);
  s.addChart(pres.charts.BAR, [{ name: "Annual value ($K)",
    labels: rs.bars.map(b => b.label), values: rs.bars.map(b => b.value_k) }], {
    x: 0.6, y: 2.0, w: 7.4, h: 4.4, barDir: "col", chartColors: [NAVY, CYAN, GREEN, GOLD],
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontFace: BODY,
    dataLabelFontSize: 11, dataLabelFormatCode: '"$"0"K"', catAxisLabelColor: SLATE,
    catAxisLabelFontFace: BODY, catAxisLabelFontSize: 10, valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, showTitle: false });
  const co = rs.callout || {};
  s.addShape(pres.shapes.RECTANGLE, { x: 8.4, y: 2.0, w: 4.3, h: 4.4, fill: { color: NAVY_DK } });
  s.addText(co.label || "Agent list price", { x: 8.7, y: 2.35, w: 3.7, h: 0.4, fontFace: BODY, fontSize: 12, color: CYAN, charSpacing: 2, margin: 0 });
  s.addText(co.big || "", { x: 8.7, y: 2.7, w: 3.7, h: 0.7, fontFace: HEAD, fontSize: 32, bold: true, color: PAPER, margin: 0 });
  if (co.sub) s.addText(co.sub, { x: 8.7, y: 3.4, w: 3.7, h: 0.35, fontFace: BODY, fontSize: 11, color: "B9CCF2", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 8.7, y: 4.0, w: 3.7, h: 0, line: { color: "27468F", width: 1 } });
  s.addText(co.multiple || "", { x: 8.7, y: 4.2, w: 3.7, h: 0.7, fontFace: HEAD, fontSize: 40, bold: true, color: GREEN, margin: 0 });
  if (co.multiple_note) s.addText(co.multiple_note, { x: 8.7, y: 4.95, w: 3.7, h: 1.0, fontFace: BODY, fontSize: 12, color: "E7EEFF", margin: 0, lineSpacingMultiple: 1.12 });
  s.addText(`Net ~$${Math.round(pr.roi.net_annual_savings).toLocaleString()}/yr · payback ~${pr.roi.payback_months} mo · implementation $${Math.round(pr.implementation_fee).toLocaleString()} (fixed)`,
    { x: 0.6, y: 6.55, w: 12.1, h: 0.4, fontFace: BODY, fontSize: 12, italic: true, color: SLATE, margin: 0 });
  footer(s, n); n++;

  // 8 WHY US
  if (spec.why_us) {
    s = pres.addSlide(); s.background = { color: PAPER };
    kicker(s, "Why Syntax"); title(s, spec.why_us.title);
    spec.why_us.cards.forEach((c, i) => { const x = 0.6 + i * 4.15, ac = [NAVY, CYAN, GREEN][i % 3];
      s.addShape(pres.shapes.RECTANGLE, { x, y: 2.1, w: 3.85, h: 3.4, fill: { color: MIST }, line: { color: LINE, width: 1 }, shadow: shadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y: 2.1, w: 3.85, h: 0.12, fill: { color: ac } });
      s.addShape(pres.shapes.OVAL, { x: x + 0.35, y: 2.55, w: 0.95, h: 0.95, fill: { color: ac } });
      s.addImage({ data: I[c.icon] || I.check, x: x + 0.59, y: 2.79, w: 0.47, h: 0.47 });
      s.addText(c.title, { x: x + 0.35, y: 3.7, w: 3.2, h: 0.5, fontFace: HEAD, fontSize: 17, bold: true, color: INK, margin: 0 });
      s.addText(c.desc, { x: x + 0.35, y: 4.2, w: 3.25, h: 1.2, fontFace: BODY, fontSize: 12.5, color: SLATE, margin: 0, lineSpacingMultiple: 1.12 }); });
    footer(s, n); n++;
  }

  // 9 NEXT STEPS
  s = pres.addSlide(); s.background = { color: NAVY_DK };
  triMark(s, 10.6, 4.2, 2.4, 0.22);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 0.6, w: 2.35, h: 1.28, rectRadius: 0.1, fill: { color: PAPER } });
  s.addImage({ path: LOGO, x: 0.83, y: 0.74, w: 1.85, h: 1.85 * 0.528 });
  s.addText("NEXT STEPS", { x: 0.62, y: 2.2, w: 8, h: 0.4, fontFace: BODY, fontSize: 13, bold: true, color: CYAN, charSpacing: 3, margin: 0 });
  s.addText(spec.next_steps.title, { x: 0.6, y: 2.6, w: 12, h: 0.9, fontFace: HEAD, fontSize: 32, bold: true, color: PAPER, margin: 0 });
  spec.next_steps.steps.forEach((st, i) => { const x = 0.62 + i * 4.1;
    s.addShape(pres.shapes.OVAL, { x, y: 3.85, w: 0.7, h: 0.7, fill: { color: GREEN } });
    s.addText(String(i + 1), { x, y: 3.85, w: 0.7, h: 0.7, align: "center", valign: "middle", fontFace: HEAD, fontSize: 22, bold: true, color: NAVY_DK, margin: 0 });
    s.addText(st.title, { x: x + 0.85, y: 3.9, w: 3.1, h: 0.5, fontFace: HEAD, fontSize: 17, bold: true, color: PAPER, margin: 0 });
    s.addText(st.desc, { x, y: 4.7, w: 3.85, h: 1.1, fontFace: BODY, fontSize: 12.5, color: MUTE, margin: 0, lineSpacingMultiple: 1.15 }); });
  s.addShape(pres.shapes.LINE, { x: 0.62, y: 6.2, w: 12.1, h: 0, line: { color: "27468F", width: 1 } });
  s.addText(`${(spec.branding && spec.branding.footer) || "Syntax Corporation © 2026"}  ·  ${meta.agent_name}`,
    { x: 0.62, y: 6.45, w: 12, h: 0.4, fontFace: BODY, fontSize: 12, color: "8FA6D8", margin: 0 });

  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  await pres.writeFile({ fileName: outFile });
  console.log("wrote", outFile);
}
build().catch(e => { console.error(e); process.exit(1); });
