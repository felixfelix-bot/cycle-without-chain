# Overcurrent trip envelope (OC-03, OC-08)

STATUS: `PARTIAL_NOT_SAFE_TO_ENERGIZE`. This computes the static corner envelope
and reproduces the figure already published in the repo. It does **not** produce a
guaranteed trip point, and says so in code (`safety_claim: False`).

## 1. The formula, and two traps

From `fast-oc-source-analysis.md` §2, the trip current is

```
Itrip = ((VREF/2 − VREF·Rb/(Rt+Rb) + Vcmp_os) / G + Vcsa_os) / Rshunt
```

My first implementation got this wrong twice, in ways that both produced
plausible-looking numbers. Both are recorded because neither is guessable from
the schematic, and a reviewer could plausibly repeat either.

**Trap 1 — the reference is mid-rail, not the divider node.** The DRV8353 CSA
output is biased at `VREF/2`. The comparator sees the *difference* between the
divider tap and that bias. Modelling the trip as "node equals threshold" ignores
the bias entirely and gives 18.60 A instead of 16.93 A.

**Trap 2 — CSA offset is referred to the shunt, not the amplifier input.** The
±3 mV is specified at the sense resistor, so it is **not** divided by G. Treating
it as input-referred makes it 0.075 A instead of **1.5 A** — twenty times too
small, and it shrinks the whole envelope. The datasheet source analysis states
this explicitly: "CSA offset alone corresponds to ±1.5 A at nominal shunt".

Either error is invisible in the output: you get a number, it has an "A" after
it, and it looks like an answer. Only reconciling against the published figure
caught them.

## 2. The envelope now reproduces the register exactly

Exhaustive binary-corner arithmetic, 128 corners per leg (7 binary terms):

| Term | Bound | Source |
|---|---|---|
| VREF | ±3 % | illustrative, not a qualified supply spec |
| Divider resistors | ±0.1 % initial | ERA-6A |
| Shunt | ±1 % | 2 mΩ, WSLP2512 |
| CSA gain | 19.4 … 20.6 | DRV8353 datasheet |
| CSA offset | ±3 mV **shunt-referred** | DRV8353 datasheet |
| Comparator offset | ±6 mV | TLV3202 over temperature (TLV3201 is ±4 mV) |

Output for the two divider legs:

- **LOW_REF** (28.7 k top, 10 k bottom): **16.92639 … 23.08413 A**
- **HIGH_REF** (10 k top, 28.7 k bottom): **−23.08413 … −16.92639 A**

Both match the register's published `16.92639…23.08413 A` to all five printed
decimals, and the mirror symmetry the source analysis asserts is now asserted in
a test rather than in prose.

## 3. What the envelope does and does not say

**The 10 A commissioning cap sits 6.93 A below the earliest possible trip.** That
is the right relationship: the cap is a first-power-up limit that must never
itself cause a trip, and the protection must fire above the permitted operating
envelope. It is *not* a rating and not permission to commission.

**The hysteresis band is 0.0291 A in the binding case.** The documented "0.030 A"
is the nominal-gain figure. At `GAIN_MAX` (20.6) the same 1.2 mV represents less
current, so the least release separation the part can offer is **0.0291 A**, and
*that* is the number relevant to nuisance latching. Quoting the nominal figure
quietly assumes the most favourable gain. The module reports all three.

A 0.029 A band cannot reject noise by itself. Hysteresis is not a mitigation;
the downstream persistent latch is what prevents re-enable chatter, and it does
not prevent a noise-induced *first* trip.

## 4. Why OC-03 stays open, and OC-08 narrows

Five terms remain unbounded, and the module carries them in
`unbounded_terms` so they cannot be forgotten:

1. **CSA midpoint bias has no guaranteed tolerance.** TI gives `VREF/2` as
   typical only. This is the dominant unknown: it is a DC shift on the very
   quantity the comparison is made against.
2. **Thermal drift** of shunt and offset is not characterised over the operating
   range. The 1 % shunt tolerance is initial; TCR and self-heating are excluded.
3. **Trip latency** between threshold crossing and latch assertion is not
   budgeted, so overshoot past the envelope is unbounded.
4. **The low-side shunt is blind during high-side conduction** (register OC-04).
   A continuously-high-side state can leave SO at midpoint while destructive
   current flows — the envelope does not describe that case at all.
5. **Common reference faults** are not covered by a rail-tolerance term. A fault
   that moves VREF and the comparator supply together is invisible to both.

**OC-03 — still OPEN.** The corner budget is now computed and reproducible, which
was the part a calculation could settle. It cannot close until midpoint error is
bounded by measurement and thermal drift is characterised — both need a board.

**OC-08 — narrowed to a measurement.** The chatter question is now posed
numerically: does measured noise plus CSA settling residue exceed **0.0291 A**
referred to the shunt? If it does, the comparator needs external hysteresis or a
blanking window, and adding positive feedback shifts both thresholds and must be
re-solved with output swing and loading (source analysis §1). The question is
answerable; the answer needs a bench.

## 5. What this changes in practice

Nothing on the board. **No component value changed.** What changed is that a
figure previously asserted in prose is now produced by code, pinned by a test to
the same five decimal places, and accompanied by an explicit list of what it
excludes. A number that can no longer drift silently is worth more than a
slightly better number.
