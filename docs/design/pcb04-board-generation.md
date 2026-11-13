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

## 4a. Does the 0.15 mm rule violate G5's "no automatic relaxation"?

`pcb-quality-gates.md` G5 says: *"No automatic relaxation of rules to obtain
green."* The pad-clearance rule above is a relaxation, so it has to be tested
against that clause rather than assumed compliant. Three things distinguish it:

1. **It is not automatic.** It lives in a reviewed file, applies to one
   condition (`Pad` vs `Pad`), and states its reason inline. G5 targets rules
   being loosened by a script until DRC passes.
2. **It is not to obtain green.** The 22 violations it removes are geometry the
   vendor's land pattern requires; the board is not "passing" anything that was
   previously a real risk. If a pad pair were genuinely too close for fabrication,
   this rule would hide it — so the constraint is checked independently below.
3. **It is bounded to 0.15 mm and to pads.** Routing copper keeps 0.2 mm. No
   other constraint is touched.

The independent check that the rule is not hiding a real risk: the tightest pad
gap on the board is measured directly, per package, and compared against a
stated fabrication floor (0.15 mm for 1 oz proto). If any pair were tighter than
0.15 mm, it would be a genuine defect that this rule would mask — so the check
must be:

```
min over all (pad, pad) pairs on the same layer of (gap) >= 0.15 mm
```

**Measured.** Independent sweep over all 1208 named pads, every pair on a shared
layer with different nets, using axis-aligned bounding-box gaps:

**minimum pad-to-pad gap between different nets = 0.1500 mm**, at U7 pads 1
(`RESET_INV`) and 2 (`SAFETY3V3`) — that is, exactly the VSSOP-8 the rule was
written for, and exactly the value the rule declares.

So the rule is not masking anything. The tightest gap on the board equals the
rule's floor to four decimal places, and no pair is closer. Had any pair been
tighter than 0.15 mm, this sweep would have found it and the rule would have been
hiding a genuine defect.

One false start worth recording: the first sweep reported a minimum of **0.0000
mm** on Q13 (TDSON-8), where pad 5 (`DUMP_LOW`) shares a rectangle with the
unnamed exposed-pad aperture. Those unnamed pads are paste/thermal apertures of
the same tab, not separate nets — the sweep now skips pads with no number, since
a pad with no net cannot be a clearance risk between nets. Counting them would
have reported a short that does not exist.

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

## 6a. Routing: first attempt timed out, and that is a finding

The first FreeRouting run used `-mp 100` (100 optimisation passes) and was killed
by a **1800 s timeout without producing a session file.** 387 parts, 271 nets and
four layers is simply a lot of routing for one pass budget, and the router keeps
optimising rather than stopping at "connected".

What that means concretely: **no tracks exist.** The board is still at the placed
state, not a partially-routed one — a timeout with no SES means nothing was
written, not that some nets got done.

The pipeline now bounds the attempt (`FREEROUTING_PASSES`, `FREEROUTING_TIMEOUT`)
so a run either produces a session or fails inside a known window, and reports
whether an SES exists on failure. An unbounded wall clock on a router is not a
plan.

Two things this rules out as causes, checked before blaming the router:
- The DSN exports cleanly at 178 KB with all 271 nets, so the input is well formed.
- The board passes its own geometric placement checks with zero courtyard
  overlaps, so the router is not fighting a pile of overlapping parts.

The remaining unknown is whether the board is *routable* at 4 layers with this
part density, which only a completed run will answer. If bounded runs also fail,
the options are more layers, a larger board, or manual routing of the power stage
with autorouting only for the analog blocks.

## 7. What PCB-04 still owes

1. Routing, which is the bulk of the work and cannot start on the 150 unsettled
   components until their topology is decided.
2. Gerber generation and a fab-capability check.
3. The board envelope confirmed against the physical bike.
