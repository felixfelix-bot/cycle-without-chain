# CTRL3V3 supply — populated, inhibited schematic milestone

**NOT SAFE TO ENERGIZE. No PCB, fabrication, procurement or riding authorization.**

One real LM5164DDAR pack-side buck was added, not an external supply connector:
`ENTRY_FUSED → D500 → CTRL_RAW → U500 SW → L500 → CTRL3V3`.
It operates upstream of MAIN in the intended architecture. PGND is the primary
return; TPSI3052 secondary references remain MAIN_SOURCE/PRE_SOURCE. R402/R412
fixed 0-ohm EN inhibits and all inherited enable networks are unchanged. No
sequencer, supply-valid interlock, partition changes or second supply is added.
PGOOD is explicitly NC. Existing entry-page statements that the buck is missing
are historical annotations; this page supersedes only that supply-absence claim.

## Source-backed circuit and adaptation

Primary sources actually read:
- [TI LM5164 SNVSAU4D](https://www.ti.com/lit/ds/symlink/lm5164.pdf), cached
  `docs/research/controller/lm5164.txt/pdf`: table 4-1, sections 5.3/5.5,
  6.3.7/6.3.9, figure 7-1, table 7-1 and equations 13–26.
- [Vishay S1 rectifiers](https://www.vishay.com/docs/88711/s1.pdf), revision
  7-May-2024, pp1–2: **S1J-E3/61T**, 600V blocking, 1A thermally derated average,
  1.1V maximum forward at 1A/25C, SMA. Cathode is banded.
- [Coilcraft MSS1246T](https://coilcraft.com/getmedia/dec41de3-f4b7-4c07-b144-cc21921ccfd5/mss1246t.pdf), document 540:
  683ML electrical row; C replaces old B small-reel suffix. 68uH ±20%,
  185.9mOhm maximum DCR, 2.26A at 10% inductance loss at 25C;
  1.30/1.80A RMS for 20/40C rise at the stated conditions.

| Circuit | Implemented value / reason |
|---|---|
| U500 pin map | 1 GND, 2 VIN, 3 EN/UVLO, 4 RON, 5 FB, 6 PGOOD NC, 7 BST, 8 SW, schematic EP9 to PGND. Physical EP mapping still needs footprint validation. |
| Input diode | D500 anode2 ENTRY_FUSED; cathode1 CTRL_RAW. Its 600V blocking exceeds 58.4V, including a charged input cap plus reversed pack in the simple two-terminal branch. Alternate paths are unqualified. |
| C500/C501 | 2 × 2.2uF 100V X7R CGA6N3X7R2A225K230AB, TI table 7-1. Effective capacitance at bias remains a release blocker. |
| Bootstrap C502 | 2.2nF 50V GCM155R71H222KA37D, BST to SW, exactly TI recommendation; internal bootstrap diode, not an omitted external part. |
| L500 | 68uH MSS1246T-683MLC; retained TI reference inductance, recalculated for 3.3V. |
| Output C503/C504 | 2 × 22uF 25V TMK325B7226KMHT, reference BOM. Effective C/ESR and startup remain unqualified. |
| RON R500 | 27.4k 1%, eq15 → about 301kHz at 3.299V, **not** reference 100k for 12V. |
| FB R501/R502 | 87.3k/49.9k 1%, VOUT=1.2(1+87.3/49.9)=3.2994V before Type-3 offset. |
| Type-3 | R503=150k SW→RAMP; C505=3.3nF RAMP→VOUT; C506=330pF C0G RAMP→FB. Adapted from figure7-1, not the unmodified 12V values. |
| UVLO R504/R505 | 1M/52.3k 1%, RAW→UVLO→PGND; approximately 30.18V rising /28.17V falling typical. No fault clamp or start authorization claimed. |

Resistors marked candidate and C506 have electrical specifications but no approved
orderable MPN. R503/R504 require ≥100V working voltage, not just wattage. Footprints
other than candidate diode SMA are intentionally unselected; BOM is review-only.
TI table7-1 has an inconsistent RFB1 value/MPN and CA description: no blind copy of
those fields is used. CA part-code 2A denotes 100V; qualify actual purchasing data.

### Calculated, NOT qualified

- At 58.4V, on-time ≈187.7ns exceeds TI 50ns typical minimum. Switching-frequency
  and on-time tolerances, parasitics and current-limit overshoot need validation.
- Eq24 CA minimum ≈1.046nF; installed 3.3nF. Eq26 CB ≥286pF for the illustrative
  75us settling target; installed 330pF. This is not a measured settling result.
- Eq25 ramp ≈20.05–20.89mV for 34.9–58.4V RAW. This exceeds 12mV nominal design
  minimum, but worst temperature/tolerance/stability needs verification.
- At L=54.4uH (−20%), ripple ≈190mA peak-to-peak at 58.4V. With 0.362W load,
  Ipeak≈205mA. TI peak limit is 1.25–1.75A; Coilcraft room-temperature 2.26A
  saturation screening is favorable, not hot saturation or fault-current proof.
- Divider plus FB reference extrema give approximately 3.206–3.392V before
  ripple-injection offset, transient excursions and loading. TPSI3052 requires
  3.0–5.5V; this arithmetic alone does not qualify startup/brownout.
- UVLO upper rising corner ≈31.79V using 1.55V and opposing ±1% resistors.
  36V minus an assumed 1.1V diode drop leaves 34.9V before wiring drop.
  Diode 1.1V is specified at 1A/25C, not a guaranteed all-temperature low-current drop.
- D500 protects only the CTRL positive supply branch. It is **not** a whole-board
  reverse-polarity controller, overvoltage clamp or qualified hot-plug solution.
  The 40A/8.3ms half-sine surge specification is not a capacitor-inrush proof.
- TI recommends input ceramics rated twice maximum VIN: 100V reference parts
  do **not** meet 2×58.4V. Nominal voltage rating exceeds operating voltage but
  bias capacitance, 125V+ replacement selection, cable resonance, input bulk/damping,
  surge and branch-fuse coordination remain explicit release blockers.

## 0.8W pack-input budget, including both drivers

Retain the prior acceptance envelope, not a measured performance guarantee:
2 TPSI3052 at **50mA each assumed**, plus future analog/sequencer allowance,
total 0.362W output. TPSI3052 26mA at 20k PXFR is **typical**, not maximum.
At assumed ≥60% conversion efficiency plus 0.10W loss/diode/bias reserve:
`0.362/0.60+0.10 = 0.7033W < 0.8W`. Future analog loads are not secretly connected
by this milestone. Both installed driver input capacitors and secondary split
capacitors are retained. Their simultaneous startup current, buck output capacitor
charging, efficiency and transfer latency are **not bounded by this steady budget**.
0.8W corresponds to 22.22mA at 36V /13.70mA at 58.4V. Measure these limits including
cold start; if startup exceeds them, revise the acceptance envelope explicitly.
No SPICE supply model or fabricated startup waveform is claimed.

## Executed evidence

`hardware/powerboard-reva/exports/ctrl-supply-red.log`: new four-test suite first
failed on absent native export (3 errors, arithmetic test passed). Then real KiCad
XML export passed all four tests normally and with `python3 -O`; endpoint-corruption
and empty-export controls reject bad inputs. Tests use explicit exceptions/unittest,
not optimization-removable asserts. Export verifier's missing/empty/malformed,
corrupted pin and ERC cases passed in normal and optimized subprocesses.

Native exports: 30 PDF/SVG pages; 354 components, 205 connected nets, 1058 connected
endpoints, 52 explicit NCs. BOM/pin map agree with native S-expression export.
`export_artifacts.py` completes with strict ERC deliberately non-clean:
**exit 5, 9 errors, 0 warnings**. Before this addition: 8 errors. New error is
U500.2 CTRL_RAW un-driven; inherited eight remain, including U400.3 CTRL3V3 because
KiCad does not propagate a power-output pin through the passive inductor.
No PWR_FLAG, waiver or pin-type falsification was added to hide this.
`ctrl-before-erc.json` and `ctrl-supply-erc.json` preserve the actual delta.

The full existing 41-test run initially had four failures from stale verifier-count
fixtures (all other tests passed). Those fixtures were updated for the actual
addition and the verifier suite rerun successfully. This is not a claim of an
additional full-suite run. Incidental unrelated simulation-log changes were discarded.
Supply-page PDF rendering was inspected: no obvious overlap/clipping; small text
requires vector zoom. No whole-project fresh visual approval is claimed.

Reproduce from `hardware/powerboard-reva`:
```
python3 export_artifacts.py
python3 -m unittest discover -s tests -p test_ctrl_supply.py
python3 -O -m unittest discover -s tests -p test_ctrl_supply.py
python3 -m unittest discover -s tests -p test_verify_exports.py
python3 -O verify_exports.py
```

## Next gates — no expansion of this milestone

- [ ] Missing circuits: independent startup/brownout interlock and operational
  sequencer; MAIN conduction proof, timeout/fault authority; approved supply
  partition and PM-powered sink behavior. Do not remove any fitted EN inhibit.
- [ ] Calculated/unqualified: above ripple/UVLO/load envelope, exact passive parts,
  input damping/fuse coordination, reverse and transient alternate-path analysis.
- [ ] Manufacturing/physical: footprints, EP/land pattern, hot-loop and feedback
  layout, thermal design, creepage, independent electrical review, prototype
  isolated/current-limited test plan; then measured line/load/startup/brownout,
  both-driver startup, polarity, hot-plug, temperature, EMI and fault tests.
- [ ] Operator requirements: actual frame/attachment constraints, crank and hub
  machine identities/ratings, battery/BMS/fuse/source impedance, harness lengths,
  ambient/weather envelope, mechanical braking independence and permitted
  test-energy limits. No frame modification or machine substitution is implied.
