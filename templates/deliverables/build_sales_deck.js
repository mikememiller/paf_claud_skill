/*
 * Syntax Corporation (c) 2026 - EBS AP PAF
 * Exec/sales deck generator (pptxgenjs). v1.0.0 / build 2026.06.02
 */
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa6");

// ---- Syntax brand palette -------------------------------------------------
const NAVY = "0632A0";
const NAVY_DK = "041F66";
const GREEN = "3CC85A";
const CYAN = "1EB4E6";
const GOLD = "F1D488";
const INK = "16203A";
const SLATE = "5B6577";
const PAPER = "FFFFFF";
const MIST = "F4F7FC";
const LINE = "DCE4F4";

const LOGO = "assets/syntax-logo.png";

async function icon(IconComponent, color = "#FFFFFF", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
const W = 13.3, H = 7.5;
pres.author = "Syntax Corporation";
pres.title = "EBS AP Invoice Automation Agent";

const HEAD = "Georgia";
const BODY = "Calibri";

// Repeated tri-color triangle motif (echoes the Syntax logo mark)
function triMark(slide, x, y, s, opacity) {
  const o = opacity == null ? 1 : opacity;
  slide.addShape(pres.shapes.LINE, { x, y: y + s, w: s, h: 0, line: { color: GREEN, width: 3, transparency: (1 - o) * 100 } });
  slide.addShape(pres.shapes.LINE, { x, y: y + s, w: s / 2, h: -s, line: { color: NAVY, width: 3, transparency: (1 - o) * 100 } });
  slide.addShape(pres.shapes.LINE, { x: x + s, y: y + s, w: -s / 2, h: -s, line: { color: CYAN, width: 3, transparency: (1 - o) * 100 } });
}

function footer(slide, n) {
  slide.addText("Syntax Corporation  ·  Confidential", { x: 0.6, y: H - 0.42, w: 6, h: 0.3, fontFace: BODY, fontSize: 9, color: SLATE });
  slide.addText(String(n), { x: W - 1.0, y: H - 0.42, w: 0.4, h: 0.3, fontFace: BODY, fontSize: 9, color: SLATE, align: "right" });
}

function kicker(slide, text) {
  triMark(slide, 0.62, 0.55, 0.22, 1);
  slide.addText(text.toUpperCase(), { x: 1.0, y: 0.5, w: 9, h: 0.35, fontFace: BODY, fontSize: 12, bold: true, color: NAVY, charSpacing: 3, margin: 0 });
}

function title(slide, text) {
  slide.addText(text, { x: 0.6, y: 0.92, w: 12.1, h: 0.9, fontFace: HEAD, fontSize: 30, bold: true, color: INK, margin: 0 });
}

function makeShadow() {
  return { type: "outer", color: "0A1A40", blur: 9, offset: 3, angle: 135, opacity: 0.14 };
}

async function build() {
  const I = {
    bolt: await icon(fa.FaBolt, "#FFFFFF"),
    file: await icon(fa.FaFileInvoiceDollar, "#FFFFFF"),
    shield: await icon(fa.FaShieldHalved, "#FFFFFF"),
    check: await icon(fa.FaCircleCheck, "#FFFFFF"),
    robot: await icon(fa.FaRobot, "#FFFFFF"),
    scale: await icon(fa.FaScaleBalanced, "#FFFFFF"),
    magnify: await icon(fa.FaMagnifyingGlassDollar, "#FFFFFF"),
    lock: await icon(fa.FaLock, "#FFFFFF"),
    database: await icon(fa.FaDatabase, "#FFFFFF"),
    gauge: await icon(fa.FaGaugeHigh, "#FFFFFF"),
    handshake: await icon(fa.FaHandshake, "#FFFFFF"),
    arrow: await icon(fa.FaArrowRight, "#" + NAVY),
  };

  // ===================================================================== 1 TITLE
  let s = pres.addSlide();
  s.background = { color: NAVY_DK };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: H, fill: { color: NAVY_DK } });
  // large faint triangle motif
  triMark(s, 9.7, 1.2, 3.1, 0.22);
  // logo on white chip (native logo is 1000x528 -> ratio 0.528)
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 0.5, w: 2.5, h: 1.36, rectRadius: 0.1, fill: { color: PAPER }, shadow: makeShadow() });
  s.addImage({ path: LOGO, x: 0.85, y: 0.66, w: 2.0, h: 2.0 * 0.528 });
  s.addText("PRIVATE AGENT FACTORY  ·  ORACLE E-BUSINESS SUITE", { x: 0.62, y: 2.55, w: 11, h: 0.4, fontFace: BODY, fontSize: 13, bold: true, color: CYAN, charSpacing: 3, margin: 0 });
  s.addText("AP Invoice Automation Agent", { x: 0.6, y: 2.95, w: 12, h: 1.2, fontFace: HEAD, fontSize: 46, bold: true, color: PAPER, margin: 0 });
  s.addText("Invoice-to-Match for EBS — extract, 3-way match, and code supplier invoices straight into the Payables Open Interface, validated against your live EBS data.",
    { x: 0.62, y: 4.2, w: 9.3, h: 1.0, fontFace: BODY, fontSize: 16, color: "CADCFC", margin: 0, lineSpacingMultiple: 1.15 });
  // accent bottom stat row
  const tstats = [["$2–3", "cost / invoice, automated"], ["~$930K", "annual value (50K invoices)"], ["100%", "audit trail preserved"]];
  tstats.forEach(([a, b], i) => {
    const x = 0.62 + i * 3.0;
    s.addText(a, { x, y: 5.55, w: 2.8, h: 0.6, fontFace: HEAD, fontSize: 30, bold: true, color: GREEN, margin: 0 });
    s.addText(b, { x, y: 6.15, w: 2.8, h: 0.5, fontFace: BODY, fontSize: 12, color: "CADCFC", margin: 0 });
  });
  s.addText("Syntax Corporation © 2026", { x: W - 4.6, y: H - 0.5, w: 4, h: 0.3, align: "right", fontFace: BODY, fontSize: 10, color: "8FA6D8" });

  // ===================================================================== 2 PROBLEM
  s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "The problem");
  title(s, "Manual AP is slow, costly, and error-prone");
  const probCards = [
    [I.file, "$12–15", "fully-loaded cost to process one invoice by hand"],
    [I.gauge, "8–10 days", "typical cycle time — late payments, missed discounts"],
    [I.magnify, "1–3%", "of spend lost to duplicate and over-billed invoices"],
  ];
  probCards.forEach(([ic, big, desc], i) => {
    const x = 0.6 + i * 4.15;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.0, w: 3.85, h: 3.0, fill: { color: MIST }, line: { color: LINE, width: 1 }, shadow: makeShadow() });
    s.addShape(pres.shapes.OVAL, { x: x + 0.35, y: 2.4, w: 0.95, h: 0.95, fill: { color: NAVY } });
    s.addImage({ data: ic, x: x + 0.59, y: 2.64, w: 0.47, h: 0.47 });
    s.addText(big, { x: x + 0.35, y: 3.55, w: 3.2, h: 0.7, fontFace: HEAD, fontSize: 30, bold: true, color: NAVY, margin: 0 });
    s.addText(desc, { x: x + 0.35, y: 4.25, w: 3.2, h: 0.7, fontFace: BODY, fontSize: 13.5, color: INK, margin: 0, lineSpacingMultiple: 1.1 });
  });
  s.addText([
    { text: "AP automation is a $3B+ category with multiple unicorns. ", options: { bold: true, color: INK } },
    { text: "Every EBS shop runs tens of thousands to millions of invoices a year — and pays incumbents $3–8 each for it.", options: { color: SLATE } },
  ], { x: 0.6, y: 5.35, w: 12.1, h: 0.8, fontFace: BODY, fontSize: 14.5, margin: 0, lineSpacingMultiple: 1.15 });
  footer(s, 2);

  // ===================================================================== 3 SOLUTION
  s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "The solution");
  title(s, "An EBS-native agent that does the AP grunt work");
  const sol = [
    [I.robot, "Reads any invoice", "PDF, email or text — a deterministic parser (zero external deps) with an optional LLM for messy/scanned documents."],
    [I.database, "Checks live EBS", "Supplier, PO, receipts, tax and GL — read-only, org-scoped lookups against the real E-Business Suite."],
    [I.scale, "Matches & codes", "Deterministic 3-way match with price/qty tolerances, GL distribution inheritance and tax classification."],
    [I.check, "Validates & delivers", "A QA gate proves every invoice balances before it writes balanced AP Open Interface files."],
  ];
  sol.forEach(([ic, h, d], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.6 + col * 6.15, y = 2.05 + row * 1.55;
    s.addShape(pres.shapes.OVAL, { x, y, w: 0.95, h: 0.95, fill: { color: i % 2 ? CYAN : NAVY } });
    s.addImage({ data: ic, x: x + 0.24, y: y + 0.24, w: 0.47, h: 0.47 });
    s.addText(h, { x: x + 1.15, y: y - 0.05, w: 4.9, h: 0.45, fontFace: HEAD, fontSize: 18, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: x + 1.15, y: y + 0.42, w: 4.9, h: 1.0, fontFace: BODY, fontSize: 12.5, color: SLATE, margin: 0, lineSpacingMultiple: 1.1 });
  });
  s.addText("Same architecture as Oracle's Private Agent Factory contract-renewal blog — pointed at the far larger AP revenue pool.",
    { x: 0.6, y: 5.5, w: 12.1, h: 0.5, fontFace: BODY, fontSize: 13, italic: true, color: NAVY, margin: 0 });
  footer(s, 3);

  // ===================================================================== 4 ARCHITECTURE
  s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "Architecture");
  title(s, "Document → agent → EBS → interface");
  const flow = [
    [I.file, "Supplier invoice", "PDF / email / text", NAVY],
    [I.robot, "Invoice Agent", "extract · match · code", CYAN],
    [I.database, "EBS (read-only)", "via MCP tools", GREEN],
    [I.check, "AP Open Interface", "balanced CSV + QA", NAVY],
  ];
  const fy = 2.45, fw = 2.7, gap = 0.55;
  flow.forEach(([ic, h, d, c], i) => {
    const x = 0.6 + i * (fw + gap);
    s.addShape(pres.shapes.RECTANGLE, { x, y: fy, w: fw, h: 2.0, fill: { color: MIST }, line: { color: LINE, width: 1 }, shadow: makeShadow() });
    s.addShape(pres.shapes.OVAL, { x: x + fw / 2 - 0.5, y: fy + 0.28, w: 1.0, h: 1.0, fill: { color: c } });
    s.addImage({ data: ic, x: x + fw / 2 - 0.26, y: fy + 0.52, w: 0.52, h: 0.52 });
    s.addText(h, { x: x + 0.1, y: fy + 1.32, w: fw - 0.2, h: 0.4, align: "center", fontFace: HEAD, fontSize: 14.5, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: x + 0.1, y: fy + 1.68, w: fw - 0.2, h: 0.3, align: "center", fontFace: BODY, fontSize: 11, color: SLATE, margin: 0 });
    if (i < 3) s.addImage({ data: I.arrow, x: x + fw + 0.07, y: fy + 0.85, w: 0.4, h: 0.4 });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 5.05, w: 12.1, h: 1.25, fill: { color: NAVY_DK } });
  s.addText([
    { text: "The agent never writes to the base AP tables.  ", options: { bold: true, color: GREEN } },
    { text: "It produces interface files for the standard Payables Open Interface Import — every existing AP control, approval and audit trail stays in force.", options: { color: "E7EEFF" } },
  ], { x: 0.95, y: 5.25, w: 11.4, h: 0.85, fontFace: BODY, fontSize: 14, valign: "middle", margin: 0, lineSpacingMultiple: 1.12 });
  footer(s, 4);

  // ===================================================================== 5 CONTROLS / TRUST
  s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "Trust & control");
  title(s, "Built for auditors, not just speed");
  const ctrl = [
    [I.lock, "Read-only by design", "Only SELECTs against EBS; the single write path is off by default and touches interface tables only."],
    [I.shield, "Multi-org safe", "Org-scoped queries and FND_GLOBAL.APPS_INITIALIZE context; bind variables everywhere — no SQL injection surface."],
    [I.scale, "Deterministic policy", "Match, tolerance and coding rules live outside the LLM — reproducible and explainable for SOX."],
    [I.check, "QA gate before load", "Every invoice is checked to balance, reconcile and resolve all FKs; failures are held, never imported."],
  ];
  ctrl.forEach(([ic, h, d], i) => {
    const row = Math.floor(i / 2), col = i % 2;
    const x = 0.6 + col * 6.15, y = 2.1 + row * 1.6;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 5.9, h: 1.4, fill: { color: MIST }, line: { color: LINE, width: 1 } });
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.32, w: 0.78, h: 0.78, fill: { color: GREEN } });
    s.addImage({ data: ic, x: x + 0.49, y: y + 0.51, w: 0.4, h: 0.4 });
    s.addText(h, { x: x + 1.3, y: y + 0.2, w: 4.4, h: 0.4, fontFace: HEAD, fontSize: 15.5, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: x + 1.3, y: y + 0.6, w: 4.45, h: 0.75, fontFace: BODY, fontSize: 11.5, color: SLATE, margin: 0, lineSpacingMultiple: 1.08 });
  });
  s.addText("Every interface row is stamped with the agent run-id and a confidence score — traceable end to end.",
    { x: 0.6, y: 5.55, w: 12.1, h: 0.5, fontFace: BODY, fontSize: 13, italic: true, color: NAVY, margin: 0 });
  footer(s, 5);

  // ===================================================================== 6 LIVE PROOF
  s = pres.addSlide();
  s.background = { color: NAVY_DK };
  triMark(s, 11.4, 0.5, 1.4, 0.25);
  s.addText("PROVEN ON LIVE EBS VISION DATA", { x: 0.6, y: 0.55, w: 11, h: 0.35, fontFace: BODY, fontSize: 12, bold: true, color: CYAN, charSpacing: 3, margin: 0 });
  s.addText("Real invoice. Real PO. Clean match.", { x: 0.6, y: 0.95, w: 12, h: 0.8, fontFace: HEAD, fontSize: 30, bold: true, color: PAPER, margin: 0 });
  // left: the scenario
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 2.05, w: 6.0, h: 4.4, fill: { color: "0B2A78" } });
  s.addText("Purchase Order 3495", { x: 0.95, y: 2.3, w: 5.4, h: 0.5, fontFace: HEAD, fontSize: 19, bold: true, color: PAPER, margin: 0 });
  s.addText("Advanced Network Devices · Org 204 · Oracle EBS 19c Vision", { x: 0.95, y: 2.78, w: 5.4, h: 0.4, fontFace: BODY, fontSize: 12, color: CYAN, margin: 0 });
  const rows = [
    ["4 lines", "monitors, RAM, hard drives"],
    ["500 / 500", "invoiced vs received on every line"],
    ["01-520-7530-0000-000", "GL distribution inherited from the PO"],
    ["$632,500.00", "invoice total — header balances to lines"],
  ];
  rows.forEach(([a, b], i) => {
    const y = 3.35 + i * 0.78;
    s.addImage({ data: I.check, x: 0.95, y: y + 0.04, w: 0.34, h: 0.34 });
    s.addText(a, { x: 1.45, y, w: 5.0, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true, color: PAPER, margin: 0 });
    s.addText(b, { x: 1.45, y: y + 0.34, w: 5.0, h: 0.32, fontFace: BODY, fontSize: 11, color: "B9CcF2", margin: 0 });
  });
  // right: result badge
  s.addShape(pres.shapes.RECTANGLE, { x: 6.95, y: 2.05, w: 5.75, h: 4.4, fill: { color: PAPER }, shadow: makeShadow() });
  s.addShape(pres.shapes.OVAL, { x: 9.35, y: 2.45, w: 1.0, h: 1.0, fill: { color: GREEN } });
  s.addImage({ data: I.check, x: 9.59, y: 2.69, w: 0.52, h: 0.52 });
  s.addText("QA STATUS", { x: 7.2, y: 3.6, w: 5.25, h: 0.35, align: "center", fontFace: BODY, fontSize: 12, bold: true, color: SLATE, charSpacing: 3, margin: 0 });
  s.addText("PASS", { x: 7.2, y: 3.92, w: 5.25, h: 0.9, align: "center", fontFace: HEAD, fontSize: 54, bold: true, color: GREEN, margin: 0 });
  s.addText("All 4 lines auto-approved · 0 errors · loadable", { x: 7.2, y: 4.95, w: 5.25, h: 0.4, align: "center", fontFace: BODY, fontSize: 13, color: INK, margin: 0 });
  s.addText("Verified against the live database during the build — not a mock.", { x: 7.2, y: 5.5, w: 5.25, h: 0.7, align: "center", fontFace: BODY, fontSize: 11.5, italic: true, color: SLATE, margin: 0, lineSpacingMultiple: 1.1 });
  s.addText("Syntax Corporation  ·  Confidential", { x: 0.6, y: H - 0.42, w: 6, h: 0.3, fontFace: BODY, fontSize: 9, color: "8FA6D8" });

  // ===================================================================== 7 ROI
  s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "Business case");
  title(s, "~$930K of annual value at 50K invoices/yr");
  s.addChart(pres.charts.BAR, [{
    name: "Annual value ($K)",
    labels: ["Processing\ncost", "Early-pay\ndiscounts", "Duplicate\nprevention", "Audit /\ncompliance"],
    values: [475, 225, 150, 80],
  }], {
    x: 0.6, y: 2.0, w: 7.4, h: 4.4, barDir: "col",
    chartColors: [NAVY, CYAN, GREEN, GOLD],
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontFace: BODY, dataLabelFontSize: 11, dataLabelFormatCode: '"$"0"K"',
    catAxisLabelColor: SLATE, catAxisLabelFontFace: BODY, catAxisLabelFontSize: 10,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, showTitle: false,
  });
  // right callout
  s.addShape(pres.shapes.RECTANGLE, { x: 8.4, y: 2.0, w: 4.3, h: 4.4, fill: { color: NAVY_DK } });
  s.addText("Agent list price", { x: 8.7, y: 2.35, w: 3.7, h: 0.4, fontFace: BODY, fontSize: 12, color: CYAN, charSpacing: 2, margin: 0 });
  s.addText("$25K–$50K", { x: 8.7, y: 2.7, w: 3.7, h: 0.7, fontFace: HEAD, fontSize: 32, bold: true, color: PAPER, margin: 0 });
  s.addText("per year, priced per invoice", { x: 8.7, y: 3.4, w: 3.7, h: 0.35, fontFace: BODY, fontSize: 11, color: "B9CcF2", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 8.7, y: 4.0, w: 3.7, h: 0, line: { color: "27468F", width: 1 } });
  s.addText("20–40×", { x: 8.7, y: 4.2, w: 3.7, h: 0.7, fontFace: HEAD, fontSize: 40, bold: true, color: GREEN, margin: 0 });
  s.addText("return on the agent fee — with margin to share with implementation partners.", { x: 8.7, y: 4.95, w: 3.7, h: 1.0, fontFace: BODY, fontSize: 12, color: "E7EEFF", margin: 0, lineSpacingMultiple: 1.12 });
  footer(s, 7);

  // ===================================================================== 8 TCO
  s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "Cost to operate");
  title(s, "Runs on OCI infrastructure you already own");
  const tco = [
    [{ text: "Tier", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontFace: BODY } },
     { text: "Invoices / yr", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontFace: BODY, align: "center" } },
     { text: "Annual (License Incl.)", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontFace: BODY, align: "center" } },
     { text: "Annual (BYOL)", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontFace: BODY, align: "center" } }],
    ["Small — single BU", "5,000", "~$6,800", "~$2,150"],
    ["Medium — multi-BU", "50,000", "~$26,900", "~$8,300"],
    ["Large — F500 multi-org", "500,000", "~$120,500", "~$45,000"],
  ];
  s.addTable(tco, {
    x: 0.6, y: 2.05, w: 8.0, colW: [3.1, 1.6, 1.85, 1.45], rowH: [0.55, 0.7, 0.7, 0.7],
    fontFace: BODY, fontSize: 13, valign: "middle", align: "center", color: INK,
    border: { type: "solid", pt: 1, color: LINE }, fill: { color: PAPER },
  });
  // make first column left aligned by overlay note - keep simple; add context card
  s.addShape(pres.shapes.RECTANGLE, { x: 8.9, y: 2.05, w: 3.8, h: 2.65, fill: { color: MIST }, line: { color: LINE, width: 1 } });
  s.addText("Why so low", { x: 9.15, y: 2.25, w: 3.4, h: 0.4, fontFace: HEAD, fontSize: 16, bold: true, color: NAVY, margin: 0 });
  s.addText([
    { text: "Private Agent Factory is $0", options: { bullet: true, breakLine: true, bold: true } },
    { text: " — included with AI Database 26ai", options: { breakLine: true } },
    { text: "BYOL drops DB cost ~76%", options: { bullet: true, breakLine: true } },
    { text: "Support Rewards can offset the OCI bill", options: { bullet: true } },
  ], { x: 9.15, y: 2.7, w: 3.4, h: 1.9, fontFace: BODY, fontSize: 11.5, color: INK, margin: 0, paraSpaceAfter: 4 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 5.15, w: 12.1, h: 1.1, fill: { color: NAVY_DK } });
  s.addText([
    { text: "The F500 tier processes 500K invoices/yr for ~$120K list ($45K BYOL). ", options: { bold: true, color: GREEN } },
    { text: "AP incumbents charge $1–3 each for that volume — $500K to $1.5M/yr.", options: { color: "E7EEFF" } },
  ], { x: 0.95, y: 5.3, w: 11.4, h: 0.8, fontFace: BODY, fontSize: 14, valign: "middle", margin: 0, lineSpacingMultiple: 1.12 });
  footer(s, 8);

  // ===================================================================== 9 WHY SYNTAX
  s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "Why Syntax");
  title(s, "The partner to put this into production");
  const why = [
    [I.database, "Deep EBS expertise", "Decades running Oracle E-Business Suite for enterprise customers — we know your AP, PO and GL setup."],
    [I.bolt, "Reference build in hand", "A working, QA'd agent proven against live Vision data — not slideware. Ready to point at your instance."],
    [I.handshake, "OCI + PAF aligned", "Positioned for the Private Agent Factory motion on AI Database 26ai, with TCO and licensing mapped."],
  ];
  why.forEach(([ic, h, d], i) => {
    const x = 0.6 + i * 4.15;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.1, w: 3.85, h: 3.4, fill: { color: MIST }, line: { color: LINE, width: 1 }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.1, w: 3.85, h: 0.12, fill: { color: [NAVY, CYAN, GREEN][i] } });
    s.addShape(pres.shapes.OVAL, { x: x + 0.35, y: 2.55, w: 0.95, h: 0.95, fill: { color: [NAVY, CYAN, GREEN][i] } });
    s.addImage({ data: ic, x: x + 0.59, y: 2.79, w: 0.47, h: 0.47 });
    s.addText(h, { x: x + 0.35, y: 3.7, w: 3.2, h: 0.5, fontFace: HEAD, fontSize: 17, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: x + 0.35, y: 4.2, w: 3.25, h: 1.2, fontFace: BODY, fontSize: 12.5, color: SLATE, margin: 0, lineSpacingMultiple: 1.12 });
  });
  footer(s, 9);

  // ===================================================================== 10 NEXT STEPS
  s = pres.addSlide();
  s.background = { color: NAVY_DK };
  triMark(s, 10.6, 4.2, 2.4, 0.22);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 0.6, w: 2.35, h: 1.28, rectRadius: 0.1, fill: { color: PAPER } });
  s.addImage({ path: LOGO, x: 0.83, y: 0.74, w: 1.85, h: 1.85 * 0.528 });
  s.addText("NEXT STEPS", { x: 0.62, y: 2.2, w: 8, h: 0.4, fontFace: BODY, fontSize: 13, bold: true, color: CYAN, charSpacing: 3, margin: 0 });
  s.addText("Let's run it on your EBS instance", { x: 0.6, y: 2.6, w: 12, h: 0.9, fontFace: HEAD, fontSize: 34, bold: true, color: PAPER, margin: 0 });
  const steps = [
    ["1", "Discovery", "Confirm AP volumes, invoice mix and target operating unit."],
    ["2", "Proof of value", "Point the agent at a read-only EBS copy; demo a live 3-way match."],
    ["3", "Productionize", "Deploy on PAF / 26ai with AME approvals and scheduled import."],
  ];
  steps.forEach(([n, h, d], i) => {
    const x = 0.62 + i * 4.1;
    s.addShape(pres.shapes.OVAL, { x, y: 3.85, w: 0.7, h: 0.7, fill: { color: GREEN } });
    s.addText(n, { x, y: 3.85, w: 0.7, h: 0.7, align: "center", valign: "middle", fontFace: HEAD, fontSize: 22, bold: true, color: NAVY_DK, margin: 0 });
    s.addText(h, { x: x + 0.85, y: 3.9, w: 3.1, h: 0.5, fontFace: HEAD, fontSize: 17, bold: true, color: PAPER, margin: 0 });
    s.addText(d, { x, y: 4.7, w: 3.8, h: 1.1, fontFace: BODY, fontSize: 12.5, color: "CADCFC", margin: 0, lineSpacingMultiple: 1.15 });
  });
  s.addShape(pres.shapes.LINE, { x: 0.62, y: 6.2, w: 12.1, h: 0, line: { color: "27468F", width: 1 } });
  s.addText("Syntax Corporation © 2026  ·  EBS AP Invoice Automation Agent", { x: 0.62, y: 6.45, w: 12, h: 0.4, fontFace: BODY, fontSize: 12, color: "8FA6D8", margin: 0 });

  await pres.writeFile({ fileName: "EBS_AP_PAF_Exec.pptx" });
  console.log("wrote EBS_AP_PAF_Exec.pptx");
}

build();
