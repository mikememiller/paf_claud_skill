/*
 * Syntax Corporation (c) 2026 — PAF Agent Factory
 * build_diagrams.js — the REQUIRED hero graphics (SVG->PNG via sharp), SPEC-DRIVEN.
 *   --kind architecture  (default) : spec.architecture.{title,subhead,tiers[],flow,flow_note}
 *   --kind flow                    : spec.flow_diagram.{title,subhead,steps[],branch}
 * v2.1.0 / 2026.06.08.
 *   node build_diagrams.js --kind architecture --spec build/spec.json --out build/architecture.png
 *   node build_diagrams.js --kind flow         --spec build/spec.json --out build/flow.png
 *   (needs sharp; reuse an existing install via NODE_PATH if not local)
 */
const sharp = require("sharp");
const fs = require("fs");
const path = require("path");

const NAVY = "#0632A0", NAVY_DK = "#041F66", GREEN = "#3CC85A", CYAN = "#1EB4E6",
      GOLD = "#F1D488", INK = "#16203A", SLATE = "#5B6577", PAPER = "#FFFFFF",
      MIST = "#F4F7FC", LINE = "#DCE4F4";
const ACCENT = { navy: NAVY, cyan: CYAN, green: GREEN, gold: GOLD };
const CYCLE = [NAVY, CYAN, GREEN, NAVY, CYAN, GREEN];
const W = 1600, H = 900;

function arg(name, def) { const i = process.argv.indexOf("--" + name); return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : def; }
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const tri = (x, y, s) => `
  <polygon points="${x},${y + s} ${x + s},${y + s} ${x + s / 2},${y}" fill="none" stroke="${GREEN}" stroke-width="3"/>
  <line x1="${x}" y1="${y + s}" x2="${x + s / 2}" y2="${y}" stroke="${PAPER}" stroke-width="3"/>
  <line x1="${x + s}" y1="${y + s}" x2="${x + s / 2}" y2="${y}" stroke="${CYAN}" stroke-width="3"/>`;
const txt = (x, y, sz, c, t, w = "normal", anc = "middle", f = "Calibri") =>
  `<text x="${x}" y="${y}" font-family="${f}" font-size="${sz}" font-weight="${w}" fill="${c}" text-anchor="${anc}">${esc(t)}</text>`;
const rrect = (x, y, w, h, fill, stroke, rx = 12) =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke || "none"}" stroke-width="2"/>`;
const arrowR = (x1, y, x2) =>
  `<line x1="${x1}" y1="${y}" x2="${x2 - 12}" y2="${y}" stroke="${SLATE}" stroke-width="4"/>
   <polygon points="${x2 - 12},${y - 8} ${x2},${y} ${x2 - 12},${y + 8}" fill="${SLATE}"/>`;
const arrowD = (x, y1, y2) =>
  `<line x1="${x}" y1="${y1}" x2="${x}" y2="${y2 - 12}" stroke="${SLATE}" stroke-width="4"/>
   <polygon points="${x - 8},${y2 - 12} ${x},${y2} ${x + 8},${y2 - 12}" fill="${SLATE}"/>`;
function wrap(text, max) {
  const words = String(text).split(/\s+/); const lines = []; let cur = "";
  for (const w of words) { if ((cur + " " + w).trim().length > max) { if (cur) lines.push(cur); cur = w; } else cur = (cur + " " + w).trim(); }
  if (cur) lines.push(cur); return lines;
}
const multiline = (x, y, sz, c, text, max, lh, anc = "middle") =>
  wrap(text, max).map((ln, i) => txt(x, y + i * lh, sz, c, ln, "normal", anc)).join("");

function head(title, subhead) {
  return `<rect width="${W}" height="130" fill="${NAVY_DK}"/>${tri(60, 38, 54)}
    ${txt(150, 64, 32, PAPER, title || "Diagram", "bold", "start", "Georgia")}
    ${subhead ? txt(150, 100, 19, CYAN, subhead, "normal", "start") : ""}`;
}
function foot(spec, meta) {
  return `<rect x="0" y="${H - 44}" width="${W}" height="44" fill="${MIST}"/>
    ${txt(60, H - 16, 15, SLATE, (spec.branding && spec.branding.footer) || "Syntax Corporation © 2026 · Confidential", "normal", "start")}
    ${txt(W - 60, H - 16, 15, SLATE, (meta && meta.agent_name) || "", "normal", "end")}`;
}

function renderArchitecture(spec) {
  const a = spec.architecture, meta = spec.meta || {};
  if (!a || !Array.isArray(a.tiers) || !a.tiers.length) { console.error("spec.architecture.tiers required — aborting."); process.exit(2); }
  const N = a.tiers.length, M = 70, GUT = 56, top = 210, boxH = 380;
  const bw = Math.floor((W - 2 * M - (N - 1) * GUT) / N);
  let cols = "";
  a.tiers.forEach((t, i) => {
    const x = M + i * (bw + GUT), ac = ACCENT[t.accent] || NAVY, ht = ac === NAVY ? PAPER : NAVY_DK;
    cols += rrect(x, top, bw, boxH, MIST, LINE);
    cols += `<rect x="${x}" y="${top}" width="${bw}" height="58" rx="12" fill="${ac}"/>`;
    cols += txt(x + bw / 2, top + 37, 21, ht, t.title, "bold", "middle", "Georgia");
    if (t.subtitle) cols += txt(x + bw / 2, top + 86, 16, SLATE, t.subtitle);
    (t.items || []).forEach((it, j) => { const iy = top + 112 + j * 56;
      cols += rrect(x + 26, iy, bw - 52, 44, PAPER, LINE, 8);
      cols += txt(x + bw / 2, iy + 28, 15, INK, it); });
    if (i < N - 1) cols += arrowR(x + bw, top + boxH / 2, x + bw + GUT);
  });
  const fy = top + boxH + 50;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <rect width="${W}" height="${H}" fill="${PAPER}"/>${head(a.title || meta.headline, a.subhead || meta.subhead)}
    ${cols}
    <rect x="${M}" y="${fy}" width="${W - 2 * M}" height="118" rx="14" fill="${NAVY_DK}"/>
    ${txt(M + 30, fy + 40, 20, GREEN, "Flow", "bold", "start", "Georgia")}
    ${txt(M + 30, fy + 76, 18, PAPER, a.flow || "", "normal", "start")}
    ${a.flow_note ? txt(M + 30, fy + 102, 15, CYAN, a.flow_note, "normal", "start") : ""}
    ${foot(spec, meta)}</svg>`;
}

function renderFlow(spec) {
  const f = spec.flow_diagram, meta = spec.meta || {};
  if (!f || !Array.isArray(f.steps) || !f.steps.length) { console.error("spec.flow_diagram.steps required — aborting."); process.exit(2); }
  const N = f.steps.length, M = 60, GUT = 26, top = 250, cardH = 250;
  const cw = Math.floor((W - 2 * M - (N - 1) * GUT) / N);
  let cards = "";
  f.steps.forEach((st, i) => {
    const x = M + i * (cw + GUT), ac = CYCLE[i % CYCLE.length];
    cards += rrect(x, top, cw, cardH, MIST, LINE);
    cards += `<rect x="${x}" y="${top}" width="${cw}" height="10" rx="5" fill="${ac}"/>`;
    cards += `<circle cx="${x + 34}" cy="${top + 50}" r="22" fill="${ac}"/>`;
    cards += txt(x + 34, top + 58, 22, PAPER, i + 1, "bold");
    cards += txt(x + cw / 2 + 18, top + 58, 19, INK, st.step, "bold", "middle", "Georgia");
    cards += multiline(x + cw / 2, top + 104, 13, SLATE, st.detail, Math.floor(cw / 7), 20);
    if (i < N - 1) cards += arrowR(x + cw, top + cardH / 2, x + cw + GUT);
  });
  // branch from the QA-gate step (or 2nd-to-last) down to a full-width callout
  const qa = Math.max(0, f.steps.findIndex(s => /qa/i.test(s.step)));
  const qx = M + (qa < 0 ? N - 2 : qa) * (cw + GUT) + cw / 2;
  const by = top + cardH + 70, bh = 120;
  let branch = "";
  if (f.branch) {
    branch += arrowD(qx, top + cardH, by);
    branch += rrect(M, by, W - 2 * M, bh, NAVY_DK, null, 14);
    branch += `<rect x="${M}" y="${by}" width="10" height="${bh}" rx="5" fill="${GOLD}"/>`;
    branch += txt(M + 36, by + 46, 20, GOLD, f.branch.label, "bold", "start", "Georgia");
    branch += txt(M + 36, by + 84, 17, PAPER, f.branch.detail, "normal", "start");
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <rect width="${W}" height="${H}" fill="${PAPER}"/>${head(f.title || "Functional flow", f.subhead || "")}
    ${cards}${branch}${foot(spec, meta)}</svg>`;
}

const kind = arg("kind", "architecture");
const spec = JSON.parse(fs.readFileSync(arg("spec", "build/spec.json"), "utf8"));
const out = arg("out", kind === "flow" ? "build/flow.png" : "build/architecture.png");
const svg = kind === "flow" ? renderFlow(spec) : renderArchitecture(spec);
fs.mkdirSync(path.dirname(out), { recursive: true });
sharp(Buffer.from(svg)).png().toFile(out)
  .then(() => console.log("wrote", out))
  .catch(e => { console.error(e); process.exit(1); });
