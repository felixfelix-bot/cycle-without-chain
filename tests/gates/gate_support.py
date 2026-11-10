"""Shared harness for the gates tests: fixture builders and a fake ``kicad-cli``.

The fake CLI is a real executable script so the gate exercises the same
subprocess boundary it would with the real tool: argument parsing, return
codes, missing output files, truncated reports and timeouts are all
controlled from the test and none of it is mocked inside the gate code.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PREFIX = "tools.gates."

# --------------------------------------------------------------------------
# Minimal but structurally real input artifacts. They are not boards anyone
# should fabricate; they exist so the gates' object probes have something to
# count and so a missing file/pad is detectable.
# --------------------------------------------------------------------------

BOARD_MIN = """(kicad_pcb (version 20240108) (generator pcbnew)
  (footprint "Test:R_0603" (layer "F.Cu")
    (pad "1" smd roundrect (at 0 0) (size 1 1) (layers "F.Cu"))
    (pad "2" smd roundrect (at 1 0) (size 1 1) (layers "F.Cu"))))
"""

BOARD_NO_PADS = """(kicad_pcb (version 20240108) (generator pcbnew)
  (footprint "Test:MountingHole" (layer "F.Cu")))
"""

BOARD_EMPTY = """(kicad_pcb (version 20240108) (generator pcbnew))
"""

SCH_MIN = """(kicad_sch (version 20231120) (generator eeschema)
  (symbol (lib_id "Device:R") (at 0 0 0) (uuid "11111111-1111-5111-8111-111111111111")))
"""

SCH_NO_SYMBOLS = """(kicad_sch (version 20231120) (generator eeschema))
"""


def drc_report(violations=(), unconnected=(), source="board.kicad_pcb", parity=()):
    payload = {
        "$schema": "https://schemas.kicad.org/drc.v1.json",
        "coordinate_units": "mm",
        "date": "2026-11-10T00:00:00+0100",
        "kicad_version": "9.0.9",
        "source": source,
        "schematic_parity": list(parity),
        "violations": list(violations),
        "unconnected_items": list(unconnected),
    }
    return json.dumps(payload, indent=1)


def violation(description="Track too close", severity="error", kind="clearance"):
    return {
        "description": description,
        "items": [{"description": "Track [GND] on F.Cu", "pos": {"x": 1.0, "y": 2.0}}],
        "severity": severity,
        "type": kind,
    }


def erc_report(violations=(), sheets=("/",), kicad_version="9.0.9"):
    payload = {
        "$schema": "https://schemas.kicad.org/erc.v1.json",
        "coordinate_units": "mm",
        "date": "2026-11-10T00:00:00+0100",
        "kicad_version": kicad_version,
        "included_severities": ["error", "warning"],
        "sheets": [
            {"path": path, "uuid_path": "/00000000-0000-5000-8000-000000000000", "violations": list(violations)}
            for path in sheets
        ],
    }
    return json.dumps(payload, indent=1)


def netlist_xml(nets, *, components=("R1", "R2", "C1")):
    """Build a KiCad-9-shaped XML netlist (``--format kicadxml`` output).

    ``nets`` maps net name -> iterable of (ref, pin).
    """
    from xml.sax.saxutils import escape

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<export version="E">', "  <design>",
             '    <source>board.kicad_sch</source>',
             '    <tool>Eeschema 9.0.9</tool>',
             '    <sheet number="1" name="/" tstamps="/"/>',
             "  </design>", "  <components>"]
    for ref in components:
        lines.append('    <comp ref="%s"><value>x</value><footprint>Test:R_0603</footprint></comp>'
                     % escape(ref))
    lines.append("  </components>")
    lines.append("  <nets>")
    for code, (name, nodes) in enumerate(sorted(nets.items()), start=1):
        lines.append('    <net code="%d" name="%s">' % (code, escape(name)))
        for ref, pin in nodes:
            lines.append('      <node ref="%s" pin="%s"/>' % (escape(ref), escape(pin)))
        lines.append("    </net>")
    lines.append("  </nets>")
    lines.append("</export>")
    return "\n".join(lines) + "\n"


def netlist_sexpr(nets, *, components=("R1", "R2", "C1")):
    """Build a KiCad-9-shaped S-expression netlist (``sch export netlist``).

    The XML and this file are two exports of the same design; the parity gate
    must grade both against one expected map. ``nets`` maps net name ->
    iterable of (ref, pin).
    """
    lines = ['(export (version "E")',
             '  (design',
             '    (source "board.kicad_sch")',
             '    (date "2026-11-10T00:00:00+0100")',
             '    (tool "Eeschema 9.0.9")',
             '    (sheet (number "1") (name "/") (tstamps "/")))',
             '  (components']
    for ref in components:
        lines.append('    (comp (ref "%s") (value "x") (footprint "Test:R_0603"))' % ref)
    lines.append("  )")
    lines.append("  (nets")
    for code, (name, nodes) in enumerate(sorted(nets.items()), start=1):
        lines.append('    (net (code "%d") (name "%s") (class "Default")' % (code, name))
        for ref, pin in nodes:
            lines.append('      (node (ref "%s") (pin "%s") (pintype "passive"))' % (ref, pin))
        lines.append("    )")
    lines.append("  ))")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Fake kicad-cli
# --------------------------------------------------------------------------

_FAKE_SOURCE = r'''#!/usr/bin/env python3
"""Test double for kicad-cli. Behaviour comes from an embedded JSON spec."""
import json, os, sys, time

SPEC = json.loads({spec!r})
argv = sys.argv[1:]

if argv[:1] == ["pcb"]:
    kind = "drc"
elif argv[:2] == ["sch", "erc"]:
    kind = "erc"
elif argv[:1] == ["sch"] and "netlist" in argv:
    kind = "netlist"
else:
    kind = "other"

record = os.environ.get("FAKE_KICAD_LOG")
if record:
    with open(record, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({{"kind": kind, "argv": argv}}) + "\n")

spec = SPEC.get(kind, {{}})
if spec.get("sleep"):
    time.sleep(float(spec["sleep"]))

out = None
for index, arg in enumerate(argv):
    if arg in ("-o", "--output") and index + 1 < len(argv):
        out = argv[index + 1]

if out and spec.get("write", True) and spec.get("content") is not None:
    parent = os.path.dirname(os.path.abspath(out))
    os.makedirs(parent, exist_ok=True)
    binary = bool(spec.get("binary"))
    payload = spec["content"]
    if not binary and not isinstance(payload, str):
        payload = json.dumps(payload)
    with open(out, "wb") as handle:
        handle.write(payload if binary else payload.encode())
# a "write to the wrong path" behaviour, used to prove the gate is not fooled
if out and spec.get("write_to"):
    with open(spec["write_to"], "w", encoding="utf-8") as handle:
        handle.write(spec.get("content") or "")

sys.exit(int(spec.get("exit", 0)))
'''


def make_fake_kicad(tmp_path, spec):
    """Write an executable fake ``kicad-cli`` and return its path."""
    script = tmp_path / "fake-kicad-cli"
    script.write_text(_FAKE_SOURCE.format(spec=json.dumps(spec)))
    script.chmod(0o755)
    return script


# --------------------------------------------------------------------------
# Module runner
# --------------------------------------------------------------------------

def run_gate(module, args, *, cwd=None, env_extra=None, timeout=120):
    """Run ``python3 -m tools.gates.<module>`` and return (proc, payload)."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    # Extra path entries let a coverage sitecustomize.py reach the gate
    # subprocesses; it is never set during a normal run.
    extra = env.get("GATES_EXTRA_PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(REPO_ROOT), extra) if part)
    if env_extra:
        env.update(env_extra)
    command = [sys.executable, "-m", MODULE_PREFIX + module, *[str(a) for a in args]]
    proc = subprocess.run(
        command,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    payload = None
    text = proc.stdout.strip()
    if text:
        try:
            payload = json.loads(text.splitlines()[-1])
        except json.JSONDecodeError:
            payload = None
    return proc, payload


def write(path, text, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)
    return path
