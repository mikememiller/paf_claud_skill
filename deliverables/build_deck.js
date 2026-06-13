/*
 * Syntax Corporation (c) 2026 — PAF Agent Factory
 * build_deck.js — wow-graphics "Deliverables Catalog" deck (pptxgenjs).
 * v1.1.0 / 2026.06.13.  Run AFTER build_diagram.js.
 *   node build_diagram.js && node build_deck.js   (needs pptxgenjs + sharp)
 *   -> PAF_Factory_Deliverables.pptx
 *   (v1.1.0 adds the two-plane monitoring/"adult supervision" slide and the
 *    Monitoring & observability TDD to the customer-facing catalog.)
 */
const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");

const NAVY = "0632A0", NAVY_DK = "041F66", GREEN = "3CC85A", CYAN = "1EB4E6",
      GOLD = "F1D488", INK = "16203A", SLATE = "5B6577", PAPER = "FFFFFF",
      MIST = "F4F7FC", LINE = "DCE4F4";
const HEAD = "Georgia", BODY = "Calibri";
const LOGO = path.join(__dirname, "..", "assets", "syntax-logo.png");
const DIAGRAM = path.join(__dirname, "assets", "deliverables_map.png");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";            // 13.333 x 7.5 in
pptx.author = "Syntax Corporation";
pptx.company = "Syntax Corporation";
const W = 13.333, H = 7.5;

// --- helpers ---------------------------------------------------------------
function triBar(slide, x, y, seg = 0.5, h = 0.12) {       // 3-color motif accent
  [NAVY, CYAN, GREEN].forEach((c, i) =>
    slide.addShape("rect", { x: x + i * seg, y, w: seg, h, fill: { color: c }, line: { type: "none" } }));
}
function header(slide, title, sub) {
  slide.background = { color: PAPER };
  slide.addShape("rect", { x: 0, y: 0, w: W, h: 1.05, fill: { color: NAVY_DK }, line: { type: "none" } });
  triBar(slide, 0.5, 0.42, 0.34, 0.1);
  slide.addText(title, { x: 1.7, y: 0.16, w: 9.6, h: 0.5, fontFace: HEAD, fontSize: 26, bold: true, color: PAPER });
  if (sub) slide.addText(sub, { x: 1.7, y: 0.62, w: 11, h: 0.32, fontFace: BODY, fontSize: 13, color: CYAN });
  slide.addImage({ path: LOGO, x: W - 1.8, y: 0.3, w: 1.25, h: 1.25 * 0.528 });
}
function footer(slide, n) {
  slide.addShape("line", { x: 0.5, y: H - 0.5, w: W - 1, h: 0, line: { color: LINE, width: 1 } });
  slide.addText("Syntax Corporation © 2026 · Confidential", { x: 0.5, y: H - 0.46, w: 8, h: 0.3, fontFace: BODY, fontSize: 9, color: SLATE });
  slide.addText(String(n), { x: W - 1, y: H - 0.46, w: 0.5, h: 0.3, fontFace: BODY, fontSize: 9, color: SLATE, align: "right" });
}
function card(slide, x, y, w, h, accent, name, fmt, desc) {
  const ct = (accent === NAVY || accent === NAVY_DK || accent === SLATE) ? PAPER : NAVY_DK;
  slide.addShape("roundRect", { x, y, w, h, rectRadius: 0.08, fill: { color: MIST }, line: { color: LINE, width: 1 } });
  slide.addShape("rect", { x, y, w, h: 0.12, fill: { color: accent }, line: { type: "none" } });
  slide.addText(name, { x: x + 0.18, y: y + 0.24, w: w - 0.36, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: INK });
  if (fmt) slide.addShape("roundRect", { x: x + 0.18, y: y + 0.72, w: 0.95, h: 0.3, rectRadius: 0.15, fill: { color: accent }, line: { type: "none" } });
  if (fmt) slide.addText(fmt, { x: x + 0.18, y: y + 0.72, w: 0.95, h: 0.3, fontFace: BODY, fontSize: 11, bold: true, color: ct, align: "center" });
  slide.addText(desc, { x: x + 0.18, y: y + 1.12, w: w - 0.36, h: h - 1.2, fontFace: BODY, fontSize: 11, color: SLATE, valign: "top" });
}

// --- 1. Title --------------------------------------------------------------
let s = pptx.addSlide();
s.background = { color: NAVY_DK };
s.addShape("rect", { x: 0, y: 0, w: W, h: H, fill: { color: NAVY_DK }, line: { type: "none" } });
s.addShape("rect", { x: 0, y: H - 1.6, w: W, h: 1.6, fill: { color: NAVY }, line: { type: "none" } });
triBar(s, 0.9, 2.2, 0.6, 0.16);
s.addText("PAF Agent Factory", { x: 0.9, y: 2.5, w: 11.5, h: 1.1, fontFace: HEAD, fontSize: 50, bold: true, color: PAPER });
s.addText("Deliverables Catalog", { x: 0.92, y: 3.7, w: 11.5, h: 0.7, fontFace: HEAD, fontSize: 28, color: CYAN });
s.addText("Everything every engagement ships — one branded, QA-gated, no-drift set.", { x: 0.92, y: 4.5, w: 11, h: 0.5, fontFace: BODY, fontSize: 16, color: MIST });
s.addImage({ path: LOGO, x: 0.9, y: H - 1.25, w: 2.2, h: 2.2 * 0.528 });
s.addText("Oracle Private Agent Factory 26.4 · domain-neutral core", { x: 7.0, y: H - 1.0, w: 5.4, h: 0.4, fontFace: BODY, fontSize: 12, color: GOLD, align: "right" });

// --- 2. Hero diagram -------------------------------------------------------
s = pptx.addSlide();
header(s, "What every engagement ships", "Define → build → package .paf → import + rebind → validate");
s.addImage({ path: DIAGRAM, x: 0.5, y: 1.25, w: 12.33, h: 12.33 * (900 / 1600) });
footer(s, 2);

// --- 3. Customer-facing catalog -------------------------------------------
s = pptx.addSlide();
header(s, "Customer-facing deliverables", "Generated from one source of truth — pricing identical everywhere");
const cust = [
  ["Sales / exec deck", ".pptx", CYAN, "The why: problem, agentic solution, architecture, ROI headline. Hero graphics."],
  ["Installation guide", ".docx", NAVY, "Prereqs, deploy, register MCP, import .paf, rebind, smoke-test."],
  ["Technical design", ".docx", NAVY, "Architecture, policy, interface contract, security, QA strategy + diagram."],
  ["Statement of Work", ".docx", NAVY, "Scope, RACI, milestones, 12/24/36-mo pricing, signature. Generic legal shell."],
  ["OCI BOM + estimator", ".xlsx", GREEN, "Sized line items (ADB/PAF, managed MCP, GenAI) + consumption flex."],
  ["ROI calculator", ".html", GOLD, "Interactive payback / NPV; 'use my data' mode. Same pricing inputs."],
  ["PAF integration pkg", ".paf", NAVY_DK, "Importable bundle (password simple4u) + MCP tool defs + canvas recipe."],
  ["Monitoring & obs TDD", ".docx", NAVY, "Two-plane supervision design (Plane A traces + Plane B availability) + CxHub data contract. Per-tenancy."],
];
const cw = 2.95, ch = 2.45, gx = 0.18, x0 = 0.5;
cust.forEach((c, i) => {
  const col = i % 4, row = Math.floor(i / 4);
  card(s, x0 + col * (cw + gx), 1.35 + row * (ch + 0.2), cw, ch, c[2], c[0], c[1], c[3]);
});
footer(s, 3);

// --- 4. Engineering & governance ------------------------------------------
s = pptx.addSlide();
header(s, "Engineering & governance deliverables", "Proof the agent is correct — not just plausible");
const eng = [
  ["The agent", "bundle", NAVY_DK, ".paf bundle(s) + Agent Spec content + clone-able flowGraph templates."],
  ["Reference engine", "code", NAVY, "Typed pipeline — reference impl + mock + test oracle."],
  ["Domain logic", "PL/SQL", CYAN, "System-of-record runs the logic (e.g. EBS XX… package) + MCP tool defs."],
  ["Test suite", "pytest", GREEN, "Hermetic + live golden + parity + packager round-trip tests."],
  ["Validation gate", "gate", GOLD, "Ground-truth scenarios + HITL + guardrails. Zero unsafe actions = PASS."],
  ["QA report", "report", SLATE, "Bug-hunt-to-zero record + honesty register."],
];
eng.forEach((c, i) => {
  const col = i % 3, row = Math.floor(i / 3);
  card(s, 0.5 + col * (3.95 + 0.18), 1.35 + row * (ch + 0.2), 3.95, ch, c[2], c[0], c[1], c[3]);
});
footer(s, 4);

// --- 5. Adult supervision — monitoring & observability ---------------------
s = pptx.addSlide();
header(s, "Adult supervision",
        "Two-plane monitoring — platform availability + agent observability, one pane");
const planes = [
  [CYAN, "Plane A · Agent observability", "The differentiator", [
    "Every run traced — step, tool call, LLM call; latency and cost attributed per run, agent and time window",
    "Tool-call success rate flags a degraded MCP server or ERP backend before users feel it",
    "Automated evaluators score groundedness and tool-call validity — quality without storing payloads",
  ]],
  [GREEN, "Plane B · Platform availability", "Table stakes", [
    "Synthetic probes replicate every PAF connection — DB 26ai, model endpoint, MCP, egress",
    "Credential-expiry calendar and config-drift watch catch silent outages before they fire",
    "SLA-backed: PAF/UI 99.5%, DB reachability 99.9%, MCP tool-call success ≥ 98%",
  ]],
];
planes.forEach((p, i) => {
  const x = 0.5 + i * (6.0 + 0.33);
  s.addShape("roundRect", { x, y: 1.35, w: 6.0, h: 3.55, rectRadius: 0.1, fill: { color: MIST }, line: { color: LINE, width: 1 } });
  s.addShape("rect", { x, y: 1.35, w: 6.0, h: 0.16, fill: { color: p[0] }, line: { type: "none" } });
  s.addText(p[1], { x: x + 0.28, y: 1.62, w: 5.4, h: 0.45, fontFace: HEAD, fontSize: 18, bold: true, color: INK });
  s.addText(p[2].toUpperCase(), { x: x + 0.28, y: 2.06, w: 5.4, h: 0.3, fontFace: BODY, fontSize: 11, bold: true, color: p[0], charSpacing: 2 });
  s.addText(p[3].map(t => ({ text: t, options: { bullet: { code: "2022", indent: 14 }, breakLine: true, paraSpaceAfter: 8 } })),
    { x: x + 0.28, y: 2.5, w: 5.45, h: 2.25, fontFace: BODY, fontSize: 12, color: SLATE, valign: "top" });
});
s.addShape("roundRect", { x: 0.5, y: 5.15, w: 12.33, h: 0.85, rectRadius: 0.08, fill: { color: NAVY_DK }, line: { type: "none" } });
s.addText([
  { text: "Ships as:  ", options: { bold: true, color: CYAN } },
  { text: "Monitoring & observability TDD (.docx)   ·   CxHub data contract (.json)   ·   Plane B probe set   ·   per-agent OAuth audit chain", options: { color: PAPER } },
], { x: 0.8, y: 5.15, w: 11.7, h: 0.85, fontFace: BODY, fontSize: 13, valign: "middle" });
s.addText("Generation is the giveaway; supervision is the product — the recurring value the foundation fee funds.",
  { x: 0.5, y: 6.15, w: 12.33, h: 0.4, fontFace: BODY, fontSize: 13, italic: true, color: NAVY });
footer(s, 5);

// --- 6. Built right --------------------------------------------------------
s = pptx.addSlide();
header(s, "Built right", "Why the deliverables are trustworthy");
const pillars = [
  ["Single source of truth", NAVY, "Customer files are generated from in-repo markdown + one pricing model. Edit the source, regenerate — deck, SOW, and ROI never disagree."],
  ["QA-gated", GREEN, "Nothing is generated until the QA gate is green: hermetic + live + parity tests pass, and the validation gate shows zero unsafe actions."],
  ["One brand, hero graphics", CYAN, "Every artifact reads from one brand source (palette, fonts, logo, tri-color motif); hero diagrams render once and are reused across deck / design / SOW."],
];
pillars.forEach((p, i) => {
  const x = 0.5 + i * (4.05 + 0.18);
  s.addShape("roundRect", { x, y: 1.5, w: 4.05, h: 4.6, rectRadius: 0.1, fill: { color: MIST }, line: { color: LINE, width: 1 } });
  s.addShape("rect", { x, y: 1.5, w: 4.05, h: 0.16, fill: { color: p[1] }, line: { type: "none" } });
  s.addText(String(i + 1), { x: x + 0.25, y: 1.85, w: 1, h: 0.9, fontFace: HEAD, fontSize: 44, bold: true, color: p[1] });
  s.addText(p[0], { x: x + 0.25, y: 2.85, w: 3.6, h: 0.7, fontFace: HEAD, fontSize: 18, bold: true, color: INK });
  s.addText(p[2], { x: x + 0.25, y: 3.6, w: 3.55, h: 2.3, fontFace: BODY, fontSize: 13, color: SLATE, valign: "top" });
});
footer(s, 6);

// --- 7. Where created ------------------------------------------------------
s = pptx.addSlide();
header(s, "Where deliverables are created", "Reusable catalog + per-engagement artifacts");
s.addShape("roundRect", { x: 0.5, y: 1.5, w: 6.0, h: 4.4, rectRadius: 0.1, fill: { color: MIST }, line: { color: LINE, width: 1 } });
s.addShape("rect", { x: 0.5, y: 1.5, w: 6.0, h: 0.16, fill: { color: NAVY }, line: { type: "none" } });
s.addText("The factory (reusable)", { x: 0.75, y: 1.8, w: 5.5, h: 0.5, fontFace: HEAD, fontSize: 18, bold: true, color: INK });
s.addText([
  { text: "paf_claud_skill", options: { bold: true, color: NAVY, fontSize: 14, breakLine: true } },
  { text: "references/deliverables.md — the recipe", options: { fontSize: 12, color: SLATE, bullet: true, breakLine: true } },
  { text: "deliverables/ — this catalog doc + showcase deck", options: { fontSize: 12, color: SLATE, bullet: true, breakLine: true } },
  { text: "templates/deliverables/ — the generators", options: { fontSize: 12, color: SLATE, bullet: true, breakLine: true } },
  { text: "core/ — the importable .paf + validation gate", options: { fontSize: 12, color: SLATE, bullet: true } },
], { x: 0.75, y: 2.5, w: 5.5, h: 3.2, fontFace: BODY, valign: "top" });
s.addShape("roundRect", { x: 6.8, y: 1.5, w: 6.0, h: 4.4, rectRadius: 0.1, fill: { color: MIST }, line: { color: LINE, width: 1 } });
s.addShape("rect", { x: 6.8, y: 1.5, w: 6.0, h: 0.16, fill: { color: GREEN }, line: { type: "none" } });
s.addText("The engagement (the actual files)", { x: 7.05, y: 1.8, w: 5.5, h: 0.5, fontFace: HEAD, fontSize: 18, bold: true, color: INK });
s.addText([
  { text: "the agent's own git repo", options: { bold: true, color: NAVY, fontSize: 14, breakLine: true } },
  { text: "deliverables/ — the .docx / .xlsx / .html / .pptx", options: { fontSize: 12, color: SLATE, bullet: true, breakLine: true } },
  { text: "slides/ — the deck + hero-diagram generators", options: { fontSize: 12, color: SLATE, bullet: true, breakLine: true } },
  { text: "e.g. EBS-Contract-Renewal-PAF (the EBS AP agent)", options: { fontSize: 12, color: SLATE, italic: true, bullet: true } },
], { x: 7.05, y: 2.5, w: 5.5, h: 3.2, fontFace: BODY, valign: "top" });
footer(s, 7);

// --- 8. Closing ------------------------------------------------------------
s = pptx.addSlide();
s.background = { color: NAVY_DK };
triBar(s, 0.9, 2.4, 0.6, 0.16);
s.addText("One factory. Every deliverable.", { x: 0.9, y: 2.75, w: 11.5, h: 1.0, fontFace: HEAD, fontSize: 40, bold: true, color: PAPER });
s.addText("Domain-neutral core · EBS bundled · branded, QA-gated, reproducible.", { x: 0.92, y: 3.9, w: 11, h: 0.5, fontFace: BODY, fontSize: 16, color: CYAN });
s.addImage({ path: LOGO, x: 0.9, y: 5.4, w: 2.2, h: 2.2 * 0.528 });
s.addText("Syntax Corporation © 2026 · Confidential", { x: 7, y: 6.6, w: 5.4, h: 0.4, fontFace: BODY, fontSize: 12, color: SLATE, align: "right" });

pptx.writeFile({ fileName: path.join(__dirname, "PAF_Factory_Deliverables.pptx") })
  .then(f => console.log("wrote", f))
  .catch(e => { console.error(e); process.exit(1); });
