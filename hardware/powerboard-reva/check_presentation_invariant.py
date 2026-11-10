"""Independent native XML comparison; no generator/checker parser imports."""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

def canonical(path):
    root=ET.parse(path).getroot()
    nodes=sorted((node.attrib['ref'],node.attrib['pin'],net.attrib['name'])
                 for net in root.findall('./nets/net') for node in net.findall('node'))
    parts=sorted((c.attrib['ref'],c.findtext('value'),c.findtext('footprint',''))
                 for c in root.findall('./components/comp'))
    if not nodes or not parts: raise ValueError('Empty native export')
    return {'ref_pin_net':nodes,'ref_value_footprint':parts}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('before');ap.add_argument('after');ap.add_argument('--out',required=True);args=ap.parse_args()
    before,after=canonical(args.before),canonical(args.after)
    if before != after: raise SystemExit('FAIL: native endpoints or part identity changed')
    Path(args.out).write_text(json.dumps(after,indent=2)+'\n')
    print(f"IDENTICAL: {len(after['ref_value_footprint'])} components, {len(after['ref_pin_net'])} ref/pin/net rows (includes native unconnected-pin nets)")
