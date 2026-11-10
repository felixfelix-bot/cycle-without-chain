# CTRL3V3 buck — independent electrical review and one correction

**Scope: prototype electrical review of the populated CTRL supply page.** This is not a
PCB, fabrication, procurement, riding or energization approval. `NOT SAFE TO ENERGIZE`
stays. Reviewer ran on model tier `tier/delegation` (the value reported by the serving
route); the family behind that tier alias is **not known**, so no cross-family claim is
made for this review. Reviewer is not the page author.

Pinned inputs: `master e6693cd`, PR5 head
`362f50edec49a8ebc9e88af8143fd6da19cbf08a`, worktree `~/worktrees/cycle-ctrl-review`.
Evidence read: `ctrl_supply_circuit.py`, `tests/test_ctrl_supply.py`,
`docs/design/ctrl-supply-milestone.md`, the regenerated native
`exports/ctrl-supply.xml` netlist (not the generator manifest), strict ERC JSON, and the
cached TI LM5164 SNVSAU4D text under `docs/research/controller/`.

## 1. The correction: input capacitors were rated below the TI recommendation

`C500`/`C501` were 2.2µF **100V** `CGA6N3X7R2A225K230AB`. TI SNVSAU4D recommends input
ceramics rated at **twice the maximum input voltage**; 2 × 58.4V = **116.8V**. The page
already said the 100V parts "do not meet 2×58.4V", i.e. the mismatch was known and left
in place. That is now fixed in the schematic, not restated:

| | Before | After |
|---|---|---|
| C500/C501 | 2.2µF 100V X7R CGA6N3X7R2A225K230AB | 2.2µF **200V** X7R **KYOCERA AVX 22252C225KAT2A** |
| Footprint | none stated | `Capacitor_SMD:C_2225_5664Metric` (stock KiCad, pads 1.625 × 6.60 mm, pitch 5.075 mm) |

Selected part, with what is and is not verified:

- **Verified from distributor and manufacturer family data**: KYOCERA AVX
  `22252C225KAT2A`, 2.2µF ±10%, **200VDC**, X7R, −55…+125°C, EIA 2225 body
  **5.7 × 6.3 mm** (KGM56 family, datasheet-indexed dimensions
  `https://datasheets.kyocera-avx.com/KGM_X7R.pdf`; listing
  `https://www.newark.com/kyocera-avx/22252c225kat2a/capacitor-2-2uf-x7r-200v-2225/dp/41AM3497`).
- **Unknown, stated as unknown**: the effective capacitance at 58.4V DC bias. No
  candidate-specific bias curve was retrieved; the manufacturer's SpiMLCC tool is linked
  but a link is not data. **Do not** read "2.2µF" as 2.2µF in circuit, and do not read
  "2 × 2.2µF" as 4.4µF effective.
- **Unknown**: cost and availability beyond a page snapshot (US$3.68 at qty 1, 260 in
  stock, cut tape, Newark part 41AM3497 — not checkout-confirmed, no EU delivered price,
  no lead-time). Not procurement-authorized.
- **Unknown**: whether the 2225 land pattern matches the vendor's recommended pad
  geometry; the stock footprint is IPC-7351 nominal and the vendor's own land pattern was
  not compared. Not a 1210/2220 drop-in — the previous part had no footprint assigned, so
  there is no footprint regression, only a new unverified one.

**Derating is a recommendation, not an absolute failure threshold.** The 100V part
exceeded the 58.4V operating voltage and would not have failed by arithmetic at
nameplate; the objection is margin under surge, hot-plug overshoot and bias-driven
capacitance loss, i.e. exactly the quantities nobody has measured. The 200V part buys
2× headroom (58.4V = 29.2% of rating) and nothing more. No claim is made that it retains a
given capacitance, damps a cable resonance, or survives the entry surge.

Supporting changes, all mechanical: the generator now assigns the footprint for C500/C501
only; the page note reads "200V input ceramics: effective C / surge / damping OPEN; 2225
footprint candidate, layout not qualified"; `review-bom.csv` regenerated.

**TDD trail.** `test_input_capacitor_derating_and_package` was added and run against the
unmodified export first: **RED, exit 1** (`exports/ctrl-review-red.log`) — the export
carried the 100V value and an empty footprint. Then the generator changed, native
exports regenerated, and the test passed.

## 2. Independent checks (recomputed, not inherited)

| Item | Recomputed result | Verdict |
|---|---|---|
| Pin map 1–8 | 1 GND, 2 VIN, 3 EN/UVLO, 4 RON, 5 FB, 6 PGOOD NC, 7 BST, 8 SW; schematic EP9 → PGND | agrees with TI table 4-1. EP-to-pad **mapping still unverified** |
| Feedback | 1.2(1+87.3/49.9) = **3.2994V**; divider extremes **3.2062–3.3919V** before ripple-injection offset | consistent with page. Type-3 adds roughly +28mV nominal offset, so the bare-divider window is not the rail window |
| fsw / on-time | 27.4k → **301.04kHz** nominal CCM; ton **314.0ns @34.9V**, **187.7ns @58.4V** | above the 50ns typical minimum, as claimed |
| 68µH ripple | Lmin 54.4µH → **182mApp @34.9V**, **190mApp @58.4V** | matches the page's ≈190mA |
| Peak / saturation | 0.362W/3.2994V = **109.7mA** load → **Ipk ≈ 205mA**; Coilcraft 2.26A @10% L drop at 25°C | peak is far below both the 1.25–1.75A TI limit and the 2.26A screening value; **hot saturation and current-limit overshoot unproven** |
| COT minimum load | CCM boundary **91–95mA**; ramp **20.05–20.89mV** over 34.9–58.4V | above the 12mV minimum-VIN design floor and near the 20mV recommendation. Below ~92mA the part enters its intended DEM/pulse-skip; **301kHz is not guaranteed at light load** and no preload is required by the datasheet |
| UVLO | **30.181V rising / 28.169V falling** typical; worst-case rising corner **31.785V** | margin exists at 34.9V cold-line; restarts into both drivers and the wiring drop remain unbounded |
| Bootstrap | 2.2nF 50V X7R BST→SW, internal bootstrap diode | TI's specified value and topology. Gate the **actual** capacitor against the 1.5–2.5nF range over tolerance/temperature/bias, not the 2.2nF label |
| D500 reverse stress | charged CTRL_RAW at +58.4V with the pack reversed at −58.4V ⇒ **≈116.8V** across the diode, not 58.4V | 600V rating clears the static two-terminal branch by a wide margin. This proves nothing about alternate paths, inrush or surge, which the 40A/8.3ms rating does not cover either |

No wiring defect was found in this scope, so nothing else in the page was changed. Every
"calculated, not qualified" statement in the milestone was re-derived and none was
overstated — several were understated (the feedback window excludes ripple offset; the
CCM boundary is load-dependent).

## 3. Remaining startup and budget limits (exact, unresolved)

The **0.8W is a PACK INPUT acceptance cap, not an output rating.**

- Steady-state: 0.362W output (2 × TPSI3052 at an **assumed** 50mA each) ÷ 0.60 efficiency
  + 0.10W diode/bias reserve = **0.7033W**, i.e. **0.0967W headroom** under 0.8W.
- Current form of the same cap: **22.22mA at 36V**, **13.70mA at 58.4V** pack input.
- **Not bounded by that number**: buck output-capacitor charging (2 × 22µF nominal, less
  at bias), simultaneous start of both driver input and secondary-split capacitors, cold
  start at −20°C, efficiency at 301kHz and 3.3V out, TPSI3052 transfer latency, and any
  inrush through D500 into C500/C501. A start that briefly exceeds 22.22mA is not covered
  by the cap; it is an acceptance-envelope decision, not a component fact.
- TPSI3052's 26mA at 20k PXFR is **typical**, not maximum; the 50mA assumption is an
  envelope, not a datasheet limit.
- Hard stops that no budget can fix: no PGOOD interlock, no supply-valid or brownout
  authority, no whole-system reverse or OV protection, EP/thermal layout unverified,
  9 strict-ERC errors unsuppressed, no footprint qualification beyond the one added here.

## 4. Finite gating checklist for the next stage (no rail partition or sequencer work here)

Nothing in this review adds a rail, a partition or a sequencer. Ties preserved: `R402` and
`R412` 0Ω EN inhibits still fitted and unchanged, `PGOOD` still explicitly NC.

1. Freeze exact passive MPNs (R500–R505, C505, C506 and the 200V input pair) with working
   voltage, tolerance and temperature; no "candidate" values survive into a fab BOM.
2. Obtain C500/C501 **effective-capacitance vs DC bias** data at 58.4V and decide the
   minimum acceptable effective input capacitance; add damping if the value is thin.
3. Validate the 2225 land pattern against the vendor recommendation and the EP/thermal
   land of the LM5164 package; then hot-loop, FB-isolation and thermal layout review.
4. Bound source and harness impedance, hot-plug overshoot, D500 inrush and reverse
   alternate paths, and branch-fuse clearing.
5. Approve an isolated, current-limited prototype test matrix: 36V and 58.4V, zero /
   minimum / full load, both-driver simultaneous start, UVLO restart, temperature; measure
   FB ripple, rail extrema and pack input current against 22.22mA / 13.70mA and 0.8W.
6. Only after 1–5: design the supply-valid / brownout interlock and the operational
   sequencer as a separate, explicitly scoped change. Do not remove an EN inhibit to get
   there.

## 5. Verification of this review's own change

- `python3 export_artifacts.py` → 30 PDF/SVG pages, 354 components, 205 nets, 1058
  endpoints, 52 NCs; strict ERC **exit 5, 9 errors, 0 warnings** — the same nine
  `power_pin_not_driven` errors as before this change (8 inherited + `U500.2`), no new
  class, no `PWR_FLAG`, no waiver, no pin-type falsification. `grep -c PWR_FLAG` = 0.
- Full suite: **42 tests OK** normally and **42 OK** under `python3 -O`
  (`exports/ctrl-review-tests.log`, `exports/ctrl-review-tests-O.log`), the 42nd being the
  new capacitor test.
- Netlist cross-check is on the native export (`exports/ctrl-supply.xml`), so the value
  and footprint assertions read KiCad's own output, not the generator's manifest.
- Regeneration rewrote 29 unrelated SVG pages with nothing but their creation timestamp;
  those were reverted so the diff stays on the supply change.
