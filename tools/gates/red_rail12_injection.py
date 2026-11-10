"""RED evidence for RAIL-12, captured before the pair wiring existed.

The defect, stated exactly. Two exports of the same design exist:

* ``exports/ctrl-supply.xml`` — what the topology tests read;
* ``exports/powerboard-reva.net`` — what ``verify_exports.py`` grades.

``verify_exports.py`` grades the `.net` against ``pin-net-map.csv``, and the
topology tests assert a handful of pins in the XML. Nothing grades the XML as a
whole, and nothing compares the two artifacts, so **a rail split injected into
the XML alone stays green**: the `.net` side never sees it and the pin-level
tests do not cover it.

This script does not modify anything under `hardware/`: it copies the XML into
a scratch dir and injects there.

    python3 tools/gates/red_rail12_injection.py
"""
import csv
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOARD = ROOT / "hardware" / "powerboard-reva"
XML = BOARD / "exports" / "ctrl-supply.xml"
NET = BOARD / "exports" / "powerboard-reva.net"
CSV = BOARD / "pin-net-map.csv"


def expected_from_pin_map(path):
    """The committed pin->net contract, spelled as the gate's expected map."""
    nets = {}
    for row in csv.DictReader(path.open()):
        nets.setdefault(row["net"], []).append([row["ref"], row["pin"]])
    return {"nets": {name: sorted(rows) for name, rows in sorted(nets.items())}}


def inject_split(source, target):
    """Move one DRIVE12 node onto a new net: a split visible in XML only."""
    target.write_bytes(source.read_bytes())
    tree = ET.parse(target)
    nets = tree.getroot().find("nets")
    if nets is None:
        raise SystemExit("no <nets> in the XML copy")
    drive = next(n for n in nets.findall("net") if n.get("name") == "DRIVE12")
    moved = drive.findall("node")[0]
    drive.remove(moved)
    split = ET.SubElement(nets, "net", {"code": "999", "name": "DRIVE12_SPLIT"})
    split.append(moved)
    tree.write(target)
    return target


def gate(args):
    proc = subprocess.run([sys.executable, "-m", "tools.gates.netlist_parity", *args],
                          cwd=str(ROOT), capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        payload = {"verdict": "NO JSON", "reason": proc.stderr.strip()[-300:]}
    return proc.returncode, payload


def invoking_files():
    """Which automation invokes the parity gate on this head?"""
    hits = []
    roots = [ROOT / "tools"]
    if (ROOT / ".github").exists():
        roots.append(ROOT / ".github")
    skip = {"run_all_gates.py", "netlist_parity.py", "red_rail12_injection.py"}
    for base in roots:
        for path in base.rglob("*"):
            if not path.is_file() or path.name in skip:
                continue
            if path.suffix not in {".py", ".yml", ".yaml", ".sh", ".cfg", ".toml"}:
                continue
            try:
                if "netlist_parity" in path.read_text():
                    hits.append(str(path.relative_to(ROOT)))
            except (UnicodeDecodeError, OSError):
                continue
    return sorted(hits)


def is_wired():
    """Is the pair wiring present in this tree?

    On an unwired head the ``--netlist-sexpr`` flag does not exist, so the pair
    call is NOT RUN and the injected split is invisible to every check that
    runs. On a wired head the pair call grades both artifacts and goes red.
    The same script therefore demonstrates the gap and the closure.
    """
    proc = subprocess.run([sys.executable, "-m", "tools.gates.netlist_parity",
                           "--help"], cwd=str(ROOT), capture_output=True, text=True)
    return "--netlist-sexpr" in (proc.stdout + proc.stderr)


def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="rail12-red-"))
    expected = tmpdir / "expected.json"
    expected.write_text(json.dumps(expected_from_pin_map(CSV), indent=1))

    injected_xml = inject_split(XML, tmpdir / "ctrl-supply.xml")

    # One expected map, four questions. `--netlist-sexpr` without `--netlist`
    # grades the S-expression artifact through the pair code path; on an
    # unwired head the flag does not exist and the call is NOT RUN.
    clean_code, clean = gate(["--netlist", str(XML), "--expected", str(expected)])
    split_code, split = gate(["--netlist", str(injected_xml), "--expected", str(expected)])
    net_code, net_payload = gate(["--netlist", str(XML),
                                  "--netlist-sexpr", str(NET),
                                  "--expected", str(expected)])
    untouched_net_code, untouched_net = gate(["--netlist", str(injected_xml),
                                              "--netlist-sexpr", str(NET),
                                              "--expected", str(expected)])
    wired = is_wired()

    print("1. XML as committed                               ->",
          clean_code, clean["verdict"])
    print("2. XML with a DRIVE12 split injected, graded alone ->",
          split_code, split["verdict"],
          "extra nets:", split.get("diffs", {}).get("nets_extra"))
    print("3. the untouched `.net`, graded against the map    ->",
          net_code if wired else "NOT RUN",
          "the split is invisible here, which is the defect")
    print("4. injected XML + untouched `.net`, graded as a pair ->",
          untouched_net_code, untouched_net["verdict"] if wired else "-",
          untouched_net.get("reason", ""))
    print("5. files invoking netlist_parity on this head      ->",
          invoking_files() or "none")
    print()
    print("The defect: the XML the topology tests read and the `.net` that")
    print("verify_exports.py grades are two exports of one design. Grading either")
    print("one alone cannot see a change made only to the other.")
    print()
    if wired:
        print("On this head the pair call exists (4) and goes RED on the injected")
        print("XML, even though the `.net` beside it is untouched and would pass on")
        print("its own (3).")
    else:
        print("On this head there is no pair call at all (4 is NOT RUN), so a split")
        print("injected into the XML alone is invisible to every check that runs.")
    print("scratch dir:", tmpdir)


if __name__ == "__main__":
    main()
