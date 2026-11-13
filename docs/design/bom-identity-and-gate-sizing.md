# BOM completeness and gate-resistor sizing

STATUS: `PARTIAL_NOT_SAFE_TO_ENERGIZE` — this document closes two register gates
about *documentation and component choice*. It says nothing about whether the
board is safe to power. No layout exists, no DRC has run, nothing is ordered.

Closes: **PCB-03** (BOM identity) and **RAIL-10** (passive MPNs), and supplies
the sizing behind the gate resistors that RAIL-10 asked to be frozen.
Leaves open: **PCB-02** (pad-level datasheet audit for every power part),
**PCB-04** (placement and routing), **PCB-05** (manufacturing packet), and the
bench work that any of these values would need before being trusted.

## 1. The state this started from

Measured, not estimated:

- 387 populated references in the generated schematic BOM
- **143 had no footprint** (37 %)
- **27 values still read "candidate", "provisional" or "TBD"**
- several gate resistors read "4R7 provisional" and "10R 1% gate candidate"

A schematic that emits 387 parts without land patterns cannot be laid out, and
`1u 100V X7R provisional` is not a purchase-order line. PCB-03's own text permits
blank footprints; RAIL-10 forbids candidate values. Both were OPEN.

## 2. What now exists

### 2.1 A derived approved list, not a hand-written one

`build_approved_mpns.py` reads `review-bom.csv` and emits
`approved-mpns.json`. The mapping from a schematic value string to a
purchasable part is the curated part; everything else is derived. This is
deliberate: PCB-03 requires *exact reference-set equality* between the
schematic and the approved list, and two hand-maintained lists of 387 entries
diverge on the first added resistor.

Result: **387 / 387 references resolved**, of which

- **58** have a part number read from a named datasheet or vendor drawing
- **329** follow a manufacturer's published series naming convention

That split is carried in the JSON as a `kind` field and is *not* collapsed,
because the two are not equally strong evidence. A resistor's MPN following the
CRCW0805 series naming is a safe inference; a power inductor's land pattern is
not, and that one was transcribed from the vendor drawing instead.

### 2.2 A gate that fails on the things that matter

`check_bom.py` enforces:

1. Reference-set equality between schematic and approved list, both directions.
2. One MPN per populated reference.
3. Every MPN has a library-qualified footprint (`Lib:Footprint`, not a bare name).
4. Every MPN declares a source.
5. No MPN is claimed for two different footprints.

Item 5 caught a real defect (see §4.2). Items 1–4 are PCB-03's exit criteria.

### 2.3 A gate that reports what a reader needs

The first version printed `unfrozen values: 47` next to `PASS`, which reads as a
self-contradiction. The two quantities were being conflated:

- **open decision** — unfrozen value *and* no MPN. Cannot be ordered.
- **stale qualifier** — unfrozen value, but the MPN is frozen. Orderable; the
  schematic text is merely out of date.

They are now separate lines. Current state: **0 open decisions, 0 deferred,
47 cosmetic stale qualifiers**, and the source text is being cleaned so the
count falls rather than being suppressed.

A gate must never report PASS while its own summary contradicts it. That was a
defect in this tooling, not in the design, and it is fixed rather than
explained away.

## 3. Gate resistor: how 3.3 Ω was derived

### 3.1 Why this needed deriving at all

Twelve gate resistors read "4R7 provisional". The value is not a preference; it
trades three things against each other:

- turn-on/off speed, and therefore switching loss
- dI/dt and dV/dt, and therefore phase-node ringing and EMI
- peak gate current, which the DRV8353's driver must supply

### 3.2 The driver has two limits, and they bound the same edge

The DRV8353 sources a finite peak current (1 A, configurable by IDRIVE). So an
edge has two candidate times:

```
t_RC    = 2.2 * (Rg + Rg_int + Rg_si) * Ciss      RC charge time
t_limit = Qg / I_source                            current-limit floor
t_sw    = max(t_RC, t_limit)
```

With the CSD19532Q5B (Ciss 4.7 nF, Qg 48 nC) and Rg_int 1.5 Ω, Rg_si 1.0 Ω:

| Rg (Ω) | t_RC (ns) | t_limit (ns) | t_sw (ns) | P_sw/device (W) | edge set by |
|---|---|---|---|---|---|
| 2.2 | 48.6 | 48.0 | 48.6 | 0.758 | RC (1.01× floor) |
| 3.3 | 60.0 | 48.0 | 60.0 | 0.936 | RC (1.25× floor) |
| 4.7 | 74.5 | 48.0 | 74.5 | 1.161 | RC |
| 6.8 | 96.2 | 48.0 | 96.2 | 1.500 | RC |
| 10.0 | 129.2 | 48.0 | 129.2 | 2.016 | RC |
| 22.0 | 253.3 | 48.0 | 253.3 | 3.952 | RC |

The crossover is at **R_total ≈ 4.64 Ω**, i.e. **Rg ≈ 2.14 Ω external**. Below
that the driver is the limiter and the resistor does nothing.

### 3.3 Why not 2.2 Ω, which has the lowest loss

Because at 2.2 Ω the RC time is **48.6 ns against a 48.0 ns floor — 1.25 %
margin**. Ciss and Rg_int are themselves ±20 % typicals, so a value that close to
the crossover cannot be shown to control the edge at all. It is the lowest-loss
choice and it is not a defensible specification.

The selection rule is therefore: *the smallest Rg that clears the crossover by
20 % while keeping dv/dt under the ceiling.* That is **3.3 Ω**.

### 3.4 Chosen: 3.3 Ω

- switching loss **0.936 W per device, 5.6 W across six**
- edge **60.0 ns**, 1.25× the driver floor — the resistor genuinely sets it
- **dv/dt 0.87 V/ns**
- peak gate demand 1.72 A against a 1 A driver, so the driver is in current limit
  for the initial rise and the resistor sets the tail

### 3.5 The dv/dt ceiling does no work here — stated plainly

Maximum dv/dt across every candidate is **1.07 V/ns**, well under the 2.0 V/ns
ceiling. The ceiling therefore excludes *nothing*; the RC-margin rule is the
only binding constraint. This is recorded because it would be easy for a later
reader to assume the design is dv/dt-limited. It is not. Loosening the ceiling
changes no outcome, and a test asserts exactly that so nobody "fixes" a
constraint that is not binding.

### 3.6 What a gate resistor does not do

It sets dV/dt; it does **not** damp the power loop. With a 4 nH assumed loop and
720 pF Coss the loop rings at **93.8 MHz** with **Z0 = 2.36 Ω**. Damping that is
a snubber-and-layout problem. Rg only controls how hard the ring is excited.
Conflating the two is a common and expensive error.

### 3.7 The design current is the bike's, not the driver's

An intermediate version used **20 A** because that is the DRV8353's rating, and
produced 22 W of switching loss across six devices — which should have been
obvious as wrong. Register gate **ARCH-04** leaves phase current undefined, so it
was derived from the drivetrain instead:

```
400 W mechanical, worst-case 36 V bus, 85 % motor efficiency
    -> 13.1 A DC  ->  ~13 A phase RMS
```

15 A is used as the design point: the 400 W case with headroom. Launch peaks run
2–3× that, but they are transient and the device's pulse rating covers them;
sizing continuous loss at the peak would over-build the gate drive for a duty
cycle that never persists.

## 4. Defects found and fixed in this work

Recorded because each was a real error in the tooling, and the point of the
gates is that errors get found before copper.

### 4.1 The gate reported PASS over contradicting counts

Described in §2.3. Fixed by separating open decisions from cosmetic debt.

### 4.2 0603 parts were being given 0805 part numbers

The design had already fixed 0603 footprints for `R65`, `R67` and `C40`; the MPN
table assigned the family default 0805. Caught by check 5 (same MPN on two
different footprints). The footprint now wins: resolution is size-aware, so a
0603 land gets a CRCW0603 / GRM188 part and never an 0805 one.

This is exactly the class of error that reaches a fab order as "part does not
fit the land".

### 4.3 `t_sw_ns` returned the wrong bound

A refactor left `return transition_range_ns(...)[1]`, which returns the
current-limit floor rather than `max(t_RC, t_limit)`. Caught by a unit test, not
by inspection. Three separate wrong answers preceded the current model (§3.3,
§3.7, and this), and each is now a named regression test.

### 4.4 A test that tested nothing

Mutation testing showed that dropping the RC-margin rule from 1.20 to 1.00 did
not fail any test, because the tests hardcoded the threshold. The policy
constants are now module-level (`RC_MARGIN`, `DVDT_CEILING_V_PER_NS`) and the
tests read them, so loosening the rule fails the suite.

Mutation results, current tree:

| mutation | caught |
|---|---|
| `t_sw_ns` returns the limit instead of the max | yes |
| design current 15 A → 20 A | yes |
| `RC_MARGIN` 1.20 → 1.00 | yes |
| `DVDT_CEILING` 2.0 → 5.0 | **no — correctly, see §3.5** |

## 5. What is still not done

- **PCB-02** remains open: only the DRV8353 and CSD19532Q5B have had a pad-level
  datasheet audit. The other power parts have MPNs and land patterns but not a
  verified pin-to-pad check.
- **329 of 387** part numbers are series-inferred, not individually audited.
  They are safe inferences for passives and are labelled as such; they are not
  evidence for any power semiconductor.
- **No layout, no DRC, no ERC clean-up** — the 10 undriven-supply ERC errors
  are unchanged by this work.
- **The gate-resistor values are modelled, not measured.** The loop inductance
  (4 nH) is an assumption for an unlaid-out board. 3.3 Ω is a defensible
  starting value to confirm on a double-pulse bench test, not a final answer.
- **PROT-09** (dump resistor pulse rating) and **PROT-11** (`f_chop` unchosen)
  are untouched.

## 6. Reproducing

```
cd hardware/powerboard-reva
python3 build_approved_mpns.py       # derive approved-mpns.json from the BOM
python3 check_bom.py                 # PCB-03 / RAIL-10 gate
python3 size_gate_resistors.py       # gate-resistor trade-off, writes JSON
python3 -m pytest tests/test_gate_resistors.py -q
```
