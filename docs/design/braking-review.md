# Downhill braking study: independent bounded review

Date: 2026-11-10. Reviewed study commit `a62e12d3735554e05338b46a4f9d20bb313dd704` and `analysis/braking/{model,summary,test_model}.py` plus `downhill-braking-envelope.md`. This review file did not exist at that commit.

**Verdict: suitable to consolidate as a screening study only. No hardware release, descent rating, procurement or energization authorization.** No circuit files changed. The current unfinished powerboard remains unsafe to energize; a proposed independent resistor test is not permission to use it.

## Independent arithmetic and boundaries

Computed separately with Python standard-library trigonometry (`theta=atan(grade)`, road length `h/sin(theta)`), without importing the study model:

- For the illustrative 150 kg, 15%, 30 km/h case, 100 m drop means 674.124947 m road length and 80.894994 s. Gravity supplies 1818.403628 W; rolling loss is 72.736145 W and aerodynamic loss 208.333333 W, leaving 1537.334150 W braking. Grade is rise/horizontal run, while velocity is along the road: using grade directly as sine would be wrong. The implementation uses the correct conversion.
- A 600 m drop supplies 882598.5 J (`mgh`), independent of descent speed. Stopping from 30 km/h is 5208.333333 J; stop energy is not a sustained descent duty.
- At zero battery acceptance and illustrative efficiency 0.8, a 300 W bus dump corresponds to 375 W mechanical generator input, 75 W motor/controller loss, and 1162.334150 W remaining mechanical braking. These are power allocations, not measured torque capability. Wheel torque would require wheel angular velocity and additional speed/current/traction limits; none are established here.
- Two 4.7 ohm resistors in series give 9.4 ohm, 382.978723 W and 6.382979 A at 60 V. Parallel gives 2.35 ohm and 1531.914894 W, not 383 W. Both resistors at minus 5% give 403.135498 W total. Opposite tolerance endpoints give 201.063830 W in the higher-resistance member. Both-low gives 201.567749 W each. These cold nominal/tolerance calculations do not qualify hot resistance, PWM, pulse energy, wiring or transistor SOA.
- The one-node model at 300 W, 40°C ambient, 0.3 K/W and 900 J/K gives 120.246878°C after 600 s and 130°C asymptote. Staying at 80°C continuously would require at most 0.133333 K/W before interface/local rises. The assumed model is not an installed heatsink curve.

No arithmetic correction was needed. The ten regression tests passed in both normal Python and optimized `python3 -O`; unittest assertions remain active. `summary.py` reproduced all rounded document tables and the 26,244-row grid extrema (133.293122–1763.517037 W). These checks validate this bounded calculator, not physical braking behavior or arbitrary nonfinite inputs.

## Manufacturer evidence independently checked

Downloaded the linked distributor-hosted **manufacturer** PDF and extracted its text again. SHA-256: `99dcb84413e75c360801cf3c43b7fb4d2143af95d8d0b9eafa865bf565c4ccab`.

- Footer: literature **1773035**, **Issued: 11-05**. This is an old issue, not proof of current product specifications.
- Page 1 explicitly labels **Standard Heatsink — Area (mm²)**: HSC300 **578000**; the next row is **Thickness (mm)**: **3**. Thus 578000 mm² = **0.578 m² area**, not a length, volume, 578 mm², or 578000 mm³. Do not multiply area by thickness and call it a cooling rating. One-/two-face area convention and installed boundary conditions remain unconfirmed.
- HSC300 is 300 W with the specified heatsink at 25°C, 75 W without; compound is essential for HSC200/250/300. Better sinks do not authorize uprating. Two 300 W labels do not prove a shared 600 W assembly.
- Rendered page 3 independently: horizontal axis is **heatsink temperature**, not ambient. The 300 W bend lies between 125°C and 150°C just above 125°C, with zero at 250°C. Replaced the study's approximate 130°C wording with that visible interval; no precise release curve is inferred.
- Retrying the linked newer Rev E PDF failed with curl HTTP/2 error 92. Current revision and exact part confirmation remain release prerequisites. No pulse rating or exact present-day revision equivalence was established.
- The Fischer sink's 0.3 K/W remains an unqualified screening number. No actual installed curve, orientation correction, guard penalty or road-speed cooling curve was fabricated or validated.

## Scope and safety retained

Only **120 kg rider plus luggage** is operator-confirmed. Gross 140/150 kg, grades, speeds, vertical drops and duty are assumptions; no actual slope/duty was supplied. In particular 150 kg / 15% / 30 km/h is not a user requirement.

Supplemental wheel braking is rider-request-only. Autonomous emergency bus clamping is separate and must not depend on a brake request. At no request, unavailable regeneration, thermal cutback or unresolved faults, credit zero useful electrical assistance; mechanical braking remains necessary and unqualified by this study. Full-pack charge rejection, isolation and supply-loss behavior remain unresolved protection prerequisites.

The 100 W independent test target and conditional 300 W/up-to-600 s proposal are not authorizations, bicycle ratings or permission to energize the unsafe board. The study's staged isolated-source protocol, independent interruption and temperature aborts remain prerequisites, not proof that tests happened. No test source, motor, resistor or bicycle was energized in this review.

## Consolidation

Local review branch incorporates GitHub default commit `44c5fd4` and its storage study/review without altering those files. Further concurrent default changes must be merged non-destructively before publication. This review does not certify storage, entry-stage circuits or any complete-board release. Remote publication is left to the manager; a clean local SHA alone is not default publication.
