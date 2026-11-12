# NVF Shirt Studio

A single-page shirt designer for New Vision Fellowship's (Madison, NC) Christmas Stroll volunteer shirts. It shows each design on a Gildan 18000 crewneck sweatshirt or a Gildan 64000 Softstyle tee, drawn to scale, with shirt colors, PMS inks, recommended color combos, print placement specs, and a "Download print files" zip of vector SVGs.

The artwork is drawn and revised in a **Claude Design** canvas (claude.ai). This repo is where those designs become the shareable Studio page. Claude Design is the drawing board; this repo is the build.

## Layout

```
src/template.html     The whole page: CSS, UI rendering, garment drawings, placement math, zip export.
                      Placeholders /*CATALOG*/, /*ART*/, /*LOGO*/ are filled by the build.
src/catalog.js        SHIRTS, INKS and the design list D (titles, descriptions, sides, recommended colors).
art/<key>.svg         One file per design, named by its catalog key. Two-ink art (see "Art files").
art/lantern1.svg      Alternate art for a design's one-sided version (catalog field art1).
logos/stacked.svg     NVF logo, stacked (used on the non-design side of two-sided shirts).
logos/horizontal.svg  NVF logo, flat one-line version.
tools/build.py        Builds dist/index.html (self-contained, ~600 KB).
tools/add_art.py      Converts an export (SVG or PNG) into art/<key>.svg. Run with -h for options.
exports/              Drop raw exports from Claude Design here (git-ignored).
reference/claude-design/  Snapshot of the Claude Design canvas source (.dc.html). Reference only;
                      it needs Claude Design's runtime to render, so it is not part of the build.
dist/index.html       The built page. Open it directly in a browser, or host it anywhere static.
```

Build: `python3 tools/build.py`. There is no other build step and no npm.

## Art files

- Each art SVG has a `viewBox` cropped to the artwork and uses exactly two fills:
  `style="fill: var(--i1, #fallback)"` (ink 1) and `style="fill: var(--i2, #fallback)"` (ink 2).
  The fallback hex is only for previewing the file on its own. The page swaps in the real inks.
- `var(--bg, none)` may appear; it means "shirt color" (a knockout) and is painted as the shirt color in mockups and as nothing in print files.
- Areas with no ink are simply empty, so the shirt shows through. No white "fake knockouts".
- The design's printed height comes from the viewBox: height/width x 12" (adult) or x 9" (youth).
  It must stay within the 12" x 14" max print area on adults (10" x 12" youth), so keep height/width at or below about 1.17.
- No live text, fonts, images, filters or gradients in art files. Everything is outlines, so the page and print files need no fonts and have no font-licensing issues.

## Adding or updating a design from Claude Design

1. In Claude Design, get the art board out as a file and save it into `exports/`:
   - Best: an **SVG** whose shapes use exactly two colors (one per ink). Art you drew elsewhere and pasted into Claude Design is usually already this.
   - Otherwise: a **large PNG** (3000 px wide or more) on a transparent background, or on one solid background color you can name as a knockout.
   - Tip: in Claude Design, set the board's two inks to two very different colors before exporting (for example pure red and pure blue) so tracing can tell them apart cleanly.
2. Convert it:
   ```
   python3 tools/add_art.py <key> exports/<file> --ink1 "<hex used for ink 1>" --ink2 "<hex used for ink 2>" [--knockout "<background hex>"]
   ```
   SVGs that qualify are converted losslessly (vector mode). Anything with live text, textures or a raster is traced (trace mode, uses potrace), which also turns text into outlines.
3. New design? Add an entry to `D` in `src/catalog.js` (copy a similar one). Update the description `b` if the art changed.
4. `python3 tools/build.py`, open `dist/index.html`, and check the design on both garments, adult and youth, with "Max print area" on.

A one-sided design that carries the flat logo beneath the art (like design 06's `lantern1.svg`) is its own art file: compose `art/<key>.svg` and `logos/horizontal.svg` into a new SVG, with the logo at 60% of the art width, centered, about 3.6% of the art width below it, then set `art1: '<newkey>'` on the design.

## Placement rules (in src/template.html, compute())

- Drawings are to scale. Sweatshirt: adult L 24" x 29", 880 drawing units shoulder to hem. Tee: adult L 22" x 30" at 26 units per inch. Youth uses the same drawing with a larger units-per-inch.
- Design width: 12" adult, 9" youth. Max print area: 12" x 14" adult, 10" x 12" youth.
- Top edge below the collar seam: sweatshirt 4" front / 3.5" back (youth 3" / 2.5"); tees sit 1" higher on adult, 0.5" higher on youth.
- Logo on the non-design side: large = same width as the design; small = left chest 4" wide (3.5" youth) or upper back.
- Shirt colors are limited to colors sold in both adult and youth sizes of both garments.

## Conventions

- Keep the page a single self-contained HTML file. Only the UI fonts (Archivo, Source Serif 4) load from Google Fonts; nothing in the artwork depends on them.
- Ink colors are Pantone (PMS) coated matches; NVF brand colors are mapped to their nearest PMS in `INKS`.
- Recommended combos (`P`) are the pastor's picks. Change them only when asked; the first one is the design's default.
- The church is New Vision Fellowship, Madison NC. Designs carry Scripture references; keep them exactly as written in the art.
