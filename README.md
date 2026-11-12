# NVF Shirt Studio

Shirt designer for the New Vision Fellowship Christmas Stroll volunteer shirts.

- **See it:** open `dist/index.html` in any browser.
- **Share it:** upload `dist/index.html` to any static host (GitHub Pages, Netlify, the church website). It is one file.
- **Change it:** open this folder in Claude Code and ask. `CLAUDE.md` explains how everything fits together.

## Setup (once, for adding new artwork)

```
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```
Plus potrace: `brew install potrace` (Mac), `sudo apt install potrace` (Linux) or `choco install potrace` (Windows).

## Bringing in a design from Claude Design

1. Export the art board from Claude Design (SVG if you can, otherwise a large PNG) into `exports/`.
2. `python3 tools/add_art.py <key> exports/<file> --ink1 "#hex" --ink2 "#hex"`
3. Add or update the design in `src/catalog.js`.
4. `python3 tools/build.py`, then open `dist/index.html`.

Or just tell Claude Code: "I exported a new design to exports/advent.png. Inks are white and NVF bright green. Add it as design 12."
