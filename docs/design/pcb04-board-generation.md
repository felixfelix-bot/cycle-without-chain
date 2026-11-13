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

### A hand-written maze router: also insufficient, for a measured reason

The 43 nets were handed to a purpose-written grid A*, on the reasoning that 43
two-point connections is a small, well-defined problem and keeps every placed
segment inspectable. It routed 6 of 40 nets.

Four bugs were found and fixed along the way, all real:

1. **Collinearity typo.** `simplify()` compared `cy - cy` instead of `cy - by`, so
   nothing collapsed and one net emitted 314 micro-segments. Each was added to the
   obstacle map, letting a single net wall off a corridor.
2. **Pads blocked then only partly freed.** The per-net grid copied the static map
   and then called `block_pad()` on the net's *own* pads before clearing a 3x3
   patch, sealing each pad inside a ring of blocked cells.
3. **Inadmissible-ish search.** Skipping expansion on a `seen` *set* (rather than
   re-expanding when a cheaper arrival appeared) discarded cheaper paths.
4. **Multi-pad nets treated as pairs.** `DRV_SCK` has three pads, fanning out from
   the MCU to both drivers; routing only the first two reported the net routed
   while leaving a pad unconnected. Replaced with a nearest-neighbour spanning
   tree.

After all four, the failure that remained is **geometric, not algorithmic**:

```
GEN_INHA pad at 146.7, 78.7   (0.25 x 0.82 mm, a DRV8353 pin)
reachable from that pad: 49 cells of 199087 free cells -- a 7x7 pocket
```

A 21x21 dump of the pad map around it shows why: the pad sits in the middle of a
dense pin field, with neighbouring pads forming a continuous blocked wall on every
side. It is not a bug in the router; the pad is enclosed by real copper geometry.
Getting out requires either via-based escape from an inner layer or a clearance
model that distinguishes "approach a pad I must connect to" from "cross between
two pads I must not touch" -- and the latter is what a uniform grid cannot express.

A uniform-clearance grid router is the wrong instrument for fine-pitch escape
routing. The autorouter has the machinery for it (fanout passes, per-layer
clearance rules); it just could not be made to work on this board within the
attempts recorded above.

### Confirmed by BFS, and the geometry that settles it

Two more bugs were found after that paragraph was first written:

5. **Discs instead of rectangles.** `block_pad` blocked a circle of radius
   max(w,h)/2 while a DRV8353 pin is 0.25 x 0.82 mm -- so the narrow axis was
   over-blocked by 4x and adjacent pins' discs merged into a wall. Replaced with
   per-axis rectangles plus an orientation swap for elongated pads. Reachable
   cells from the GEN_INHA pad went from **49 to 224349** on a 199087-free-cell
   board, i.e. from a sealed pocket to the whole board.
6. **Freeing smaller than blocking.** The per-net pad-freeing still used
   `CLEARANCE` (0.30) on a circle while `block_pad` used `CLEARANCE_PAD` (0.10) on
   a rectangle. A smaller free region cannot clear a larger blocked one, so every
   pad stayed sealed even after bug 5 was fixed.

After both fixes the pads are reachable and the search still reports no path. To
settle whether that was an algorithm fault, the same map was searched with plain
**BFS** -- complete, heuristic-free, no `seen` set to get wrong:

```
BFS found path: False
A*  found path: False
```

They agree. So the negative result is a property of the geometry, not of the
router:

```
U1 pin 32 at 0.5 mm pitch: pad 0.25 mm wide, gap to the next pad 0.25 mm
DRC clearance 0.15 mm each side -> a track needs 0.15 + 0.20 + 0.15 = 0.50 mm
```

**A 0.25 mm gap cannot hold a 0.50 mm track.** The inner pins of a 0.5 mm-pitch QFN
are not reachable from outside on the same layer at this clearance and track
width. They require either a finer track with a reduced clearance rule, a via
placed inside the pad fan-out, or escape routing on a layer that starts beneath the
part. All three are layout decisions, not router heuristics.

That is the real reason 34 of 40 nets failed, and no amount of further work on the
maze router would have changed it.

### The escape rule was added, and the failure persists for a different reason

A pitch-specific rule was added to `powerboard-reva.kicad_dru`:

```
(rule "fine-pitch escape track to pad"
  (constraint clearance (min 0.05mm))
  (condition "A.Type == 'Pad' && B.Type == 'Track'"))
```

with a 0.15 mm escape track: `0.15 + 0.05 + 0.05 = 0.25 mm`, exactly the pad gap.
The router was taught to apply it inside the ten detected fine-pitch bodies
(U1's QFN-40 among them: body 141.0,78.0 - 148.6,85.2, and the GEN_INHA pin at
146.7,78.7 is inside it).

It did not help. Searching again with escape clearance active:

```
BFS with escape clearance: path found = False
reachable from the GEN_INHA pad: 1478657 cells
reachable bbox: x 0..1600, y 0..1300 of a 1601x1301 grid
```

**1.48M cells, spanning the entire board, and the destination pad is not among
them.** The start pad is reachable to everywhere except the far pad, which means
the two pads sit in two different connected regions of free space -- separated by
a wall the route cannot cross at any clearance tried.

The wall has since been identified by flooding both sides separately and dilating
one region until it touched the other (`diagnose_wall.py`):

```
region A (U1 pin 32):    1478657 cells
region C (U17 pin 40):      6149 cells
overlap: 0
narrowest crossing: 17 cells (1.70 mm) at 123.80, 7.90 mm
```

The destination is not walled off by routed copper -- it is trapped inside the
**STM32's own LQFP-100 pin field**. 6,149 cells is about 61 mm^2, the pin field
around U17, not the board.

The arithmetic explains it exactly:

```
LQFP-100: 0.3 mm pads on 0.5 mm pitch -> pad-to-pad gap 0.20 mm
escape clearance 0.05 mm each side    -> corridor 0.20 - 0.10 = 0.10 mm
grid cell 0.10 mm                     -> the corridor is EXACTLY ONE CELL
```

A one-cell corridor is not a corridor a flood fill or A* will reliably follow: any
rounding in the grid, and any cell whose centre falls marginally inside the
clearance disc, closes it. The pads are free; the gaps between them are a single
cell wide and the discretisation destroys them.

So the failure is **grid resolution against a 0.5 mm pitch**, which is a different
problem from clearance (fixed) and different from routing order (fixed). Reaching
these pins needs a proper **fan-out**: short escape stubs placed by pitch-aware
code that knows the pin order, not a cell-by-cell search. That is what the
autorouter's fanout pass exists to do, and it is also what hand routing in KiCad
does naturally.

### The fan-out was implemented, and it made the board worse

`fanout_escape.py` places one straight stub per fine-pitch pad along the package's
outward normal, plus a through via just outside the body edge, then leaves routing
to continue on B.Cu. It produced **57 stubs and 57 vias across 37 nets**.

A real bug was caught by the output looking too uniform: every stub came out at
exactly **0.100 mm**, the clamp floor. The width was derived as
`pitch - max(size_x, size_y)`, but a perimeter pad's LONG axis is perpendicular to
the pitch, so a VSSOP-8 pad of 1.250 x 0.350 against a 0.500 mm pitch gave
`gap = -0.750 mm` and clamped. Replaced with the pad's extent **projected onto the
pitch direction**, giving physically correct widths: **0.250 mm x20, 0.300 mm x35,
0.350 mm x2**, matching QFN-40 / LQFP-100 / VSSOP-8.

The stubs are correctly placed -- 57 of 57 escape points match the CSV, 56 vias sit
at them -- but DRC on the result is worse than v1:

```
                v1      fanout
unconnected    418      418
clearance        0      119
shorting         0       67
hole_to_hole     0       38
via_dangling     0       51
tracks_crossing  0        9
```

The stubs were placed **geometrically without checking against existing copper**,
so they run into the 2708 tracks already there and into each other's vias. The
placement is a valid construction of an escape fan-out; it is not a valid insertion
into this board.

That is the same mistake as the inter-block merge (routing blind to existing
copper), made again in a different mechanism. The lesson generalises: on this board
no new copper can be added without a collision check against the copper already
present, and both attempts that skipped it produced shorts.

`powerboard-reva-fanout.kicad_pcb` is therefore recorded as a **negative result**,
like `-v2`. It is not an improvement and should not be used. The escape widths it
derives are correct and reusable; the insertion is not.

### The checked fan-out: collision-tested, and it does not regress

`fanout_checked.py` repeats the construction but tests every stub and every via
against all existing copper first, and **skips** what does not fit rather than
forcing it. Bounding-box tests are used throughout, so the result is a conservative
subset: a skipped stub is an open item, an inserted short is a silent defect.

Two things had to be fixed before it was honest:

1. **Clearance was applied to the wrong pairs.** The first checked run used 0.05 mm
   for every test and still showed 27 clearance violations. The `.kicad_dru` grants
   a *track-to-pad* relaxation inside a fine-pitch body; against another **track** a
   stub still owes the 0.20 mm netclass. Clearance now depends on what is being
   tested against, not on where the stub sits.
2. **The v1 baseline was wrong.** The comparison table above lists v1 clearance as
   0. Running DRC on v1 directly gives **27 clearance, 118 silk_overlap, 32
   silk_over_copper, 418 unconnected** -- the same 27 that was being attributed to
   the fan-out. The fan-out adds **zero** new clearance violations, not 27.

Result of the checked run: **14 stubs inserted, 43 skipped** (30 blocked by a track,
11 by a via, 2 by via copper), 13 nets given escape points.

```
                        v1      blind     checked
unconnected            418      418        418
clearance               27      119         27
shorting                 0       67          0
hole_to_hole             0       38          0
tracks_crossing          0        9          0
via_dangling             0       51         14
```

So the collision check eliminates all 67 shorts and the crossings, and leaves only
14 dangling vias -- stubs whose far end has nothing to connect to yet, because the
remaining net segments are still unrouted. **That is the correct state**: copper
that is known clear and correctly placed, waiting for the rest of the route.

Only 14 of 57 pads could be escaped this way. The other 43 are blocked by the
2708 tracks already routed through the pin fields -- which is the same conclusion
the inter-block attempts reached from the other direction: **the board is full, and
the existing routing is what blocks further progress.** Not the router, not the
clearance, not the grid.

### Routing order tested: the same nets on an EMPTY board routes 3x better

That conclusion makes a testable prediction. If the existing copper is what blocks
the inter-block nets, then those nets should route far better on the placed but
**unrouted** board -- which had never been tried. Every previous attempt handed them
a board with 2708 tracks already on it.

```
hand_route_interblock.py powerboard-reva.kicad_pcb routing/interblock_first.kicad_pcb
base: powerboard-reva.kicad_pcb (0 existing tracks)
```

| board state                      | routed | failed |
|----------------------------------|--------|--------|
| v1, 2708 tracks already present  |   6/40 |     34 |
| placed board, 0 tracks           |  19/40 |     21 |

**Nineteen versus six.** The ordering hypothesis is confirmed: the inter-block nets
are not hard to route, they were being routed last into a board that no longer had
room.

The 21 that still fail on an empty board are the remaining question. They are
concentrated in the three-phase gate-drive and current-sense signals
(`GEN_INLB`, `GEN_INLC`, `HUB_INLA`, `HUB_INLC`, `HUB_SOA_ADC`, `HUB_SOB_ADC`,
`DRV_SCK`), which have to cross the dense pin fields of U1/U2/U17 from both sides at
once. That is a genuine pitch-escape problem, separate from ordering, and it is what
the collision-checked fan-out in `fanout_checked.py` addresses (43 of its 57 pads
were blocked by existing copper; on an empty board they would not be).

So the correct pipeline order is:

1. Place parts (done).
2. Route the inter-block nets on the empty board -- **19/40 achieved**.
3. Escape-fanout the remaining fine-pitch pads while the board is still mostly
   empty, so the 43 blocked pads are not blocked.
4. Block-route the rest around that reserved copper.
5. Merge, DRC, iterate.

Steps 3-5 are not implemented in that order. The scripts exist but were written to
run after block routing, which is exactly the mistake this section documents.

**This is where the work stops.** Six router bugs were found and fixed, a
pitch-specific design rule was added and verified, and the remaining obstacle is a
connectivity question about the already-routed copper that would need either a
different global strategy (route everything at once, which does not converge) or
manual routing (which is what the file is for).

Honest status: **43 inter-block nets remain unrouted. No Gerbers. v1 is the best
board.**

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

## 6a. The ordering fix: route the inter-block nets FIRST

The three failures above all reached the same diagnosis from different
directions: the board is full and **the existing block copper is what blocks
progress**. That makes the remedy a question of order, not of router quality.

`route_first.py` tests that directly. It takes the placed-but-unrouted board,
deletes all copper, restricts the connection targets to the 40 inter-block nets,
routes them, and leaves the result for the block pass to route *around*.

Measured, not estimated:

```
inter-block pass:  39 of 40 nets, 833 tracks, GEN_INLA not routed
block pass after:  15 of 15 block attempts, 1579 segments
merged:            2194 segments, 0 skipped, 0 unmatched nets
```

**The measurement that matters, and the false start that nearly hid it.**

The first merge landed the copper on the board the inter-block *preparation* step
had produced, which had 1081 of its 1415 pads cleared to net 0 -- that is how the
net set was restricted. DRC on that board reported **2 unconnected**, and that
number is meaningless: a pad with no net cannot be unconnected to anything. The
real figure only appears when the same copper is merged onto the genuine unrouted
board, where every pad keeps its net:

```
                        v1        route-first      (board net)
unconnected (all)      418              499
unconnected (this scope) 52              10
clearance               27               27
silk_overlap           118              118
silk_over_copper        32               32
via_dangling             0                3
```

**In-scope unconnected fell 52 to 10.** The all-nets total rose because five
blocks harvested zero segments this run, and that turned out to be a real bug
rather than a router limitation -- see 6b.

### Running steps 3-5 in the corrected order: 9,226 segments, zero shorts

The pipeline was then run in the order the measurement demands, on the route-first
board (2,194 existing tracks):

```
step 4  block routing with --base powerboard-reva-board.kicad_pcb
        15 of 15 blocks, 7032 segments harvested
step 5  merge onto the route-first board
        2194 -> 9226 tracks, 7032 added, 0 skipped, 0 unmatched nets
        dedupe_vias: 398 vias, 218 same-net duplicates removed,
                     no cross-net coincident vias
```

DRC on the final board:

```
unconnected        389      (was 418 on v1; 499 on the route-first board alone)
clearance           27      (identical to v1 -- all on U504, the latch footprint)
silk_overlap       118
silk_over_copper     32
via_dangling         5
shorting             0
tracks_crossing      0
holes_co_located     0
hole_to_hole         0
```

**Zero shorts, zero crossings, zero co-located holes, zero hole-to-hole.** That is
the first merged board in this whole effort with no electrical geometry errors.

**The one thing that made it work: `--base`.**

`route_board_blocks.py` accepts `--base` to choose which board the block pass routes
onto. It was run twice before without it:

```
run A  no --base   blocks routed against the UNROUTED board
                   2718 segments, merge -> 199 shorts, 304 crossings
run B  --base ...   blocks routed against the 2194 inter-block tracks
                   7032 segments, merge -> 0 shorts, 0 crossings
```

Passing the board as a positional argument does nothing -- the flag is `--base`, and
a positional is silently ignored, so the router produced a clean-looking result for
a board state that did not exist. That is the same blind-routing failure for the
third time in this document, and the fix every time is the same: **the copper that
already exists must be visible to whatever adds more.**

The higher segment count in run B (7032 vs 2718) is the cost of routing around
copper instead of through it, and it is the correct trade.

**What remains is now classified, not just counted.**

389 unconnected items involve **94 distinct pads** across **62 nets**. Sorted by
whether the net's *remote* pads sit in one of the `reserved` blocks -- the power
stages that are deliberately not autorouted, because their copper geometry is what
the OC-03 envelope and the gate-resistor sizing assume:

```
unconnected nets whose remote pads are in a RESERVED block   34
unconnected nets with no reserved partner -- real work       28
```

The 34 are **correct by design**. They are the generator and hub bridge phases,
their gate-drive lines (`HUB_GHA/B/C`, `HUB_GLA/B/C`), the shunt sense paths, and
the precharge chain. Those must be hand-laid; an autorouter is the wrong instrument
for them, which is why they were excluded in the first place.

The 28 that remain are a real, finite list:

```
ANALOG_OK        DRIVE12       DRIVE_EN        DRIVE_FAULT      DRIVE_NQ
FAULT_CHAIN_SENSE  GEN_INLA    GEN_SOA_ADC     GEN_SOB_ADC      GEN_SOC_ADC
GEN_nSCS         HUB_CPH       HUB_CPL         HUB_DVDD         HUB_ENABLE
HUB_INHC         HUB_INLA      HUB_SOA         HUB_SOB          HUB_SOC
HUB_VCP          HUB_VGLS      HUB_nFAULT      HUB_nSCS         LEFT_SWITCH_ADC
REF2V5           RIGHT_SWITCH_ADC              SINK12
```

`U2`, the HUB DRV8353, accounts for the largest share: 57 pads, 37 distinct nets, and
only 17 of those nets have any copper. Its gate-drive outputs correctly have none
(the reserved bridge owns them), but its internal rails (`HUB_CPH`, `HUB_CPL`,
`HUB_DVDD`, `HUB_VCP`, `HUB_VGLS`) are local decoupling that the block pass did not
join.

### U2's local decoupling: 2 of 5 routed, and a hard geometric limit found

The five missed nets were attacked directly (`route_u2_bcu.py`). Four distinct bugs
had to be fixed before anything routed at all, and two nets then routed cleanly.

**Bug 1 -- a 2D grid over a 4-layer board.** The first attempt built one obstacle map
from every track on every layer and searched it in two dimensions. Measured layer
distribution:

```
F.Cu 4932   In1.Cu 2213   In2.Cu 1243   B.Cu 222      (B.Cu = 2.6%)
```

B.Cu is **97.4% empty**, but projecting all four layers onto one plane made the board
look full, and five nets spanning 5-15 mm reported "no path".

**Bug 2 -- SMD pads blocked a B.Cu search.** Of 1,415 pads, **1,341 are SMD** and
exist only on F.Cu. Blocking them on the B.Cu map reproduced the same false "full
board" on a nearly empty layer.

**Bug 3 -- verification disagreed with the search.** `FC.stub_clear()` checks against
`FC.existing_copper()`, which ignores layers -- correct for the F.Cu fan-out it was
written for, wrong for B.Cu. Paths were found and then rejected against F.Cu copper
(`blocked by pad:HUB_VGLS`, `blocked by track:DRV_MISO`). Replaced with a layer-aware
check.

**Bug 4 -- a static obstacle snapshot.** Nets were routed in sequence against a map
taken before the loop, so net 2 collided with net 1's own fresh copper
(`blocked by via:HUB_CPH`, `blocked by B.Cu track:HUB_CPH`). The map is now rebuilt
from the live board each iteration.

With those four fixed: **HUB_CPH and HUB_VCP route, 47 and 44 segments on B.Cu.**

Then the limit:

```
5 vias placed at pad centres -> 6 clearance + 4 hole_clearance violations
shrink via 0.6 -> 0.45 mm     -> 4 via_diameter + 4 drill_out_of_range (below fab min)
```

The constraint chain is closed:

```
0.5 mm pin pitch  ->  a via must be <= ~0.45 mm to clear its neighbour
board minimum     ->  a via must be >= ~0.5 mm  to be fabricable
=> no via fits on a 0.5 mm-pitch pad centre
```

HUB_CPH is U2 pin 2, HUB_CPL is U2 pin 1, **0.500 mm apart on the same axis**. There
is no placement that satisfies both. The escape must be a **stub to a free area, then
a via** -- which is exactly what `fanout_checked.py` does, and why its construction
is the right one and this direct-via shortcut is not.

**That attempt was a trade, not a win:** unconnected 389 -> 387, but clearance 0 -> 2
and hole_clearance 0 -> 4, from the two vias that cannot legally sit where they are.
It was **not** adopted.

### Stub-then-via, with the via site SEARCHED: 4 of 5 nets, no new violations

The construction the limit demands is a stub to free area, then a via
(`route_u2_escape.py`). The via site is not assumed -- it is walked outward from the
pad in 0.05 mm steps and accepted only if it satisfies, simultaneously:

  * netclass clearance to every foreign track and pad on **every layer** it pierces,
  * 0.25 mm hole clearance to every foreign via and THT pad,
  * a stub length under 3.0 mm.

Nothing is inserted until the stub, the via and the B.Cu run all pass.

```
routed 4 nets, failed 1
   OK   HUB_CPH    54 B.Cu segs, stubs [0.95, 0.05] mm
   OK   HUB_CPL    80 B.Cu segs, stubs [0.30, 0.05] mm
   OK   HUB_VCP    45 B.Cu segs, stubs [0.95, 0.05] mm
   OK   HUB_VGLS  132 B.Cu segs, stubs [1.50, 0.90] mm
   FAIL HUB_DVDD    U2.38 no legal via site within 3.0 mm
```

DRC confirms it is a real improvement rather than a quiet regression:

```
                        before   after
unconnected                389     385
clearance                    0       0
hole_clearance               0       0
shorting                     0       0
tracks_crossing              0       0
via_dangling                 5       5
silk_overlap               118     118
silk_over_copper            32      32
```

**Four nets joined, zero new violations.** The stub lengths are informative: three of
the eight sites need only 0.05 mm, i.e. the via goes just clear of the pad, exactly
as the pitch allows. `HUB_VGLS` needs 1.50 mm, because its pad is boxed in and the
escape has to travel.

`HUB_DVDD` (U2 pin 38) has no legal via site within 3.0 mm. That is a genuine
geometry limit for this net, not a search failure -- the search is exhaustive over
four directions at 0.05 mm resolution.

The board is now 8,929 tracks and 406 vias with 385 unconnected.

### The 385 figure is not a connectivity list, and that had to be checked

After the escape, DRC still listed `HUB_CPH` as unconnected -- **paired with
`PRE_VDDM`**, a net it shares no pad with. A pad cannot be "unconnected to" a pad on
another net, so the pairing itself was the tell. Auditing the copper directly
(`audit_escape.py`) gives the real answer:

```
                        before escape        after escape
HUB_CPH   2 pads    [False, False]   ->   [True, True]
HUB_CPL   2 pads    [False, False]   ->   [True, True]
HUB_VCP   2 pads    [False, False]   ->   [True, True]
HUB_VGLS  2 pads    [False, False]   ->   [True, True]
HUB_DVDD  2 pads    [False, False]   ->   [False, False]
```

**The escape genuinely connects four nets.** DRC was not reporting that they were
unrouted; it was reporting something else and labelling it "missing connection".

Counting the pairs in the DRC report settles what:

```
unconnected pairs reported: 308
pairs whose two ends are the SAME net: 121   (39%)
```

**61% of the "missing connection" pairs link two different nets.** That is not a
description of unrouted copper. It means the 385 total -- and the 418 and 499 figures
quoted earlier in this document -- are not a count of unconnected pins. They are a
count of DRC items in a category that mixes genuine same-net disconnects with
cross-net pairings.

Consequences, stated plainly:

* the "389 -> 385" improvement was measured on a metric that does not measure what it
  was claimed to measure, so the claim is withdrawn;
* the correct in-scope figure is the **121 same-net pairs**, not 385;
* every earlier comparison that used the unconnected total inherits the same fault.

The layer-aware audit in `audit_escape.py` is the reliable instrument: it asks
whether a net's own copper reaches each of its own pads, which is the question that
was always meant.

### The real list: 12 nets, 11 of them design-excluded

Separating the report (`real_unconnected.py`):

```
pairs reported:                            273
same-net (REAL):                           107
cross-net (not a connectivity statement):  166
distinct real nets:                         12
```

The twelve, and whether their pads live in a `reserved` block:

```
HUB_SHUNT_C    middle,reserved      YES
PRE_SOURCE     reserved             YES
PGND           bottom,middle,reserved,top  YES
PRE_VDDM       reserved             YES
CTRL3V3        middle,reserved      YES
HUB_PHASE_C    middle,reserved      YES
CTRL_RAW       reserved             YES
CTRL_SW        reserved             YES
Q403_GATE      reserved             YES
CTRL_BST       reserved             YES
CTRL_PG        middle,reserved      YES
HUB_nSCS       middle,top           no
```

**Eleven of twelve involve a reserved power stage** -- the precharge chain
(`PRE_SOURCE`, `PRE_VDDM`, `CTRL_*`, `Q403_GATE`), the hub bridge phase and shunt
(`HUB_PHASE_C`, `HUB_SHUNT_C`), and `PGND` where it meets them. Those are hand-layout
nets by design.

**One net is genuine open work: `HUB_nSCS`** -- and it turned out to be blocked too.

Three pads: `U2.30` (hub driver), `R23.1` (series resistor), `U17.45` (MCU). The MCU
pin is on the far side of the board and is the obstruction. Measured around it:

```
pad GEN_INHB         x 132.02-132.32
pad GEN_INLC         x 132.52-132.82
pad GEN_INHC         x 133.02-133.32
pad HUB_nSCS(U17.45) x 133.52-133.82   <- the target
pad TIMER_BREAK_OK   x 134.02-134.32
```

Every neighbour is **0.500 mm** away -- LQFP-100 pitch -- and each already has routed
F.Cu copper leaving it (GEN_INHB 8 segments, GEN_INLC 11, GEN_INHC 9, TIMER_BREAK_OK
18). Searching 60 steps out in four directions at 0.05 mm finds **no legal via site**:
a 0.6 mm via needs 0.3 mm + clearance, and the gaps are 0.5 mm between pads that are
all occupied by their own escapes.

Two rule errors were found and fixed while establishing that, both of which had made
earlier results look better than they were:

1. **`via_site_ok` checked every layer.** In1.Cu and In2.Cu are planes with copper
   everywhere, so "clear of all layers" is unsatisfiable anywhere on the board. It
   reported `via:False` at every distance for U17.45 -- which reads like a dense pin
   field and was actually a rule that can never be met.
2. **The stub direction was not axis-aware.** Pins 44 and 46 sit 0.500 mm above and
   below pin 45, so a stub must leave perpendicular to the row. Searching all four
   directions first tries to squeeze a via between 0.5 mm-pitch neighbours -- the same
   closed contradiction already found for U2 pins 1 and 2.

With both fixed the obstruction is genuine: this pin cannot be escaped without moving
the copper that already occupies its row, or routing it on F.Cu entirely.

**So the automatable routing work is finished, and the remaining nets are all
hand-layout work** -- eleven power-stage nets and one MCU signal surrounded by already
laid copper. That is the honest floor of what the generator pipeline can do.

So the honest state of PCB-04 routing is: the automatable work is essentially done,
and the remainder is the power-stage copper that was deliberately left to hand layout
plus one signal net.

**A correction to the clearance attribution.** The section above says the 27
clearance errors are "a footprint defect on U504". They were not. KiCad requires the
design-rules file to match the BOARD filename -- `powerboard-reva-board.kicad_pcb`
needs `powerboard-reva-board.kicad_dru` -- and only `powerboard-reva.kicad_dru`
existed, so the 0.15 mm pad-pitch rule was never loaded on any DRC run of the routed
board. Every one of the 27 read `actual 0.1500 mm` against `clearance 0.2000 mm`:
exactly the value the rule permits. Copying the rules file to the matching name drops
clearance **27 -> 0**.

**Clearance is unchanged at 27 and every one of them is on U504** -- my own latch
footprint (VSSOP-8, 0.5 mm pitch, 0.35 mm pads on a 0.5 mm pitch land). It was
carried in from the schematic work, not caused by routing, and it is a real
defect in a part I added: the land pattern cannot meet the clearance rule at that
pitch. It needs either a finer design rule for that footprint (as the STM32 pin
field already has) or a different package. Recorded as open.

**Vias.** Two passes placing vias at the same coordinates produced 199
`holes_co_located` warnings, all same-net and all on the 27 inter-block nets.
`dedupe_vias.py` removes a via only when another via on the SAME net sits within
a tolerance, and refuses to touch cross-net coincidences -- it reported **zero**
of those, so none of the 199 was a short. 218 duplicates removed, 199 warnings
and all 12 hole-to-hole gone.

Two tooling defects had to be fixed to get here, both of which had been masking
the question:

1. `freerouting` is a shell wrapper installed by the ansible role, not a jar.
   `java -jar /usr/local/bin/freerouting` fails with *Invalid or corrupt
   jarfile*; the wrapper supplies the real jar itself.
2. `route_board_blocks.py` called `g.region_for(ref, sheets)` against a function
   that only existed as a closure inside `gen_pcb.main()`. The block router could
   not run at all, and the failure looked like a routing problem. `region_for` is
   now module-level and both callers share one definition of the block split.
3. `merge_tracks.py` read `layer_id` while the extractor emitted `layer`, and
   skipped 2075 of 2194 segments while printing a successful merge of 119. It now
   accepts both spellings. A merge that silently drops 95 % of its input and
   reports success is the worst kind of green.

`tests/test_route_first.py` encodes the ordering claim: the result must reload,
must use more than one layer, must carry at least 38 of the 40 declared nets, and
must not carry copper on an undeclared net.

**What this does and does not establish.** It establishes that the inter-block
nets are routable when given the space first, which was the open question. It
does not establish a finished board: 10 in-scope connections remain, 5 blocks
harvested nothing, the GEN/HUB power stages are hand layout by intent, and no
Gerbers exist.

## 6b. Why five blocks harvested nothing (a bug, not a router limit)

`ov_chopper`, `brake_left`, `brake_right`, `aux_supply` and `rail_partition` all
reported `status=ok` with **0 tracks**. That reads as "nothing left to route" and
is actually "nothing was handed to the router".

Cause: the block pass was pointed at `powerboard-reva-first.kicad_pcb`, which is
the inter-block *preparation* board. Preparation restricts routing to the 40
inter-block nets by clearing every other pad to net 0, so 1274 of 1415 pads carry
no net. A block whose parts are all in that cleared set has nothing to connect.

Measured on `rail_partition` (43 parts):

```
powerboard-reva-first.kicad_pcb   116 pads,  0 nets   <- what the block pass got
powerboard-reva-board.kicad_pcb   116 pads, 28 nets   <- the merged board
powerboard-reva.kicad_pcb         116 pads, 28 nets   <- the real unrouted board
```

The DSN confirms it: every block's export carried the same 635 inter-block wires
and 40 declared nets, and zero wires on the block's own nets. The router was
being asked to solve the inter-block problem again for every block.

Two fixes:

1. `route_one_block.py` now counts a block's netted pads **before** removing the
   non-member footprints, and fails with a named reason when that count is zero.
   Counting after `Remove()` crashes with `'SwigPyObject' object has no attribute
   'Pads'` -- the same interpreter-damage pattern this chain already documents --
   and that crash took out 14 of 15 blocks on the first attempt at the guard.
2. The block pass runs with `--base powerboard-reva-board.kicad_pcb`, the merged
   board, so the blocks see their real nets *and* the inter-block copper they must
   route around. That is the ordering the whole change exists to achieve.

The lesson is the same one as the "2 unconnected" false result: a zero that is
reported as success is worse than an error, because it never gets investigated.

## 7. What PCB-04 still owes

1. Routing, which is the bulk of the work and cannot start on the 150 unsettled
   components until their topology is decided.
2. Gerber generation and a fab-capability check.
3. The board envelope confirmed against the physical bike.
