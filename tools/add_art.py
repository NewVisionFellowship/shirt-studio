#!/usr/bin/env python3
"""Turn an artwork export into a recolorable two-ink art file: art/<key>.svg

Every art file uses two ink slots, filled with var(--i1, ...) and var(--i2, ...),
so the Studio can recolor it for any shirt and ink combo.

Two ways in:

  vector  An SVG whose shapes use exactly the two ink colors you name (no <text>,
          no images). The shapes are kept as-is; only the colors are swapped for
          the ink slots. Best quality. This is the mode for SVGs you drew yourself
          or pasted into Claude Design.

  trace   Anything else: a PNG export from Claude Design, or an SVG that still has
          live text, filters or textures. The art is rendered large, every pixel is
          sorted to the nearest ink (or to "no ink"), and each ink is traced to
          smooth vector outlines with potrace. Text ends up as outlines, so no
          fonts are needed afterwards.

Examples
  python3 tools/add_art.py advent exports/advent.svg --ink1 "#ffffff" --ink2 "#78be20"
  python3 tools/add_art.py advent exports/advent.png --ink1 "#ffffff" --ink2 "#78be20" --knockout "#222a3d"
  python3 tools/add_art.py advent exports/advent.png --ink1 "#ffffff" --one-color

Options
  --ink1 / --ink2   The colors the export actually uses for ink 1 and ink 2.
  --knockout HEX    A color that means "no ink" (repeatable), e.g. the shirt color
                    if the export has a solid shirt-colored background or uses the
                    shirt color for cut-outs. Transparent pixels are always no ink.
  --one-color       The art has a single ink.
  --mode            auto (default: vector when possible, else trace) | vector | trace
  --width           Trace resolution in pixels across (default 3000).
  --crop            Trim empty margins (default on; --no-crop to keep the canvas).

Needs: Python 3.9+, pillow, numpy, playwright (python -m playwright install chromium),
and potrace on the PATH (brew install potrace / apt install potrace / choco install potrace).
"""
import argparse, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

NAMED = {'white': '#ffffff', 'black': '#000000', 'red': '#ff0000', 'blue': '#0000ff', 'green': '#008000',
         'yellow': '#ffff00', 'navy': '#000080', 'gray': '#808080', 'grey': '#808080', 'gold': '#ffd700'}


def norm(c):
    c = c.strip().lower()
    if c in NAMED:
        return NAMED[c]
    m = re.fullmatch(r'#([0-9a-f]{3})', c)
    if m:
        return '#' + ''.join(ch * 2 for ch in m.group(1))
    if re.fullmatch(r'#[0-9a-f]{6}', c):
        return c
    m = re.fullmatch(r'rgba?\(\s*([\d.]+)%?\s*,\s*([\d.]+)%?\s*,\s*([\d.]+)%?.*\)', c)
    if m:
        vals = [float(x) for x in m.groups()]
        if '%' in c:
            vals = [v * 2.55 for v in vals]
        return '#' + ''.join(f'{round(v):02x}' for v in vals)
    return None


def hex_rgb(h):
    h = norm(h)
    if not h:
        sys.exit(f'Not a color: {h}')
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


COLOR_RE = re.compile(r'(#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\([^)]*\)|\b(?:' + '|'.join(NAMED) + r')\b)')


def vector_mode(src, inks):
    s = src.read_text(encoding='utf-8')
    if re.search(r'<(text|image|foreignObject)\b', s):
        raise ValueError('has <text>, <image> or <foreignObject>; use trace mode')
    if re.search(r'<filter\b|<mask\b|<pattern\b|Gradient\b', s):
        raise ValueError('uses filters, masks, patterns or gradients; use trace mode')
    vb = re.search(r'<svg[^>]*\sviewBox="([^"]+)"', s)
    if not vb:
        raise ValueError('the <svg> has no viewBox')
    inner = re.sub(r'^.*?<svg[^>]*>', '', s, count=1, flags=re.S)
    inner = re.sub(r'</svg>\s*$', '', inner.strip())
    inner = re.sub(r'<(title|desc|metadata)\b.*?</\1>', '', inner, flags=re.S)
    want = {norm(v): slot for slot, v in inks.items()}
    leftovers = set()

    def swap(m):
        n = norm(m.group(0))
        if n in want:
            slot = want[n]
            return f'var(--{slot}, {n})'
        leftovers.add(m.group(0))
        return m.group(0)

    # swap colors only inside fill/stroke attributes and style declarations
    def fix_attr(m):
        return m.group(1) + COLOR_RE.sub(swap, m.group(2)) + m.group(3)
    inner = re.sub(r'((?:fill|stroke|stop-color)=")([^"]*)(")', fix_attr, inner)
    inner = re.sub(r'(style=")([^"]*)(")', fix_attr, inner)
    inner = re.sub(r'(<style[^>]*>)(.*?)(</style>)', fix_attr, inner, flags=re.S)
    # attribute fills cannot use var(): move them into style
    inner = re.sub(r'\s(fill|stroke)="(var\([^"]+\))"', r' style="\1: \2"', inner)
    inner = re.sub(r'style="([^"]*)" style="([^"]*)"', r'style="\1; \2"', inner)
    if leftovers:
        raise ValueError('uses colors other than the inks: ' + ', '.join(sorted(leftovers)) +
                         ' (pass them as --ink1/--ink2, or use trace mode)')
    return vb.group(1), inner


def tight_viewbox(vb, inner):
    """Shrink the viewBox to the drawn shapes (plus a small margin) using a headless browser."""
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as td:
        page = pathlib.Path(td) / 'b.html'
        page.write_text(f'<!doctype html><html><body><svg id="s" xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="1000"><g id="g">{inner}</g></svg></body></html>', encoding='utf-8')
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto(page.as_uri())
            r = pg.evaluate("() => { const b = document.getElementById('g').getBBox(); return [b.x, b.y, b.width, b.height]; }")
            b.close()
    x, y, w, h = r
    m = max(w, h) * 0.005
    return f'{x - m:.1f} {y - m:.1f} {w + 2 * m:.1f} {h + 2 * m:.1f}'


def render_rgba(src, width):
    import numpy as np
    from PIL import Image
    if src.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
        im = Image.open(src).convert('RGBA')
        if im.width < width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        return np.asarray(im).astype(int)
    if src.suffix.lower() != '.svg':
        sys.exit('Trace mode takes .svg, .png, .jpg or .webp')
    from playwright.sync_api import sync_playwright
    s = src.read_text(encoding='utf-8')
    vb = re.search(r'viewBox="([^"]+)"', s)
    vw, vh = [float(x) for x in vb.group(1).replace(',', ' ').split()[2:4]] if vb else (1000, 1000)
    h = round(width * vh / vw)
    with tempfile.TemporaryDirectory() as td:
        page = pathlib.Path(td) / 'p.html'
        svg = re.sub(r'<svg\b([^>]*)>',
                     lambda m: '<svg' + re.sub(r'\s(width|height)="[^"]*"', '', m.group(1)) + f' width="{width}" height="{h}">',
                     s, count=1)
        page.write_text(f'<!doctype html><html><body style="margin:0;background:transparent">{svg}</body></html>', encoding='utf-8')
        out = pathlib.Path(td) / 'r.png'
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={'width': width, 'height': h})
            pg.goto(page.as_uri())
            pg.wait_for_timeout(1500)
            pg.locator('svg').first.screenshot(path=str(out), omit_background=True)
            b.close()
        return np.asarray(Image.open(out).convert('RGBA')).astype(int)


def trace_mode(src, inks, knockouts, width, crop):
    import numpy as np
    from PIL import Image
    a = render_rgba(src, width)
    opaque = a[..., 3] >= 128
    refs = [(slot, hex_rgb(v)) for slot, v in inks.items()] + [(None, hex_rgb(k)) for k in knockouts]
    rgb = a[..., :3]
    dist = np.stack([((rgb - np.array(c)) ** 2).sum(axis=2) for _, c in refs])
    nearest = dist.argmin(axis=0)
    masks = {slot: opaque & (nearest == i) for i, (slot, _) in enumerate(refs) if slot}
    H, W = opaque.shape
    x0, y0, x1, y1 = 0, 0, W, H
    if crop:
        anyink = np.zeros_like(opaque)
        for m in masks.values():
            anyink |= m
        ys, xs = np.nonzero(anyink)
        if len(xs) == 0:
            sys.exit('No ink found. Check --ink1/--ink2 against the colors in the export.')
        pad = max(4, W // 200)
        x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
        x1, y1 = min(W, xs.max() + pad + 1), min(H, ys.max() + pad + 1)
    parts = []
    with tempfile.TemporaryDirectory() as td:
        for slot, m in masks.items():
            m = m[y0:y1, x0:x1]
            if not m.any():
                continue
            pbm = pathlib.Path(td) / f'{slot}.pbm'
            svg = pathlib.Path(td) / f'{slot}.svg'
            Image.fromarray(((~m) * 255).astype('uint8')).convert('1').save(pbm)
            subprocess.run(['potrace', str(pbm), '-b', 'svg', '-t', '6', '-a', '1.0', '-O', '0.4', '--flat', '-o', str(svg)], check=True)
            t = svg.read_text()
            g = re.search(r'<g transform="([^"]+)"[^>]*>\s*<path d="([^"]+)"', t)
            if g:
                parts.append(f'<g transform="{g.group(1)}"><path style="fill: var(--{slot}, {norm(inks[slot])})" d="{g.group(2).replace(chr(10), " ")}"/></g>')
    return f'0 0 {x1 - x0} {y1 - y0}', '\n'.join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key', help='design key, e.g. advent (becomes art/advent.svg)')
    ap.add_argument('src', type=pathlib.Path)
    ap.add_argument('--ink1', required=True)
    ap.add_argument('--ink2')
    ap.add_argument('--one-color', action='store_true')
    ap.add_argument('--knockout', action='append', default=[])
    ap.add_argument('--mode', choices=['auto', 'vector', 'trace'], default='auto')
    ap.add_argument('--width', type=int, default=3000)
    ap.add_argument('--no-crop', dest='crop', action='store_false')
    a = ap.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9_]*', a.key):
        sys.exit('key: lower-case letters, digits and _ only, starting with a letter')
    if not a.one_color and not a.ink2:
        sys.exit('Give --ink2, or --one-color for single-ink art')
    inks = {'i1': a.ink1} if a.one_color else {'i1': a.ink1, 'i2': a.ink2}
    mode = a.mode
    if mode in ('auto', 'vector') and a.src.suffix.lower() == '.svg':
        try:
            vb, body = vector_mode(a.src, inks)
            if a.crop:
                vb = tight_viewbox(vb, body)
            mode = 'vector'
        except ValueError as e:
            if a.mode == 'vector':
                sys.exit(f'Vector mode failed: {e}')
            print(f'Vector mode not possible ({e}); tracing instead.')
            mode = 'trace'
    elif mode == 'vector':
        sys.exit('Vector mode needs an .svg')
    else:
        mode = 'trace'
    if mode == 'trace':
        vb, body = trace_mode(a.src, inks, a.knockout, a.width, a.crop)
    out = ROOT / 'art' / f'{a.key}.svg'
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">\n<title>{a.key}</title>\n{body}\n</svg>\n', encoding='utf-8')
    w, h = [float(x) for x in vb.split()[2:4]]
    print(f'Wrote {out.relative_to(ROOT)} ({mode} mode). Height/width = {h / w:.3f} '
          f'(prints {12 * h / w:.1f}" tall at 12" wide; must be 14" or less on adult shirts).')
    print(f'Next: add a {{ k: \'{a.key}\', ... }} entry to src/catalog.js, then run python3 tools/build.py')


if __name__ == '__main__':
    main()
