#!/usr/bin/env python3
"""Build dist/index.html: the self-contained NVF Shirt Studio page.

Inputs:  src/template.html, src/catalog.js, art/*.svg, logos/*.svg
Output:  dist/index.html  (one file, no external assets except Google Fonts for the UI text)
Run:     python3 tools/build.py
"""
import json, re, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

def load_svg(path):
    s = path.read_text(encoding='utf-8')
    vb = re.search(r'<svg[^>]*\sviewBox="([^"]+)"', s)
    if not vb:
        sys.exit(f'{path}: missing viewBox')
    inner = re.sub(r'^.*?<svg[^>]*>', '', s, count=1, flags=re.S)
    inner = re.sub(r'</svg>\s*$', '', inner.strip())
    inner = re.sub(r'<title>.*?</title>\s*', '', inner, count=1, flags=re.S)
    return {'vb': vb.group(1), 'body': inner.strip()}

def main():
    catalog = (ROOT / 'src/catalog.js').read_text(encoding='utf-8')
    art = {p.stem: load_svg(p) for p in sorted((ROOT / 'art').glob('*.svg'))}
    logos = {p.stem: load_svg(p) for p in sorted((ROOT / 'logos').glob('*.svg'))}
    keys = re.findall(r"\{ k: '(\w+)', t:", catalog)
    for k in keys:
        if k not in art:
            sys.exit(f'Design "{k}" is in src/catalog.js but art/{k}.svg is missing')
    for k in re.findall(r"art1: '(\w+)'", catalog):
        if k not in art:
            sys.exit(f'art1 "{k}" is in src/catalog.js but art/{k}.svg is missing')
    for k in ('stacked', 'horizontal'):
        if k not in logos:
            sys.exit(f'logos/{k}.svg is missing')
    t = (ROOT / 'src/template.html').read_text(encoding='utf-8')
    t = t.replace('/*CATALOG*/', catalog)
    t = t.replace('/*ART*/', json.dumps(art, separators=(',', ':')))
    t = t.replace('/*LOGO*/', json.dumps(logos, separators=(',', ':')))
    out = ROOT / 'dist/index.html'
    out.parent.mkdir(exist_ok=True)
    out.write_text(t, encoding='utf-8')
    print(f'Built {out.relative_to(ROOT)}: {len(keys)} designs, {len(t)//1024} KB')

if __name__ == '__main__':
    main()
