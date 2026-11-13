# Board generation: what the PCB actually is, and what it is not

STATUS: `PARTIAL_NOT_SAFE_TO_ENERGIZE`. A real `.kicad_pcb` exists and DRC runs
against it. It is **placed but not routed**, and 150 components sit in circuits
the schematic itself does not consider settled.

## 1. What exists

`gen_pcb.py` reads `exports/powerboard-reva.net` and writes
`powerboard-reva.kicad_pcb` using KiCad's own `pcbnew` module (system
`/usr/bin/python3`, KiCad 9.0.9 — `pcbnew` is not available to the 3.11 venv).

| Property | Value |
|---|---|
| Footprints placed | **387 / 387** |
| Pad-net assignments | **1193 / 1193** (exact parity, gate-enforced) |
| Board | **160 × 130 mm**, 4 copper layers |
| Components off-board | **0** |
| DRC violations | **147**, all silkscreen warnings, **0 errors** |
| Unconnected items | 499 (no tracks routed yet) |

Balloon-fresh writes `.kicad_pcb` S-expressions by hand. This uses `pcbnew`
instead: the library loads footprints, the API assigns pads, and `kicad-cli drc`
reads a file KiCad itself wrote. One less thing to be subtly wrong.

## 2. Six generator bugs, and the check that caught each

Every one of these produced a file that *looked* fine.

1. **Net parser truncated at the first `)`** — captured ~1 node per net instead
   of ~4. Board had **271** pad-net assignments where 1193 were expected. Caught
   by comparing against the netlist's own node count; now a hard equality gate.
2. **Footprint cache returned one shared object.** `FootprintLoad` returns the
   same instance per library id, so adding it twice put *the same* footprint on
   the board twice and `SetReference` overwrote earlier references. **294/1193.**
   Fixed with `pcbnew.FOOTPRINT(proto)` per placement.
3. **Overflow fallback parked parts at one point** — four resistors at identical
   `(x, y)`, **199 courtyard overlaps**.
4. **Region rectangles hand-drawn by eye** — 91, then 124 parts off-board, while
   total area demand (123.6 cm² at 55 % packing) was well inside the 192 cm²
   board. Replaced with area-derived, largest-first packing.
5. **Region height estimated from area, not measured packing.** The estimate was
   optimistic, regions overflowed, and the fallback then *grew a region into its
   neighbour*. Fixed by making sizing and placement call **one function**
   (`pack_positions`); they can no longer disagree.
6. **Footprints are not origin-centred.** A 1×05 pin header has pad 1 at the
   origin, so its 13.75 mm bounding box is centred **5.08 mm below** it. Placing
   by bounding-box centre put every header ~5 mm lower than the packer assumed.
   This single bug caused **all 30 courtyard overlaps** (J9/J10/J11 with their
   own resistors). Fixed with `footprint_center_offset()`.

Bug 6 is worth dwelling on: the symptom (a resistor overlapping a header) looked
like a packing problem and was chased as one through three rewrites. The actual
cause was a coordinate convention. What found it was computing the overlap
geometry independently instead of trusting DRC's report.

## 3. On trusting DRC

Early on, DRC reported 25 courtyard overlaps including J11 against C410 — parts
whose **pads are 52.86 mm apart**. Extracting the same three footprints into a
fresh board gave **zero** overlaps, and an independent geometric sweep of the
real board found 30 *different* pairs. DRC over-reported some pairs (repeatedly)
and under-reported others.

So the generator's placement is verified by an **independent geometric check**
(courtyard rectangle union), not by reading DRC totals. DRC is still the
authority for copper clearance; it is not the authority for courtyard truth at
this part count.

## 4. Design-rule decision: 0.15 mm pad clearance

`powerboard-reva.kicad_dru` relaxes copper clearance to **0.15 mm for pad-to-pad**
only. Reason: the VSSOP-8 packages (U7, U8, U12) have 0.5 mm pitch with 0.3 mm
pads, so adjacent pads are 0.15 mm apart *by the vendor's own land pattern*. No
placement can change that. This cleared **22 violations that were rule-scale
errors, not layout defects**. 0.15 mm is fabricable on standard 1 oz prototype.
Routing copper keeps the 0.2 mm default. Nothing else is loosened.

## 5. Silkscreen: a genuine density limit, reported not suppressed

The remaining **147** violations are all silkscreen. Two fixes were attempted:

- **Shrink reference text to 0.7 mm** → created **114 `text_height` violations**.
  0.8 mm is the legal floor; the fix broke a different rule.
- **Nudge text above the pad row** → silk went **147 → 167**, because the text
  then collided with the neighbouring part's silk.

Neither improved anything, so the change was reverted and the warnings stand.
Small parts (area < 12 mm², i.e. 0603/0805/SOT-23) have their designator hidden;
larger parts keep a visible reference. At 387 parts on 160 × 130 mm this is the
density limit, and stating that is more useful than a suppressed check.

## 6. What this is not

- **Not routed.** 499 unconnected items are the absence of tracks.
- **Not fab-ready.** No Gerbers generated; 150 components belong to circuits the
  schematic marks unqualified/inhibited and are placed in reserved zones.
- **Not DRC-clean.** 147 silk warnings remain.
- **The 160 × 130 mm envelope is provisional.** Derived from measured footprint
  area, but never checked against bike mounting or thermal requirements.

## 7. What PCB-04 still owes

1. Routing, which is the bulk of the work and cannot start on the 150 unsettled
   components until their topology is decided.
2. Gerber generation and a fab-capability check.
3. The board envelope confirmed against the physical bike.
