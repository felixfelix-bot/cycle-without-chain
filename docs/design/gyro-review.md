> **STATUS: INDEPENDENT STUDY REVIEW — NOT HARDWARE OR RIDER-SAFETY APPROVAL.**

# Gyro feasibility review

Reviewed 2026-11-10: feature `091de96183989c496fb7e7e502b35d41c518ef6e`, integrated without conflicts onto fetched `github/master` at `d07bdb2`, in `~/worktrees/cycle-gyro-review` (`integration/gyro-reviewed`). Scope: [study](gyro-balance-feasibility.md), [source ledger](gyro-parts-sources.md), [candidate CSV](gyro-candidate-bom.csv), arithmetic model/tests and README delta. No hardware changes, orders, keys or rotor-construction advice.

## Verdict

**Suitable to merge as bounded research after the corrections below, not an implementation decision.** The electrical-buffer baseline remains unchanged. No qualified bicycle-scale contained CMG was established by the bounded sourcing exercise; that is not proof of universal market absence or physical impossibility. No guarded rotor design or rider stabilizer was qualified.

## Independent arithmetic checks

Recomputed directly with `math`, without importing the study model:

| Quantity | Derivation | Result |
|---|---|---:|
| Gravity torque, 150 kg, 1 m, 1 degree | `150*9.80665*sin(pi/180)` | 25.672446 Nm |
| Gravity torque, same at 5 degrees | `150*9.80665*sin(5*pi/180)` | 128.205880 Nm |
| Earlier 25 km/h kinetic energy | `0.5*150*(25/3.6)^2` | 3616.898148 J |
| Angular speed at hypothetical 60,000 rpm | `60000*2*pi/60` | 6283.185307 rad/s |
| Momentum of that energy at that speed | `H=2E/omega` | 1.151294438 Nms |
| Full energy for 1 Wh usable, speed ratio 0.8 | `3600/(1-0.8^2)` | 10,000 J |
| Reserved energy | `10000*0.8^2` | 6400 J |
| Full / minimum momentum | `2E/omega`, or `I*omega` with fixed inertia | 3.183098862 / 2.546479089 Nms |

The earlier approximately **128.25 Nm** follows from `g=9.81` (128.249675 Nm); the study's **128.206 Nm** uses its explicitly documented standard gravity `g=9.80665`. This is a constant choice, not an arithmetic error. No numerical-model correction was needed.

One Wh usable is the **3600 J difference**, not the total rotor energy. Minimum momentum is 80% of full momentum while reserved energy is 64% of full energy. Any authority requirement must hold at minimum momentum and usable geometry, not just full speed. `tau/H=111.358 rad/s` for the earlier energy case is a mathematical best-case ratio, not an actuator selection.

## Direction, finite travel and safety

- `dH/dt` is rotor torque; chassis reaction has the opposite sign. The study states this. Its scalar `H*cos(delta)*delta_dot` is an orientation-dependent projection, not a universal restoring sign or independent three-axis control law.
- Corrected the model's impulse helper docstring from “Signed exchange magnitude” to **“Absolute exchange magnitude”** because it returns `abs(...)`. Runtime behavior is unchanged. A controller must not use that scalar as a signed correction command.
- Fixed-speed `2H` is an upper bound on net vector momentum change, not continuously available torque. For the ideal H=10 Nms, -45 to +45 degree example, `H*(sin45-sin(-45))=14.142 Nms`; at 25.672 Nm this is about 0.551 s of ideal constant-torque impulse. It is not time-to-fall or recovery performance. Rewinding returns an opposite impulse; external desaturation/contact forces remain necessary.
- Turning, singularities, finite travel, power loss and startup/shutdown remain explicitly unresolved. Tests establish arithmetic only. No containment, mounting, medical benefit, traction recovery or fall-prevention claim is adopted.

## Source cross-check and corrections

All nine reachable primary links in the ledger returned HTTP 200 during this review (Seakeeper product/technology, Lit Motors, Adafruit product/pinouts, PJRC, ROBOTIS, TEDCO and Veleon). The deliberately recorded failed `gyro.bike` discovery lead was not counted as a qualified source or re-tested. HTTP success alone is not specification validation.

The [live Seakeeper 1 technical table](https://www.seakeeper.com/seakeeper-products/seakeeper-1/) says **“Weight 365 lbs (166 kg)”**, not 165 kg. Corrected the study, CSV and ledger to 166 kg and the resulting minimum combined masses to **306/316 kg**. Verified the table also states 9,750 rpm, 1,000 N-M-S, 12 VDC, 600 W maximum spool-up, and 225–600 W operating input. This remains a marine scale comparator, not a bicycle candidate; a vacuum enclosure is not verified rotor-burst containment.

Supporting spot-checks confirmed Adafruit's 2.5 g and dated stock wording, PJRC's 600 MHz and non-5-V-tolerant 3.3 V pins, and ROBOTIS's distinct 4.1 Nm stall and 46 rpm no-load points at 12 V. **BNO085, Teensy 4.1 and XM430 are experiment-support leads only**, not a proven closed-loop rider stabilizer or a qualified guarded rotor system. The educational candidate remains HOLD. Prices and delivery were not qualified.

## Execution and preservation evidence

Commands run from the integration worktree:

```sh
python3 -m unittest discover -s analysis/gyro -v
python3 -O -m unittest discover -s analysis/gyro -v
python3 analysis/gyro/model.py
python3 -O analysis/gyro/model.py
git diff --check github/master
```

Both test modes passed **8/8**; both model modes produced matching displayed outputs. Relative Markdown links in the study, source ledger and README resolved to existing files. Diff whitespace check passed. README changes are only three additive study-link lines: all five prior audience bullets, the sixth balance-assistance use case and the historical-source/purchasing caution remain intact. No concurrent base files were replaced.

Review tooling initially lacked BeautifulSoup; direct HTTPS retrieval and standard-library HTML stripping supplied the source checks instead, without installing dependencies. This review did not run a dynamic bicycle simulation, hardware test, rotor qualification or market-wide search.

Remote publication is left to the parent manager under the manager-only GitHub mutation rule. The integration branch contains the original study history and this review; fetch/recheck the default branch before publishing without force.
