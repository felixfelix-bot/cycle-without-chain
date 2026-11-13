# Board sizing and the layout blocker (PCB-04)

STATUS: `PARTIAL_NOT_SAFE_TO_ENERGIZE`. This derives a board size from measured
footprint geometry and records why a routed board cannot be completed for the
whole schematic. The size is defensible; the readiness is not.

## 1. Measured input, not assumption

Every one of the 387 netlist components resolves to a real footprint
(`pcbnew.FootprintLoad` against `/usr/share/kicad/footprints` plus the local
`Powerboard.pretty`). No blanks, no invented names — that was PCB-03's work and
it holds.

Bounding-box area, summed:

| Class | Area | Note |
|---|---|---|
| SMD | 48.5 cm² | one side usable |
| Through-hole | 17.9 cm² | 33 parts; blocks both sides, hand-assembled |
| **Total** | **66.4 cm²** | |

The single largest items are the MCU (306 mm², LQFP-100 14×14), two 470 µF 100 V
radial electrolytics (282 mm² each, 16 mm cans), the Coilcraft MSS1246
(167 mm²), the 20 A fuse holder (157 mm², 24.4 mm long) and the TDK SPM10065
(132 mm²). Those five set the floor.

## 2. Derived board size

Packing fractions used: **45 %** for SMT (leaves routing channels and courtyard
clearance), **25 %** for THT (a through-hole part occupies both sides and needs
a keep-out around the leads for hand soldering).

Area requirement = 48.5/0.45 + 17.9/0.25 ≈ **179 cm²**.

| Outline | Area | Parts only | Incl. routing |
|---|---|---|---|
| 140 × 110 mm | 154 cm² | 43.1 % | **116.4 %** — does not fit |
| 150 × 115 mm | 172 cm² | 38.5 % | 103.9 % — marginal |
| **160 × 120 mm** | **192 cm²** | 34.6 % | **93.4 %** — recommended |
| 170 × 125 mm | 213 cm² | 31.2 % | 84.4 % — comfortable |
| 180 × 130 mm | 234 cm² | 28.4 % | 76.6 % — generous |

**Recommendation: 160 × 120 mm, 4 layers.**

Why 4 layers and not 2: this board carries two independent 100 V motor phases
(GEN and HUB) at ~13 A with hard-switched edges of 0.87 V/ns. A two-layer board
forces those high-di/dt loops onto the same copper as the analog CSA returns and
the 3V3 reference dividers — the exact coupling the OC-03 envelope's ±3 % VREF
assumption cannot tolerate. A four-layer stack gives a solid ground plane
(L2) and a dedicated power plane (L3):

```
L1  F.Cu    signal + components
L2  In1.Cu  ground plane (continuous under the analog block)
L3  In2.Cu  power plane (split: DC_LINK / SINK12 / DRIVE12)
L4  B.Cu    signal + THT
```

Stackup 1.6 mm, 1 oz outer copper. 4 layers at this size is standard prototype
pricing and changes nothing about the design-phase cost estimate.

Why 160 × 120 specifically: it clears the requirement with ~7 % margin, which is
the smallest standard-ish size that does. Going to 140 × 110 fails outright;
150 × 115 leaves 4 % and would force the routing to be cramped in exactly the
power stage where clearance matters. If the bike envelope later forbids
160 × 120, the honest options are 170 × 125 (more margin, bigger) or splitting
into two boards along the GEN/HUB axis.

## 3. The blocker: 38 % of the board is not designable yet

This is the finding that matters more than the size.

The schematic's own sheet names carry the qualification state, and 146 of 387
components (**38 %**) sit in blocks explicitly marked as unfinished:

| Components | Block |
|---|---|
| 29 | Rail partition passive networks — **unqualified** |
| 24 | GEN 100 V MOSFET bridge — **schematic only** |
| 24 | HUB 100 V MOSFET bridge — **schematic only** |
| 16 | CTRL3V3 pack-side buck — **unqualified**, enables inhibited |
| 13 | MAIN back-to-back — **hardware inhibited** |
| 13 | PRE back-to-back — **hardware inhibited** |
| 9 | Bounded bench DC entry — **active pairs inhibited** |
| 6 | Unfinished safety / control / supply boundaries |
| 6 | OFFBOARD switch end-of-line network — **candidate** |
| 6 | LEFT/RIGHT FSR ESD clamps — **unqualified** |

"Hardware inhibited" gates (MAIN, PRE) are placeholders for a topology decision
not yet made. "Schematic only" bridges have no assigned part numbers for the
actual MOSFET/driver combination in a qualified state. Routing these now would
mean:

1. **Fixing copper geometry around a circuit that will change.** The MAIN/PRE
   back-to-back pairs are 26 components whose topology is undecided. Their
   placement determines the DC_LINK entry geometry, which the power stage
   placement must respect. Route it wrong and the power stage gets re-placed.
2. **Producing Gerbers that cannot be ordered.** A fab order needs every part
   sourced; 27 values are still series-inferred rather than datasheet-confirmed,
   and the inhibited blocks have no committed BOM at all.
3. **Claiming DRC-clean as design-done.** DRC checks geometry, not intent. A
   board can route clean and still be electrically wrong because the circuit it
   routed was a placeholder.

So the layout work splits cleanly:

- **241 components (62 %) are frozen** and can be placed and routed now with
  confidence. That includes the MCU, both DRV8353 drivers, the CSA trip chains,
  the FSR frontends, the DFF memory, the aux supply and all the analog sensing —
  i.e. everything the OC-03 and CDIV analyses depend on.
- **146 components (38 %) must not be routed** until their topology is decided.

## 4. What I am doing about it

Building the generator and proving it end to end on the frozen 62 %, with the
inhibited blocks placed as clearly-marked reserved zones. That gives:

- a real `.kicad_pcb` with edge cuts, a 4-layer stackup and DRC run,
- placement that respects the GEN/HUB symmetry the schematic already has,
- reserved courtyards sized for the undecided blocks, so a later topology change
  drops into space that was left for it rather than forcing a re-place,
- Gerbers for **review**, explicitly not for order.

That is a genuine PCB file and a genuine DRC result. It is not a fab-ready board,
and the register row will say so.

## 5. Decision still needed from the operator

Two choices I cannot make:

1. **Is 160 × 120 mm acceptable as the board envelope?** It follows from the
   parts, but whether it fits the bike is a mechanical question I have no
   measurements for.
2. **Decide the MAIN/PRE back-to-back topology** (26 components, 6 cm²). Until
   then those zones stay reserved and the board cannot be closed.

Neither blocks the generator work. Both block calling the board done.
