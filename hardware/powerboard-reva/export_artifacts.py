#!/usr/bin/env python3
"""Regenerate, export with real KiCad CLI, then audit exported connectivity."""
from pathlib import Path
import subprocess
p=Path(__file__).resolve().parent
(p/'exports/svg').mkdir(parents=True,exist_ok=True)
# Remove only obsolete generated rider-Hall pages; machine Hall sensors remain.
for old in (p/'exports/svg').glob('*rider Hall and supervised binary interface.svg'):
    old.unlink()
commands=[['python3','generate_schematic.py'],['kicad-cli','sch','export','netlist','-o','exports/powerboard-reva.net','powerboard-reva.kicad_sch'],['kicad-cli','sch','erc','-o','exports/erc.rpt','powerboard-reva.kicad_sch'],['kicad-cli','sch','export','pdf','-o','exports/powerboard-reva.pdf','powerboard-reva.kicad_sch'],['kicad-cli','sch','export','svg','-o','exports/svg','powerboard-reva.kicad_sch'],['python3','verify_exports.py']]
for command in commands:
    print('+',' '.join(command),flush=True)
    subprocess.run(command,cwd=p,check=True)
# Native XML is an independent test input; never synthesized from the manifest.
subprocess.run(['kicad-cli','sch','export','netlist','--format','kicadxml','-o','exports/ctrl-supply.xml','powerboard-reva.kicad_sch'],cwd=p,check=True)
# Strict ERC is evidence, not waived by consistency-check success.
strict = subprocess.run(['kicad-cli','sch','erc','--format','json','--exit-code-violations','-o','exports/fsr-erc-strict.json','powerboard-reva.kicad_sch'],cwd=p)
(p/'exports/fsr-erc-exit.txt').write_text(str(strict.returncode)+'\n')
if strict.returncode not in (0,5):
    raise SystemExit(strict.returncode)
print('Strict ERC exit:',strict.returncode,'; nonzero violations remain release blockers')
