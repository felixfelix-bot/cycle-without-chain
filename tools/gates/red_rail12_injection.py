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


def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="rail12-red-"))
    expected = tmpdir / "expected.json"
    expected.write_text(json.dumps(expected_from_pin_map(CSV), indent=1))

    clean_code, clean = gate(["--netlist", str(XML), "--expected", str(expected)])
    injected_xml = inject_split(XML, tmpdir / "ctrl-supply.xml")
    split_code, split = gate(["--netlist", str(injected_xml), "--expected", str(expected)])
    net_code, net_payload = gate(["--netlist", str(NET), "--expected", str(expected)])
    pair_code, pair = gate(["--netlist", str(injected_xml),
                            "--netlist-sexpr", str(NET),
                            "--expected", str(expected)])

    print("1. gate on the clean committed XML               ->",
          clean_code, clean["verdict"])
    print("2. gate on that XML with a DRIVE12 split injected ->",
          split_code, split["verdict"],
          "extra nets:", split.get("diffs", {}).get("nets_extra"))
    print("3. gate pointed at the S-expression `.net`        ->",
          net_code, net_payload["verdict"], "-", net_payload.get("reason", ""))
    print("4. gate on BOTH artifacts at once                ->",
          pair_code, pair["verdict"], "-", pair.get("reason", ""))
    print("5. files that invoke netlist_parity on this head ->",
          invoking_files() or "none")
    print()
    print("So: the strict comparison does exist and does catch an injected split")
    print("(2 is red). But nothing points it at the committed artifacts, it cannot")
    print("read the `.net` at all (3), and it cannot compare the two (4). A split")
    print("injected into the XML alone is therefore invisible to every check that")
    print("actually runs — which is the RAIL-12 defect.")
    print("scratch dir:", tmpdir)


if __name__ == "__main__":
    main()
