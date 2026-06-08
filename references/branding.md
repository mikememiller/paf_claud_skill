<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# Syntax branding — applies to EVERY document

One source of truth: `assets/brand.json` drives all generators (deck, all docx,
xlsx, ROI html). No artifact ships unbranded.

## Palette (from the Syntax logo)
- Navy `#0632A0` (primary), Green `#3CC85A` (accent), Cyan `#1EB4E6`,
  Gold `#F1D488` (sparing), ink `#16203A`, slate `#5B6577`, paper `#FFFFFF`,
  mist `#F4F7FC`, line `#DCE4F4`. Dark title/section = `#041F66`.
- Motif: the **tri-color triangle** (navy/cyan/green) echoing the logo mark.
- Logo: `assets/syntax-logo.png` (place on a white chip when on dark slides;
  native ratio ≈ 0.528 — don't squash).

## Typography
Header **Georgia** (bold), body **Calibri**. Title 30–46pt, section 16–24pt,
body 11–15pt, captions 9–11pt. Left-align body; center only titles.

## Required on every artifact
Syntax cover/letterhead, logo, the triangle motif, footer
`Syntax Corporation © 2026 · Confidential`. Dark title/closing, light content.

## File-header banner (every code/script file)
```
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
 Project : <name>   Module : <file>
 Version : x.y.z   Build : YYYY.MM.DD   Date : YYYY-MM-DD
================================================================================
```
See `templates/file_header.txt`. QA fails the build if any file lacks it.

## Anti-AI-slop rules
No accent underlines beneath titles; no decorative full-width colored bars; white
(not cream) default background; never ship text that overflows its shape.
