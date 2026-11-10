"""Measure native KiCad stroke-text bounds, not invisible SVG font estimates.
Bounded to FSR and neighboring brake pages; no electrical interpretation.
"""
import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

NS = '{http://www.w3.org/2000/svg}'
TITLES = ('FSR', 'binary brake', 'switch end-of-line', 'dump PWM')

def bounds(el):
    pts = []
    for p in el.iter(NS+'path'):
        nums = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', p.get('d', ''))]
        pts += list(zip(nums[::2], nums[1::2]))
    if not pts:
        return None
    return [min(x for x,y in pts)-.0762, min(y for x,y in pts)-.0762,
            max(x for x,y in pts)+.0762, max(y for x,y in pts)+.0762]

def overlap(a,b):
    return min(a[2],b[2]) > max(a[0],b[0]) and min(a[3],b[3]) > max(a[1],b[1])

def measure(path):
    root=ET.parse(path).getroot()
    text=[]; shapes=[]
    def walk(e):
        if e.get('class') == 'stroked-text':
            b=bounds(e)
            if b: text.append((''.join(e.find(NS+'desc').itertext()),b))
            return
        if e.tag == NS+'path' and not re.search(r'[AaCcQqSsTt]', e.get('d','')):
            # Test individual straight strokes, NOT the filled bounding box of
            # a label outline (its text intentionally lives inside that box).
            commands=re.findall(r'([ML])\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)', e.get('d',''))
            previous=None
            for cmd,x,y in commands:
                point=(float(x),float(y))
                if cmd=='L' and previous is not None:
                    x0,y0=previous; x1,y1=point
                    shapes.append([min(x0,x1)-.0762,min(y0,y1)-.0762,max(x0,x1)+.0762,max(y0,y1)+.0762])
                previous=point
        for ch in e: walk(ch)
    walk(root)
    # Exclude frame/title block and review prose; inspect circuit field region.
    text=[(t,b) for t,b in text if b[0]>15 and b[1]>30 and b[3]<245]
    tt=[(a,c) for i,(a,b) in enumerate(text) for c,d in text[i+1:] if overlap(b,d)]
    ts=[(a,b,s) for a,b in text for s in shapes if overlap(b,s)
        and s[2]-s[0]<80 and s[3]-s[1]<80]
    return {'text_bounds_mm':text,'text_text':tt,'text_graphic':ts}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('svg_dir');ap.add_argument('--out',required=True);ap.add_argument('--check',action='store_true');args=ap.parse_args()
    result={p.name:measure(p) for p in Path(args.svg_dir).glob('*.svg') if any(t in p.name for t in TITLES)}
    Path(args.out).write_text(json.dumps(result,indent=2)+'\n')
    for name,r in result.items(): print(name,len(r['text_bounds_mm']),'text;',len(r['text_text']),'text/text;',len(r['text_graphic']),'text/graphic')
    if not result: raise SystemExit('No target SVGs')
    if args.check and any(r['text_text'] or r['text_graphic'] for r in result.values()): raise SystemExit(1)
