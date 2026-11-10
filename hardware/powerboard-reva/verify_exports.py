#!/usr/bin/env python3
"""Verify actual KiCad-exported nets, not generator intent alone."""
import csv,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
# Import also deterministically regenerates sources; export first using same generator.
from generate_schematic import parse,child,val
net=parse((P/'exports/powerboard-reva.net').read_text())
components=child(net,'components')[1:]; nets=child(net,'nets')[1:]
actual={}
for n in nets:
    name=val(child(n,'name')[1])
    for node in n:
        if isinstance(node,list) and node[0]=='node': actual[(val(child(node,'ref')[1]),val(child(node,'pin')[1]))]=name
expected=list(csv.DictReader((P/'pin-net-map.csv').open()))
errors=[f'{r}: exported {actual.get((r["ref"],r["pin"]))}' for r in expected if actual.get((r['ref'],r['pin']))!=r['net']]
assert not errors,'\n'.join(errors)
assert len(components)==84
assert len([c for c in components if val(child(c,'ref')[1]).startswith('Q')])==12
assert len([c for c in components if val(child(c,'ref')[1]).startswith('U')])==2
assert len(nets)==80
rpt=(P/'exports/erc.rpt').read_text()
issues=re.findall(r'^\[([^]]+)\]',rpt,re.M)
assert issues==['power_pin_not_driven']*3,issues
summary={'components':len(components),'nets':len(nets),'verified_pin_assignments':len(expected),'mosfets':12,'drivers':2,'erc_errors':3,'erc_warnings':0,'erc_reason':'External AUX12V_EXT, LOGIC3V3_EXT, PGND supplies not modeled as power outputs. No PWR_FLAG used to hide unfinished supply boundary.','status':'PARTIAL_NOT_SAFE_TO_ENERGIZE','svg_pages':len(list((P/'exports/svg').glob('*.svg')))}
(P/'exports/verification.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
