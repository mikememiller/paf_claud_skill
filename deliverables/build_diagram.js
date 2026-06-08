/*
 * Syntax Corporation (c) 2026 — PAF Agent Factory
 * build_diagram.js — hero "deliverables map" (SVG -> PNG via sharp) for the
 * deliverables showcase deck. v1.0.0 / 2026.06.08
 * Run:  node build_diagram.js   (needs sharp; NODE_PATH may point at a slides/ install)
 */
const sharp = require("sharp");
const fs = require("fs");
const path = require("path");

const NAVY = "#0632A0", NAVY_DK = "#041F66", GREEN = "#3CC85A", CYAN = "#1EB4E6",
      GOLD = "#F1D488", INK = "#16203A", SLATE = "#5B6577", PAPER = "#FFFFFF",
      MIST = "#F4F7FC", LINE = "#DCE4F4";
const W = 1600, H = 900;

const tri = (x, y, s) => `
  <polygon points="${x},${y+s} ${x+s},${y+s} ${x+s/2},${y}" fill="none" stroke="${GREEN}" stroke-width="3"/>
  <line x1="${x}" y1="${y+s}" x2="${x+s/2}" y2="${y}" stroke="${PAPER}" stroke-width="3"/>
  <line x1="${x+s}" y1="${y+s}" x2="${x+s/2}" y2="${y}" stroke="${CYAN}" stroke-width="3"/>`;
const rect = (x, y, w, h, fill, stroke, rx=14) =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke||'none'}" stroke-width="2"/>`;
const txt = (x, y, s, c, t, w="normal", anc="middle", f="Calibri") =>
  `<text x="${x}" y="${y}" font-family="${f}" font-size="${s}" font-weight="${w}" fill="${c}" text-anchor="${anc}">${t}</text>`;
const arrow = (x1, y, x2) =>
  `<line x1="${x1}" y1="${y}" x2="${x2-12}" y2="${y}" stroke="${SLATE}" stroke-width="4"/>
   <polygon points="${x2-12},${y-7} ${x2},${y} ${x2-12},${y+7}" fill="${SLATE}"/>`;

// pipeline step chip
function step(x, n, label, accent) {
  const w = 250, y = 168, h = 84;
  return `${rect(x, y, w, h, PAPER, LINE)}
    <rect x="${x}" y="${y}" width="8" height="${h}" rx="4" fill="${accent}"/>
    ${txt(x+w/2+4, y+34, 16, accent, n, "bold")}
    ${txt(x+w/2+4, y+62, 18, INK, label, "bold")}`;
}
// deliverable tile
function tile(x, y, name, fmt, accent, sub) {
  const w = 350, h = 168;
  const ct = (accent === NAVY || accent === NAVY_DK || accent === SLATE) ? PAPER : NAVY_DK;
  return `${rect(x, y, w, h, MIST, LINE)}
    <rect x="${x}" y="${y}" width="${w}" height="10" rx="5" fill="${accent}"/>
    ${txt(x+24, y+52, 21, INK, name, "bold", "start", "Georgia")}
    <rect x="${x+24}" y="${y+66}" width="${(fmt.length*11)+24}" height="30" rx="15" fill="${accent}"/>
    ${txt(x+24+((fmt.length*11)+24)/2, y+86, 15, ct, fmt, "bold")}
    ${txt(x+24, y+128, 15, SLATE, sub, "normal", "start")}`;
}

const steps = [
  ["1", "Define", NAVY],
  ["2", "Build flowGraph", CYAN],
  ["3", "Package .paf", GREEN],
  ["4", "Import + Rebind", NAVY],
  ["5", "Validate", GOLD],
];
let pipeline = "";
let x = 70;
steps.forEach((s, i) => {
  pipeline += step(x, s[0], s[1], s[2]);
  if (i < steps.length - 1) pipeline += arrow(x + 250, 210, x + 290);
  x += 290;
});

const tiles = [
  ["Sales / exec deck", ".pptx", CYAN, "Hero graphics · the why + ROI"],
  ["Installation guide", ".docx", NAVY, "Deploy · import · rebind · smoke-test"],
  ["Technical design", ".docx", NAVY, "Architecture · policy · security · QA"],
  ["Statement of Work", ".docx", NAVY, "RACI · 12/24/36 pricing · signature"],
  ["OCI BOM + estimator", ".xlsx", GREEN, "Sized line items · consumption flex"],
  ["ROI calculator", ".html", GOLD, "Sliders · payback · NPV · use-my-data"],
  ["PAF integration pkg", ".paf", NAVY_DK, "Importable bundle + MCP tool defs"],
  ["Engineering + QA", "code", SLATE, "Tests · validation gate · QA report"],
];
let grid = "";
const cols = 4, tw = 350, th = 168, gx = 22, gy = 26, gx0 = 70, gy0 = 470;
tiles.forEach((t, i) => {
  const cx = gx0 + (i % cols) * (tw + gx);
  const cy = gy0 + Math.floor(i / cols) * (th + gy);
  grid += tile(cx, cy, t[0], t[1], t[2], t[3]);
});

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect width="${W}" height="${H}" fill="${PAPER}"/>
  <rect width="${W}" height="120" fill="${NAVY_DK}"/>
  ${tri(60, 34, 52)}
  ${txt(150, 58, 34, PAPER, "PAF Agent Factory — What Every Engagement Ships", "bold", "start", "Georgia")}
  ${txt(150, 95, 20, CYAN, "Define → build → package .paf → import + rebind → validate  ·  one branded, QA-gated deliverable set", "normal", "start")}
  ${pipeline}
  ${txt(W/2, 318, 22, NAVY, "↓  ships  ↓", "bold")}
  ${txt(150, 360, 22, INK, "Customer-facing", "bold", "start", "Georgia")}
  ${txt(150, 386, 16, SLATE, "generated from one source of truth · pricing identical everywhere · no drift", "normal", "start")}
  ${grid}
  <rect x="0" y="${H-46}" width="${W}" height="46" fill="${MIST}"/>
  ${txt(70, H-16, 16, SLATE, "Syntax Corporation © 2026 · Confidential", "normal", "start")}
  ${txt(W-70, H-16, 16, SLATE, "Domain-neutral core · EBS is the bundled worked example", "normal", "end")}
</svg>`;

const outDir = path.join(__dirname, "assets");
fs.mkdirSync(outDir, { recursive: true });
const out = path.join(outDir, "deliverables_map.png");
sharp(Buffer.from(svg)).png().toFile(out)
  .then(() => console.log("wrote", out))
  .catch(e => { console.error(e); process.exit(1); });
