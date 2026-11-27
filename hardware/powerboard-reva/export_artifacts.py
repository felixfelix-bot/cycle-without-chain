#!/usr/bin/env python3
"""Regenerate, export with real KiCad CLI, then audit exported connectivity."""
from pathlib import Path
import subprocess
p=Path(__file__).resolve().parent
(p/'exports/svg').mkdir(parents=True,exist_ok=True)
commands=[['python3','generate_schematic.py'],['kicad-cli','sch','export','netlist','-o','exports/powerboard-reva.net','powerboard-reva.kicad_sch'],['kicad-cli','sch','erc','-o','exports/erc.rpt','powerboard-reva.kicad_sch'],['kicad-cli','sch','export','pdf','-o','exports/powerboard-reva.pdf','powerboard-reva.kicad_sch'],['kicad-cli','sch','export','svg','-o','exports/svg','powerboard-reva.kicad_sch'],['python3','verify_exports.py']]
for command in commands:
    print('+',' '.join(command),flush=True)
    subprocess.run(command,cwd=p,check=True)
