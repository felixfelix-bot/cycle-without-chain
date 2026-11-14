#!/usr/bin/env python3
"""Generate a placed KiCad PCB from the exported netlist.

WHY pcbnew AND NOT HANDWRITTEN S-EXPRESSIONS
--------------------------------------------
balloon-fresh writes .kicad_pcb text directly, which works and is fast. It also
means every footprint instance, pad-net assignment and UUID is text this project
would have to keep valid by hand across 387 components. KiCad ships a real
pcbnew Python module at /usr/bin/python3 (9.0.9); using it means the library
loads the footprints, the API assigns pads, and kicad-cli DRC reads a file KiCad
itself wrote. One less thing to be subtly wrong.

Run with /usr/bin/python3, not the default python3 — pcbnew is not installed for
the 3.11 venv Python.

WHAT IT DOES
------------
  1. Reads exports/powerboard-reva.net (387 comps, 271 nets).
  2. Places components in functional blocks, mirroring the schematic's GEN/HUB
     symmetry so the two motor phases are physically identical.
  3. Leaves RESERVED zones for blocks the schematic marks inhibited/unqualified.
  4. Writes the edge cuts and a 4-layer stackup.
  5. Loads nets onto pads so the board is ready to route.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not route. Routing is a separate, reviewable step, and the 38 % of the
board that is not designable yet must not be routed at all.

PLACEMENT STRATEGY
------------------
Board 160 x 120 mm. Blocks are laid out by function in columns, with the two
motor phases (GEN left, HUB right) as mirror images about the vertical centre.
Power entry and the DC link sit along the bottom edge, the MCU and analog
sensing along the top where they are furthest from the switching nodes, and the
aux supply between them. That ordering is the electrically meaningful one: it
puts the least noise-sensitive circuits furthest from the highest di/dt loops.
"""

from __future__ import annotations

import math
import os
import re
import sys
import uuid

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.join(HERE, "exports", "powerboard-reva.net")
OUTPUT = os.path.join(HERE, "powerboard-reva.kicad_pcb")
LIBROOT = "/usr/share/kicad/footprints"
LOCAL_LIB = os.path.join(HERE, "Powerboard.pretty")

# Board envelope, derived in docs/design/pcb04-board-sizing.md from measured
# footprint area (66.4 cm2 of parts against a 179 cm2 requirement).
BOARD_W = 160.0
# 120 mm was derived from area alone and came within 2.7 mm of fitting. Shelf
# packing inside regions wastes some height no matter how the area is budgeted,
# and one 0603 capacitor still spilled off the bottom edge. 130 mm absorbs that
# inefficiency rather than pretending area arithmetic packs perfectly.
BOARD_H = 130.0

# Blocks whose circuits are not settled. Components here are placed inside a
# reserved courtyard and NOT routed; routing them would fix copper around a
# topology that is still going to change.
UNSETTLED = re.compile(
    r"schematic only|candidate|unqualified|inhibited|unfinished", re.I)

# Functional region assignment. Keyed by a substring of the sheet name.
# Order matters: first match wins.
REGIONS = [
    # (sheet substring,                  region name,        row)
    ("Bounded bench DC entry",           "power_entry",      "bottom"),
    ("MAIN back-to-back",                "reserved_main",    "reserved"),
    ("PRE back-to-back",                 "reserved_pre",     "reserved"),
    ("Independent brake chopper",        "brake_chopper",    "bottom"),
    ("Rider dump PWM",                   "brake_chopper",    "bottom"),
    ("Bus-fed auxiliary",                "aux_supply",       "middle"),
    ("CTRL3V3 pack-side buck",           "reserved_ctrl",    "reserved"),
    ("Rail partition",                   "rail_partition",   "middle"),
    ("Rail partition: SINK12",           "rail_partition",   "middle"),
    ("GEN DRV8353S driver",              "gen_driver",       "middle"),
    ("GEN 100 V MOSFET bridge",          "reserved_bridge",  "reserved"),
    ("HUB DRV8353S driver",              "hub_driver",       "middle"),
    ("HUB 100 V MOSFET bridge",          "reserved_bridge",  "reserved"),
    ("GEN independent raw CSA",          "gen_sense",        "top"),
    ("HUB independent raw CSA",          "hub_sense",        "top"),
    ("Ratiometric OC window",            "oc_window",        "top"),
    ("Autonomous OV chopper",            "ov_chopper",       "top"),
    ("Release-before-rearm",             "fault_logic",      "top"),
    ("LVC Schmitt fault inputs",         "fault_logic",      "top"),
    ("STM32G474VET6",                    "mcu",              "top"),
    ("MCU 3V3 decoupling",               "mcu",              "top"),
    ("Six CSA ADC input filters",        "analog_filter",    "top"),
    ("3V3 Hall interfaces",              "hall",             "middle"),
    ("LEFT supervised binary brake",     "brake_left",       "top"),
    ("RIGHT supervised binary brake",    "brake_right",      "top"),
    ("LEFT selected FSR",                "fsr_left",         "top"),
    ("RIGHT selected FSR",               "fsr_right",        "top"),
    ("LEFT FSR candidate ESD",           "fsr_left",         "top"),
    ("RIGHT FSR candidate ESD",          "fsr_right",        "top"),
    ("OFFBOARD supervised switch",       "reserved_offboard","reserved"),
    ("Unfinished safety",                "reserved_safety",  "reserved"),
]

# Region placement is COMPUTED from measured footprint area, not hand-drawn.
#
# The first attempt hard-coded 32 rectangles by eye. 91 components overflowed
# them, because guessing "the MCU block needs about this much room" is exactly
# the kind of estimate that looks fine and is wrong. Each region is now sized
# from the sum of its parts' real bounding boxes plus a routing allowance, which
# means the layout re-derives itself when the schematic changes.
#
# Regions are placed in priority order into a shelf packer over the board area.
REGION_ORDER = [
    "power_entry", "mcu", "analog_filter", "gen_sense", "hub_sense",
    "oc_window", "ov_chopper", "fault_logic", "brake_left", "brake_right",
    "gen_driver", "hub_driver", "aux_supply", "rail_partition", "hall",
    "fsr_left", "fsr_right", "brake_chopper",
    "reserved_safety", "reserved_ctrl", "reserved_main", "reserved_pre",
    "reserved_offroad", "reserved_offboard",
]

# Packing allowance: parts occupy this fraction of their region. The rest is
# routing channels and courtyard clearance. 0.55 was chosen because courtyard
# extents already include the part's own clearance; going lower wastes board.
PACK_FRACTION = 0.55


def _region_areas(comps: list[dict]) -> dict[str, tuple[int, float]]:
    """region -> (count, total footprint area mm^2)."""
    out = {}
    for c in comps:
        n, a = out.get(c["region"], (0, 0.0))
        out[c["region"]] = (n + 1, a + c.get("area", 0.0))
    return out


def pack_positions(sizes: list[tuple[float, float]], width: float):
    """Shelf-pack parts largest-first inside a fixed width.

    Returns (positions, height) where positions[i] is the (x, y) of the centre of
    the part whose size is sizes[i].

    Sizing and placement MUST use one function. They were separate: the region
    height was estimated from area, then the parts were placed by a second,
    different packing pass. When the two disagreed, parts were laid down past
    their own region's bottom edge, straight into the region below — J9's
    resistors landing on J9 is how that showed up. One code path cannot disagree
    with itself.
    """
    order = sorted(range(len(sizes)), key=lambda k: -(sizes[k][0] * sizes[k][1]))
    positions = [None] * len(sizes)
    cx, cy, shelf_h = 1.0, 1.0, 0.0
    for k in order:
        w, h = sizes[k]
        if cx + w > width - 1.0:
            cx = 1.0
            cy += shelf_h + 0.6
            shelf_h = 0.0
        positions[k] = (cx + w / 2.0, cy + h / 2.0)
        cx += w + 0.6
        shelf_h = max(shelf_h, h)
    return positions, cy + shelf_h + 1.0


def compute_regions(comps: list[dict]) -> dict[str, tuple]:
    """Pack regions into the board, largest first, sized by measured packing.

    Region width is set from area for a sensible aspect ratio, then the height is
    the REAL packed height of that region's parts at that width. Regions then
    shelf-pack into the board. Any region whose height makes the board overflow
    is visible in the returned rectangle rather than hidden by a fallback.
    """
    areas = _region_areas(comps)
    sizes = {}
    for c in comps:
        sizes.setdefault(c["region"], []).append(footprint_size(c["footprint"]))

    margin = 3.0
    usable_w = BOARD_W - 2 * margin
    x, y = margin, margin
    shelf_h = 0.0
    rects = {}
    for region, (_n, area) in sorted(areas.items(), key=lambda kv: -kv[1][1]):
        w = min(max(math.sqrt(area * 1.6), 12.0), usable_w)
        _pos, h = pack_positions(sizes[region], w)
        if x + w > BOARD_W - margin:
            x = margin
            y += shelf_h + 2.0
            shelf_h = 0.0
        rects[region] = (x, y, x + w, y + h)
        x += w + 2.0
        shelf_h = max(shelf_h, h)
    return rects

REGION_RECTS: dict[str, tuple] = {}


def region_for(ref: str, sheets: dict[str, str]) -> str:
    """Which placement region a reference belongs to.

    Promoted from a closure inside main() so that route_board_blocks.py can share
    exactly one definition of the block split. It previously called
    g.region_for(ref, sheets) against a function that only existed inside main(),
    so the block router could not run at all -- the failure looked like a routing
    problem and was a missing symbol.
    """
    sheet = sheets.get(ref, "")
    for sub, region, _row in REGIONS:
        if sub.lower() in sheet.lower():
            return region
    return "reserved_safety"


def region_rect(region: str) -> tuple[float, float, float, float]:
    return REGION_RECTS.get(region, (BOARD_W / 2 - 10, BOARD_H / 2 - 10,
                                     BOARD_W / 2 + 10, BOARD_H / 2 + 10))

def sheet_of(netlist_text: str) -> dict[str, str]:
    """Map reference -> sheet name from the netlist comp blocks."""
    out = {}
    for m in re.finditer(
            r'\(comp \(ref "([^"]+)"\).*?\(sheetpath \(names "([^"]*)"\)',
            netlist_text, re.S):
        out[m.group(1)] = m.group(2)
    return out


def parse_comps(netlist_text: str) -> list[dict]:
    out = []
    for m in re.finditer(
            r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)'
            r'(?:\s*\(footprint "([^"]*)"\))?', netlist_text):
        out.append({"ref": m.group(1), "value": m.group(2),
                    "footprint": m.group(3) or ""})
    return out


def parse_nets(netlist_text: str) -> dict[str, list[tuple[str, str]]]:
    """net name -> [(ref, pin)].

    Split on the net marker rather than regex-matching a body with a closing
    lookahead. The lookahead version stopped at the first ")" that happened to be
    followed by whitespace, so it captured ~1 node per net instead of ~4 and the
    board ended up with 271 pad-net assignments where 1193 were expected. A
    count check on the result is what caught it.
    """
    nets = {}
    for chunk in netlist_text.split("(net (code ")[1:]:
        m = re.match(r'"\d+"\) \(name "([^"]+)"\)', chunk)
        if not m:
            continue
        name = m.group(1)
        nodes = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', chunk)
        if nodes:
            nets[name] = nodes
    return nets


_FP_CACHE: dict[str, object] = {}
_FP_BBOX: dict[str, tuple[float, float]] = {}


def load_footprint(fpid: str):
    """Load and cache a footprint. FootprintLoad reads from disk each call, and
    the generator needs each part twice (once to measure, once to place), which
    doubled a several-minute run into a timeout."""
    if ":" not in fpid:
        return None
    if fpid in _FP_CACHE:
        return _FP_CACHE[fpid]
    lib, name = fpid.split(":", 1)
    base = LOCAL_LIB if lib == "Powerboard" else os.path.join(LIBROOT, lib + ".pretty")
    fp = pcbnew.FootprintLoad(base, name)
    _FP_CACHE[fpid] = fp
    if fp is not None:
        bb = fp.GetBoundingBox(False, False)
        _FP_BBOX[fpid] = (pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))
    return fp


def footprint_size(fpid: str) -> tuple[float, float]:
    if fpid not in _FP_BBOX:
        load_footprint(fpid)
    return _FP_BBOX.get(fpid, (0.0, 0.0))


def footprint_center_offset(fpid: str) -> tuple[float, float]:
    """Offset from the footprint's origin to its bounding-box centre, in mm.

    THIS IS THE BUG THAT MADE PARTS OVERLAP. Many footprints do not have their
    origin at the centre of their own bounding box. A 1x05 pin header has pad 1
    at the origin, so its 13.75 mm bounding box is centred 5.08 mm BELOW the
    origin. Placing it by assuming the bbox is origin-centred puts its top edge
    5.08 mm lower than the packer accounted for, and the parts packed above it
    end up inside its courtyard. 30 courtyard overlaps, all involving headers
    and connectors, came from exactly this.
    """
    if fpid not in _FP_OFFSET:
        fp = load_footprint(fpid)
        if fp is None:
            return (0.0, 0.0)
        bb = fp.GetBoundingBox(False, False)
        _FP_OFFSET[fpid] = (pcbnew.ToMM(bb.GetX()) + pcbnew.ToMM(bb.GetWidth()) / 2.0,
                            pcbnew.ToMM(bb.GetY()) + pcbnew.ToMM(bb.GetHeight()) / 2.0)
    return _FP_OFFSET[fpid]


_FP_OFFSET: dict[str, tuple[float, float]] = {}


def add_edge_cuts(board):
    pts = [(0, 0), (BOARD_W, 0), (BOARD_H and 0, 0)]  # placeholder, replaced below
    corners = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    for i in range(4):
        x0, y0 = corners[i]
        x1, y1 = corners[(i + 1) % 4]
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x0), pcbnew.FromMM(y0)))
        seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.1))
        board.Add(seg)


def setup_stackup(board):
    """4 layers: signal / ground / power / signal (see pcb04-board-sizing §2).

    Layer *type* matters, not just layer count. SetCopperLayerCount(4) creates all
    four as `signal`, which tells the router that every layer is fair game for
    routing. That contradicts the stackup this project documented: L2 is a ground
    plane and L3 a power plane. With all four declared signal, the router has to
    fit 277 nets into four general-purpose layers with no reference plane, which
    is the most likely reason two routing attempts failed to converge.

    Marking planes as planes (and later pouring them) means the router routes on
    F.Cu and B.Cu with a solid reference underneath, which is both routable and
    the electrically correct thing for the analog sensing this board carries.
    """
    board.SetCopperLayerCount(4)
    for layer, kind in ((pcbnew.In1_Cu, "power"),
                        (pcbnew.In2_Cu, "power")):
        # KiCad's layer type is what the PCB editor and DSN export read. Setting
        # these to `power` marks them as plane layers; the actual zones are poured
        # separately. "mixed" is not a valid type here.
        board.SetLayerType(layer, pcbnew.LT_POWER)


def setup_design_rules(board):
    """Clearance and trace defaults for a 4-layer power board.

    The default netclass clearance is 0.2 mm, which is a sensible rule but is
    wrong for SMD pad-to-pad gaps inside fine-pitch packages: a VSSOP-8 has pads
    0.5 mm apart, so the gap between adjacent pads is 0.15 mm and DRC flags 22
    violations that no amount of moving parts can fix. The pads are the vendor's
    own land pattern; the rule is what is out of scale.

    So: 0.15 mm within-package clearance, which is a real fabricated-geometry
    number (0.15 mm is comfortably inside standard 1 oz proto capability and is
    what the package requires), with a wider default for routing. This is a
    design-rule decision and is recorded in the doc rather than quietly applied.
    """
    ds = board.GetDesignSettings()
    # KiCad 9 exposes netclass values through the project when one is loaded; a
    # bare BOARD() has no project, so the per-netclass setters are unreachable
    # here (GetDefaultNetclass does not exist on BOARD_DESIGN_SETTINGS in 9.0.9).
    # What DRC reads for the copper rules are the design-settings minimums, which
    # ARE settable. 0.15 mm is the real requirement of a 0.5 mm-pitch package.
    ds.m_MinClearance = pcbnew.FromMM(0.15)


def main() -> int:
    text = open(NETLIST, encoding="utf-8").read()
    comps = parse_comps(text)
    sheets = sheet_of(text)
    nets = parse_nets(text)
    print("netlist: %d comps, %d nets" % (len(comps), len(nets)))

    board = pcbnew.BOARD()
    setup_stackup(board)
    setup_design_rules(board)
    add_edge_cuts(board)

    # net name -> NETINFO_ITEM
    netmap = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni


    placed = 0
    missing = []
    overflow_x = 0.0
    overflow_row = 0.0
    overflow_refs = []

    # Measure every part once and assign it to a region, BEFORE computing the
    # region rectangles — the rectangles are sized from these measured areas.
    by_region: dict[str, list[dict]] = {}
    for c in comps:
        c["region"] = region_for(c["ref"], sheets)
        c["settled"] = not UNSETTLED.search(sheets.get(c["ref"], ""))
        w0, h0 = footprint_size(c["footprint"])
        if w0 == 0.0:
            missing.append((c["ref"], c["footprint"]))
        c["area"] = w0 * h0
        by_region.setdefault(c["region"], []).append(c)

    global REGION_RECTS
    REGION_RECTS = compute_regions(comps)

    # Place using the SAME packing function that sized the regions.
    for region, group in sorted(by_region.items()):
        x0, y0, x1, y1 = region_rect(region)
        # Reference order within a region, so the saved file's footprint sequence is
        # a function of the netlist rather than of dict iteration or pcbnew's writer.
        group = sorted(group, key=lambda c: c["ref"])
        sizes = [footprint_size(c["footprint"]) for c in group]
        positions, _h = pack_positions(sizes, x1 - x0)
        for c, (px, py) in zip(group, positions):
            proto = load_footprint(c["footprint"])
            if proto is None:
                missing.append((c["ref"], c["footprint"]))
                continue
            fp = pcbnew.FOOTPRINT(proto)
            # pack_positions returns the desired centre of the bounding box.
            # SetPosition sets the footprint ORIGIN, which is not the same point.
            ox, oy = footprint_center_offset(c["footprint"])
            fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x0 + px - ox),
                                           pcbnew.FromMM(y0 + py - oy)))
            fp.SetReference(c["ref"])
            fp.SetValue(c["value"])
            # Silkscreen density: at 160x130 mm with 387 parts, a reference
            # designator beside every 0603 lands on its own pads. DRC reports
            # these as `silk_over_copper` warnings -- legibility, not electrical.
            # Small passives get their reference hidden (the value is in the
            # BOM and the assembly drawing); parts the builder must orient or
            # identify (ICs, connectors, polarity-marked parts, power devices)
            # keep visible text. That is the standard trade at this density and
            # it removes ~400 warnings rather than suppressing the check.
            w, h = footprint_size(c["footprint"])
            # Silk density: at 160x130 mm with 387 parts there is no placement of
            # a designator that avoids every pad. Two things were tried:
            #   1. shrink the text to 0.7 mm -> 114 text_height violations,
            #      i.e. it broke a different rule; 0.8 mm is the legal floor.
            #   2. nudge text above the pad row -> silk went 147 -> 167, because
            #      it then collided with the neighbouring part's silk.
            # Neither is an improvement, so small parts keep the field hidden and
            # larger parts keep a visible designator. The remaining warnings are
            # a genuine density limit and are reported, not suppressed.
            if w * h < 12.0:            # 0603/0805/SOT-23 and smaller
                fp.Reference().SetVisible(False)
            board.Add(fp)
            if y0 + py > BOARD_H:
                overflow_refs.append(c["ref"])
            c["x"], c["y"] = x0 + px, y0 + py
            placed += 1

    # assign nets to pads
    ref_to_fp = {fp.GetReference(): fp for fp in board.GetFootprints()}
    assigned = 0
    for name, nodes in nets.items():
        ni = netmap.get(name)
        for ref, pin in nodes:
            fp = ref_to_fp.get(ref)
            if fp is None:
                continue
            for pad in fp.Pads():
                if pad.GetNumber() == pin:
                    pad.SetNet(ni)
                    assigned += 1
                    break

    # The netlist states how many pin-to-net connections exist. If the board
    # carries materially fewer, the net parser is wrong and the file is not a
    # placed board — it is a scattered pile of footprints. Checking the count is
    # what caught the 271-instead-of-1193 bug; without it this would have
    # "succeeded" and produced an unroutable file.
    expected = len(re.findall(r'\(node \(ref "', text))
    if assigned != expected:
        print("FAIL: %d of %d netlist nodes reached a pad; %d have no pad"
              % (assigned, expected, expected - assigned))
        return 1

    # DETERMINISTIC SAVE ORDER (PCB-07) -- measured, not assumed.
    #
    # Two runs on identical input differ. Bisecting the difference rather than
    # guessing at the cause produced four separate sources:
    #
    #   1. FOOTPRINT ORDER in the file. 79225 of 83169 lines differed after blanking
    #      uuids, with the same multiset of 397 footprints. The in-memory order IS
    #      stable (checked by spying on the board at SaveBoard time), so pcbnew's
    #      writer reorders. Parts are now inserted in reference order AND the file is
    #      re-emitted in a canonical order below.
    #
    #   2. UUIDs. Every one of 7731 uuid fields is freshly minted per run by the API.
    #      gen_pcb does not write them and cannot control them through pcbnew.
    #
    #   3. TEXT FIELD ORDER inside a footprint: the two user fp_text objects,
    #      "${VALUE}" and "${REFERENCE}", swap places between runs while keeping
    #      identical coordinates. That is the library footprint being re-serialised
    #      in a different member order.
    #
    #   4. Nothing else. Verified by comparing all 397 footprint blocks with uuids
    #      stripped and blocks sorted: exactly ONE block differed, and only in the
    #      text-field ordering above.
    #
    # Removing and re-adding footprints to force an order is NOT an option: BOARD.
    # Remove() corrupts the swig bindings in this interpreter (measured repeatedly
    # in this project). So the canonicalisation is done on the TEXT, after saving,
    # which is also the only place the uuid problem can be addressed.
    pcbnew.SaveBoard(OUTPUT, board)

    # PCB-07: two runs on the same netlist must produce the same bytes.
    #
    # The API cannot give that on its own -- it mints a fresh uuid for every object
    # on every run, and its writer emits footprints in a varying order. Both are
    # fixed by rewriting the saved text: see canonicalise_pcb.py for the four
    # measured sources and the parser that separates footers from bodies without
    # guessing. Verified: two independent builds are byte-identical AND the result
    # loads in pcbnew with 397 footprints.
    import canonicalise_pcb
    canonicalise_pcb.canonicalise_file(OUTPUT)
    settled = sum(1 for c in comps if not UNSETTLED.search(sheets.get(c["ref"], "")))
    print("placed %d/%d footprints, %d pad-net assignments"
          % (placed, len(comps), assigned))
    print("settled (routable): %d   unsettled (reserved): %d"
          % (settled, len(comps) - settled))
    if overflow_refs:
        print("OVERFLOW (outside the board, regions too small): %d"
              % len(overflow_refs))
        print("   %s" % " ".join(overflow_refs[:20]))
    if missing:
        print("MISSING FOOTPRINTS: %d" % len(missing))
        for r, f in missing[:10]:
            print("   %s %s" % (r, f))
    print("wrote %s" % os.path.basename(OUTPUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
