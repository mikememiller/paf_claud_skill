/*
 * Syntax Corporation (c) 2026 — PAF Agent Factory
 * build_diagrams.js — the REQUIRED hero architecture/flow diagram (SVG->PNG via
 * sharp), SPEC-DRIVEN. Renders spec.architecture.{title,subhead,tiers[],flow,
 * flow_note} as N tiered columns + a flow strip. Brand from assets/brand.json
 * convention (palette below). v2.0.0 / 2026.06.08.
 *   node build_diagrams.js --spec build/spec.json --out build/architecture.png
 *   (needs sharp; reuse an existing install via NODE_PATH if not local)
 */
const sharp = require("sharp");
const fs = require("fs");
const path = require("path");

const NAVY = "#0632A0", NAVY_DK = "#041F66", GREEN = "#3CC85A", CYAN = "#1EB4E6",
      GOLD = "#F1D488", INK = "#16203A", SLATE = "#5B6577", PAPER = "#FFFFFF",
      MIST = "#F4F7FC", LINE = "#DCE4F4";
const ACCENT = { navy: NAVY, cyan: CYAN, green: GREEN, gold: GOLD };
const W = 1600, H = 900;

function arg(name, def) {
  const i = process.argv.indexOf("--" + name);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : def;
}
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const tri = (x, y, s) => `
  <polygon points="${x},${y + s} ${x + s},${y + s} ${x + s / 2},${y}" fill="none" stroke="${GREEN}" stroke-width="3"/>
  <line x1="${x}" y1="${y + s}" x2="${x + s / 2}" y2="${y}" stroke="${PAPER}" stroke-width="3"/>
  <line x1="${x + s}" y1="${y + s}" x2="${x + s / 2}" y2="${y}" stroke="${CYAN}" stroke-width="3"/>`;
const txt = (x, y, sz, c, t, w = "normal", anc = "middle", f = "Calibri") =>
  `<text x="${x}" y="${y}" font-family="${f}" font-size="${sz}" font-weight="${w}" fill="${c}" text-anchor="${anc}">${esc(t)}</text>`;
const rrect = (x, y, w, h, fill, stroke, rx = 12) =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke || "none"}" stroke-width="2"/>`;
const arrow = (x1, y, x2) =>
  `<line x1="${x1}" y1="${y}" x2="${x2 - 12}" y2="${y}" stroke="${SLATE}" stroke-width="4"/>
   <polygon points="${x2 - 12},${y - 8} ${x2},${y} ${x2 - 12},${y + 8}" fill="${SLATE}"/>`;

const specPath = arg("spec", "build/spec.json");
const out = arg("out", "build/architecture.png");
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
const a = spec.architecture;
if (!a || !Array.isArray(a.tiers) || !a.tiers.length) {
  console.error("spec.architecture.tiers is required (none found) — aborting."); process.exit(2);
}
const meta = spec.meta || {};

// --- layout the N tiers ------------------------------------------------------
const N = a.tiers.length;
const M = 70, GUT = 56, top = 210, boxH = 380;
const bw = Math.floor((W - 2 * M - (N - 1) * GUT) / N);
let cols = "";
a.tiers.forEach((t, i) => {
  const x = M + i * (bw + GUT);
  const ac = ACCENT[t.accent] || NAVY;
  const headTxt = ac === NAVY ? PAPER : NAVY_DK;
  cols += rrect(x, top, bw, boxH, MIST, LINE);
  cols += `<rect x="${x}" y="${top}" width="${bw}" height="58" rx="12" fill="${ac}"/>`;
  cols += txt(x + bw / 2, top + 37, 21, headTxt, t.title, "bold", "middle", "Georgia");
  if (t.subtitle) cols += txt(x + bw / 2, top + 86, 16, SLATE, t.subtitle);
  (t.items || []).forEach((it, j) => {
    const iy = top + 112 + j * 56;
    cols += rrect(x + 26, iy, bw - 52, 44, PAPER, LINE, 8);
    cols += txt(x + bw / 2, iy + 28, 15, INK, it);
  });
  if (i < N - 1) cols += arrow(x + bw, top + boxH / 2, x + bw + GUT);
});

const flowY = top + boxH + 50;
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect width="${W}" height="${H}" fill="${PAPER}"/>
  <rect width="${W}" height="130" fill="${NAVY_DK}"/>
  ${tri(60, 38, 54)}
  ${txt(150, 64, 32, PAPER, a.title || meta.headline || "Solution Architecture", "bold", "start", "Georgia")}
  ${txt(150, 100, 19, CYAN, a.subhead || meta.subhead || "", "normal", "start")}
  ${cols}
  <rect x="${M}" y="${flowY}" width="${W - 2 * M}" height="118" rx="14" fill="${NAVY_DK}"/>
  ${txt(M + 30, flowY + 40, 20, GREEN, "Flow", "bold", "start", "Georgia")}
  ${txt(M + 30, flowY + 76, 18, PAPER, a.flow || "", "normal", "start")}
  ${a.flow_note ? txt(M + 30, flowY + 102, 15, CYAN, a.flow_note, "normal", "start") : ""}
  <rect x="0" y="${H - 44}" width="${W}" height="44" fill="${MIST}"/>
  ${txt(M, H - 16, 15, SLATE, (spec.branding && spec.branding.footer) || "Syntax Corporation © 2026 · Confidential", "normal", "start")}
  ${txt(W - M, H - 16, 15, SLATE, meta.agent_name || "", "normal", "end")}
</svg>`;

fs.mkdirSync(path.dirname(out), { recursive: true });
sharp(Buffer.from(svg)).png().toFile(out)
  .then(() => console.log("wrote", out))
  .catch(e => { console.error(e); process.exit(1); });
