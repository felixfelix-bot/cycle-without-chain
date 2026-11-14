"""Tests for the QFN-40 land-pattern audit (PCB-02, pad half).

The audit compares the stock KiCad QFN-40 footprint used by both DRV8353s against the
vendor's published land geometry. A check that only ever passes proves nothing, so the
mutant tests below break the geometry and assert the audit reports it.

WHY THE MUTATION RUNS IN A SUBPROCESS
-------------------------------------
`pcbnew` is installed only for the system interpreter, and `pytest` only for the
project's python3. So this test file cannot import pcbnew itself. The board is mutated
by a tiny script executed with the interpreter that HAS pcbnew, and the audit is then
run the same way. That keeps one test file runnable under the documented runner.

Mutation is done through the pcbnew API rather than by editing text. Text substitution
found the WRONG pad twice while this was being written -- a nested pad before the real
one, and a 0603's pad in another footprint -- and both times the audit correctly said
PASS because the footprint had not changed. An API mutation cannot make that mistake.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
AUDIT = HERE / "audit_qfn40_land.py"
BOARD = HERE / "powerboard-reva.kicad_pcb"
SYS_PY = "/usr/bin/python3"          # the interpreter with pcbnew

MUTATE = r'''
import sys, pcbnew
path, ref, padnum, what = sys.argv[1:5]
b = pcbnew.LoadBoard(path)
hit = False
for fp in b.GetFootprints():
    if fp.GetReference() != ref:
        continue
    for p in fp.Pads():
        if p.GetNumber() != padnum:
            continue
        if what == "width":
            p.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.725), pcbnew.FromMM(0.250)))
        elif what == "pitch":
            pos = p.GetPosition()
            p.SetPosition(pcbnew.VECTOR2I(pos.x, pos.y + pcbnew.FromMM(0.15)))
        hit = True
    break
if not hit:
    print("MUTATION TARGET NOT FOUND"); sys.exit(3)
pcbnew.SaveBoard(path, b)
print("mutated %s pad %s (%s)" % (ref, padnum, what))
'''


def _stage(tmp_path):
    shutil.copy2(BOARD, tmp_path / BOARD.name)
    shutil.copy2(AUDIT, tmp_path / AUDIT.name)


def _run(cmd, cwd):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       timeout=900)
    return r.returncode, r.stdout + r.stderr


def _mutate(tmp_path, ref, padnum, what):
    script = tmp_path / "_mutate.py"
    script.write_text(MUTATE)
    rc, out = _run([SYS_PY, str(script), str(tmp_path / BOARD.name),
                    ref, padnum, what], tmp_path)
    assert rc == 0, out
    return out


def _audit(tmp_path):
    return _run([SYS_PY, str(AUDIT)], tmp_path)


def test_audit_passes_on_the_real_board(tmp_path):
    _stage(tmp_path)
    rc, out = _audit(tmp_path)
    assert rc == 0, out
    assert "PASS" in out


def test_audit_catches_a_pad_width_error(tmp_path):
    """0.825 -> 0.725 mm is 0.1 mm, far outside the 0.5 um tolerance."""
    _stage(tmp_path)
    _mutate(tmp_path, "U1", "1", "width")
    rc, out = _audit(tmp_path)
    assert rc == 1, "audit passed a board whose pad 1 is 0.1 mm too narrow:\n" + out
    assert "0.7250" in out or "pad1 size" in out


def test_audit_catches_a_pitch_error(tmp_path):
    """Move pad 2 by 0.15 mm, turning a 0.5 mm pitch into 0.65 mm."""
    _stage(tmp_path)
    _mutate(tmp_path, "U1", "2", "pitch")
    rc, out = _audit(tmp_path)
    assert rc == 1, "audit passed a board with a 0.65 mm pitch:\n" + out
