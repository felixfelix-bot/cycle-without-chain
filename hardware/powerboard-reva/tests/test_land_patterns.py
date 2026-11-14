"""Mutation tests for the HSOP-8 / TO-247 / VSSOP-8 land audits (PCB-02).

Every check here must be able to FAIL. The QFN-40 audit in this project passed on real
hardware while its pitch test was dead code -- it only ran when the wrong pad list won a
length comparison -- and that was found only by writing a mutant that should have failed
and did not. So each family gets a mutant that changes one real quantity by more than
the 0.01 mm tolerance.

Mutations run in a subprocess with the interpreter that has pcbnew, because pcbnew is
not installed for the project's pytest python. Mutations go through the pcbnew API, not
text substitution: text substitution picked the wrong pad twice in this project (a
nested pad before the real one, and another footprint's pad), and the audit correctly
reported PASS both times because nothing had actually changed.
"""
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
AUDIT = HERE / "audit_power_lands.py"
BOARD = HERE / "powerboard-reva.kicad_pcb"
SYS_PY = "/usr/bin/python3"

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
        if what == "size":
            p.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(2.10), pcbnew.FromMM(0.60)))
        elif what == "shift":
            pos = p.GetPosition()
            p.SetPosition(pcbnew.VECTOR2I(pos.x, pos.y + pcbnew.FromMM(0.20)))
        elif what == "narrow":
            p.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.10), pcbnew.FromMM(0.35)))
        hit = True
    break
if not hit:
    print("TARGET NOT FOUND"); sys.exit(3)
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
    script = tmp_path / "_m.py"
    script.write_text(MUTATE)
    rc, out = _run([SYS_PY, str(script), str(tmp_path / BOARD.name),
                    ref, padnum, what], tmp_path)
    assert rc == 0, out


def _audit(tmp_path):
    return _run([SYS_PY, str(AUDIT)], tmp_path)


def test_audit_passes_on_the_real_board(tmp_path):
    _stage(tmp_path)
    rc, out = _audit(tmp_path)
    assert rc == 0, out
    assert "PASS" in out


def test_catches_hsop8_pad_width(tmp_path):
    """1.95 -> 2.10 mm on U500 pad 1."""
    _stage(tmp_path)
    _mutate(tmp_path, "U500", "1", "size")
    rc, out = _audit(tmp_path)
    assert rc == 1, "HSOP-8 pad width error not caught:\n" + out
    assert "U500" in out


def test_catches_hsop8_pitch(tmp_path):
    """Shift U500 pad 2 by 0.2 mm, breaking the 1.27 mm pitch."""
    _stage(tmp_path)
    _mutate(tmp_path, "U500", "2", "shift")
    rc, out = _audit(tmp_path)
    assert rc == 1, "HSOP-8 pitch error not caught:\n" + out


def test_catches_to247_pad_size(tmp_path):
    """2.5 -> 2.10 mm on Q400 pad 1."""
    _stage(tmp_path)
    _mutate(tmp_path, "Q400", "1", "size")
    rc, out = _audit(tmp_path)
    assert rc == 1, "TO-247 pad size error not caught:\n" + out
    assert "Q400" in out


def test_catches_vssop8_pad_width(tmp_path):
    """1.25 -> 1.10 mm on U7 pad 1."""
    _stage(tmp_path)
    _mutate(tmp_path, "U7", "1", "narrow")
    rc, out = _audit(tmp_path)
    assert rc == 1, "VSSOP-8 pad width error not caught:\n" + out


def test_catches_vssop8_pitch(tmp_path):
    """Shift U7 pad 2 by 0.2 mm, breaking the 0.5 mm pitch."""
    _stage(tmp_path)
    _mutate(tmp_path, "U7", "2", "shift")
    rc, out = _audit(tmp_path)
    assert rc == 1, "VSSOP-8 pitch error not caught:\n" + out
