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

## 6z. The stackup defect behind the routing failures

`SetCopperLayerCount(4)` creates **all four layers as `signal`**. The documented
stackup is signal / **ground** / **power** / signal, so the board file
contradicted its own spec from the moment it was generated.

Consequences, in order of severity:

1. **No ground reference anywhere on the board.** Every analog block — the CSA
   sense chains, the OC window comparators, the FSR frontends — was placed on a
   board with no plane under it. That is not a routing nuisance; it is the thing
   the whole ±3 % VREF assumption in the OC-03 envelope depends on.
2. **The router was told all four layers are fair game**, so it had to fit 277
   nets into four general-purpose layers with no plane to escape onto. Both
   failed attempts (1800 s, then 1117 s) are consistent with that.

Fixed with `SetLayerType(In1_Cu, LT_POWER)` and the same for In2. Verified at
the DSN boundary rather than trusted at the API:

```
(layer In1.Cu
  (type power)
  ...
```

So the correction reaches the router, not just the `.kicad_pcb`.

Two API notes worth keeping, because both cost time:
- `SetLayerType` is a **BOARD** method; it is not on `BOARD_DESIGN_SETTINGS`. An
  early probe used the settings object, found nothing, and wrongly concluded the
  call did not exist.
- `LT_POWER == 1`. Without checking, `GetLayerType` returning `1` looks like an
  error code rather than "power".

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

## 6b. The router was not too slow — it was memory-starved

Three full-board routing attempts failed (1800 s at 100 passes, 1117 s at 8, then
1200 s at 6). Cutting the pass count never helped, which was the clue: if passes
were the problem, fewer passes would have finished sooner.

Feasibility test: the same board reduced to **12 components routes in 5.21
seconds** with `incomplete connections: 0, clearance violations: 0`. So
FreeRouting works, the DSN is valid, and the geometry is routable.

The router's own log gave the rest:

```
using 7.47 total CPU seconds, 2.85 GB total allocated,
330.5 MB peak heap usage
```

and at startup it reports `1024 MB RAM`. The launcher is:

```
exec java -Djava.awt.headless=true -jar freerouting-2.5.0.jar ...
```

**No `-Xmx`.** The JVM therefore picks an ergonomic default, and on this host that
default is exactly `MaxHeapSize = 1073741824` — 1 GB. FreeRouting is
memory-bound at 397 parts, not pass-bound.

The host has **7.4 GB total, 4.6 GB available**. `route_pcb.py` now invokes the
jar directly with `-Xmx5g` (`FREEROUTING_HEAP`), falling back to the wrapper with
a printed warning if java or the jar is missing — so a fallback run is never
mistaken for a fixed one.

**The heap fix did not solve it.** A fourth run with `-Xmx5g` confirmed live in
the process table (`Xmx5g`) still timed out at 1500 s with no session file.

So the 1 GB default heap was a **real defect** — an ergonomic JVM default
starving a 397-part route — but it was **not the binding constraint**. This
section originally presented it as the answer, which was wrong; the correction is
recorded rather than edited away because "found a plausible cause" and "found the
cause" are different claims and only the second one earns a fix.

Four attempts: 1800 s @ 100 passes, 1117 s @ 8, 1200 s @ 6, 1500 s @ 15 with 5 GB.
Every one produced no SES.

## 6c. Scale, measured

Rather than adjust the timeout a fifth time, a scaling test against slices of the
real board:

| Parts | Result | Time |
|---|---|---|
| 12 | routed, 0 incomplete, 0 clearance | **5.21 s** |
| 80 | routed, 0 incomplete, 0 clearance, 744 track segments | **2 min 45 s** |
| 397 | no session file, four attempts | > 20 min each |

That is the answer to "is it memory or is it scale": **it is scale**, and the
curve is steep. 80 parts already takes 165 s; the full board is five times the
parts and adds the two 100 V bridges, the DRV8353 gate loops and the dense
decoupling fields. Nothing in the 80-part run suggests it was near a resource
ceiling — it reported 0 clearance violations throughout and finished normally.

Practical consequence: **the router is not broken and the board is not unroutable
one block at a time.** The full-board single-shot autoroute is the wrong tool at
this size, and four timeouts were spent learning that.

What this does not yet prove: that the blocks will join up. Routing 80 parts in
isolation is easier than routing them with the other 317 nets demanding space.
Block routing needs the inter-block nets handled deliberately, not by luck.

**The lesson worth keeping:** three failed runs were diagnosed as "too much
routing for the pass budget" because that is what the symptom looked like. The
measurement that settled it was a deliberately tiny board — if 12 parts route in
5 seconds and 397 time out, the problem is scale, and the next question is *which*
resource, which the router's own log answered.

## 6d. Block routing: routed, with the inter-block gaps left open

Route the board one functional block at a time, merge the tracks. 15 blocks:

| Block | Parts | Segments | | Block | Parts | Segments |
|---|---|---|---|---|---|---|
| mcu | 19 | 219 | | fsr_left | 17 | 147 |
| analog_filter | 15 | 52 | | fsr_right | 17 | 120 |
| fault_logic | 29 | 387 | | aux_supply | 9 | 55 |
| gen_sense | 21 | 225 | | rail_partition | 43 | 456 |
| hub_sense | 21 | 232 | | brake_chopper | 13 | 149 |
| oc_window | 5 | 4 | | brake_left | 6 | 35 |
| ov_chopper | 14 | 121 | | brake_right | 6 | 28 |
| hall | 27 | 210 | | | | |

**2708 items merged (2428 tracks + 280 vias), 0 unmatched nets.**

DRC on the merged board: **177 violations, 418 unconnected** — down from 499
unconnected on the unrouted board, and 199 dangling tracks eliminated.

### The two bugs that made the first merge a no-op

**Bug 1 — net codes are not portable.** Removing footprints from a sub-board
deletes nets that lost all their pads and *renumbers the survivors*, so block net
37 is not master net 37. The first merge drew 2428 tracks that were every one
dangling, and DRC still said 499 unconnected. **That number being identical to
the unrouted board is what gave it away** — real routing cannot leave the count
unchanged. Fixed by carrying the net *name* and matching through
`NetsByName()`.

**Bug 2 — vias were dropped.** FreeRouting routed on all four layers (this was
before In1/In2 were marked as planes), so it changed layers through vias. The
harvest loop skipped everything that was not `PCB_TRACE_T`, discarding every via.
F.Cu and In1.Cu tracks then met at a point with nothing between them. DRC's
wording — *"Track has unconnected end"* — pointed at a missing interconnect
rather than a missing track, which is what identified it. Carrying vias took
unconnected from 499 to 418 and dangling from 199 to 0.

### What the remaining 418 actually are — corrected

The first version of this section said all 418 were inter-block gaps. **That was
wrong**, and the correction matters because it changes what work is left.

Splitting the 418 by whether their nets are entirely inside settled blocks:

| Category | Count |
|---|---|
| Involve a net that touches an excluded block | **375** |
| Entirely within settled nets (real inter-block gaps) | **43** |

So the bulk is the deliberately-excluded power-stage circuitry, not merge gaps.
Named evidence for the first row: `PRE_SOURCE` (6 refs, **6 on unsettled
sheets**), `Q403_GATE` (3 refs, 3 unsettled), `CTRL3V3` (10 refs, 10 unsettled).
Those nets were never in scope for autorouting, so their being unconnected is
expected rather than a failure of the merge.

The **43** real gaps are exactly what they should be — signals that necessarily
cross block boundaries:

- **SPI to the drivers:** `DRV_MOSI`, `DRV_SCK`, `DRV_MISO`
- **Gate drives:** `GEN_INHA/INHB/INHC`, `GEN_INLA/INLB/INLC`, and the six HUB
  equivalents (12 nets at 2 gaps each)
- **Sensing:** `GEN_SOB/SOC`, `HUB_SOA/SOB/SOC_ADC`, `OC_HIGH_REF`, `OC_LOW_REF`
- **Inputs:** `GEN_HALL_1..3`, `HUB_HALL_1..3`, `ENC_A`, `ENC_B`,
  `LEFT_FSR_ADC`, `RIGHT_FSR_ADC`
- **Control:** `OC_OK`, `MCU_ARM`, `ARM_CLEAN`, `RESET_REQUEST`, `WDI`,
  `TIMER_BREAK_OK`, `FSR_SAMPLE_ENABLE`, `BRAKE_DUMP_PWM`

That is a finite, named list of 43, which is a tractable target: route them
explicitly on the merged board, or route overlapping block pairs that contain
both ends.

### Attempted: routing the 43 separately. It made things worse.

The 40 nets that exist as pads (43 minus 3 that are net-name variants) were
extracted into a sub-board with every non-target pad cleared, leaving 141 target
pads. FreeRouting converged well on that problem -- **score 973.60, 2 unrouted,
0 violations** -- and produced 820 segments. Merging them onto the routed board
gave 3528 items total, 0 unmatched nets.

DRC then got **worse**:

| Metric | Before | After |
|---|---|---|
| unconnected | 418 | **368** (better) |
| clearance | 27 | **365** |
| shorting items | 0 | **199** |
| tracks crossing | 0 | **180** |
| hole-to-hole | 0 | 21 |

**Why: the inter-block pass was routed blind to the existing copper.** The
prepare step cleared non-target *pads* so the router would not try to connect
them, but the router had no knowledge of the 2708 tracks already on the board, so
it drew new tracks straight across them. Named example: a 42.8 mm `GEN_INLC` track
on In1.Cu shorting against both `RESET_INV` and `MCU_VDDA`.

The router's own "0 violations" is therefore not evidence of a clean result -- it
was clean *in a world where the other 2708 tracks did not exist*. A sub-board
approach only works if the existing copper is represented in it, which means
importing the merged tracks into the sub-board before routing, or routing on the
merged board itself.

`powerboard-reva-routed-v2.kicad_pcb` is therefore an **intermediate artifact, not
an improvement on v1**. v1 remains the better board.

### Three more attempts at making the copper visible to the router

All three failed, and each failure is recorded because each looked reasonable.

**Keepout cells.** Delete non-target tracks but leave circular keepout zones where
they were, so the router must go around them. Crashed: `ZONE(board)` plus
`SetOutline()` on a loaded board dumped core (`timeout: the monitored command
dumped core`). Zone construction through this API on an already-populated board
is not reliable.

**Netless tracks as obstacles.** Keep the tracks but clear their net codes, so
they are copper with no connection target. `SaveBoard` wrote a file that
`LoadBoard` then **returned `None` for** -- the board was destroyed on save, and
`ExportSpecctraDSN` failed on it. A board file that will not reload is worse than
no file.

**Full DSN with the optimizer disabled.** Export the routed board so all 2708
tracks are present as wires, and route with `--router.optimizer.enabled=false`
intending gap-fill only. This one is the most promising: FreeRouting reports a
**baseline of 545 unrouted items**, i.e. it now sees the real problem rather than
an empty board. It did not finish inside 20 minutes.

### Where that leaves it

The correct approach is established even though it is not complete: **the router
must be given the existing copper, and told not to optimise.** Earlier attempts
failed either by hiding the copper (199 shorts) or by letting the optimizer
rewrite all 2708 tracks (endless `normalizeTraces` oscillation warnings on
`OC_HIGH_REF`, `LOGIC3V3_EXT`, `LEFT_SWITCH_ADC`).

What is not established is that gap-fill converges in reasonable time on a board
this size. That is the open question, and it needs an unattended run rather than
another iteration of guessing.

Also still absent by intent: the **GEN and HUB power stages** are not autorouted.
Their loop geometry is what the OC-03 envelope assumes.

## 7. What PCB-04 still owes

1. Routing, which is the bulk of the work and cannot start on the 150 unsettled
   components until their topology is decided.
2. Gerber generation and a fab-capability check.
3. The board envelope confirmed against the physical bike.
