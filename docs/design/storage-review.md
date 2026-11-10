# Storage study review — 2026-11-10

> **Provisional analysis accepted with corrections, not chemistry selection or hardware release.**
> Reviewed source `1927fbcfca3ba9dc1aeb753d6b43ab500df0272c` on latest fetched
> GitHub master `30560f6`. No schematic changes, purchases or pack qualification.

## Findings and corrections

1. **Launch arithmetic agrees.** Independent 100,000-step midpoint integration of
   `Pwheel=(ma+mg*Crr+rho*CdA*v²/2)*v`, followed by division by drive efficiency
   and subtraction of **250*0.9=225 W electrical generation**, confirms
   150 kg/25 km/h/10 s: net 0.6951 Wh and ramp-end deficit 778.1615 W.
   Multiplying the complete wheel demand by the 80% combined efficiency would
   wrongly apply generator losses to stored energy. Neither 10 s nor 778 W is an
   operator requirement; no power increase follows from this scenario.
2. **Net energy is not capacity.** Existing prose warned correctly, but the model
   only emitted clipped net `buffer_wh`. Added signed `net_bus_wh`, cumulative
   `excursion_wh`, initial energy and charge headroom. For the same case they are
   0.6951, 0.7709, 0.6951 and 0.0758 Wh respectively. Storage losses, SOC reserve,
   rejected charge, rotating inertia and actual efficiency maps remain unmodelled.
   The nonnegative-resistance domain is now explicit and invalid time/efficiency
   inputs fail with ValueError. A 30 s ramp has **negative net** -0.1753 Wh yet
   needs 0.5592 Wh ideal excursion: regression protects this distinction.
3. **Screen slower launch, not larger hardware.** Under the same assumptions,
   30 s to25 km/h gives 235.63 W residual storage peak, 455.63 W traction-bus
   demand and 460.63 W including auxiliaries. Thus this illustrative case is below
   500 W even when comparing total traction demand, not merely residual storage.
   This is not a selected launch profile or torque/thermal feasibility proof.
4. **Cap energy and voltage checks agree.** 20s means 20 series cells, not20 seconds:
   300 F/20=15 F; 20*4.5 mΩ=0.09 Ω; 50–25 V yields3.90625 Wh ideal.
   25 V is not compatible with a36 V minimum direct bus; DC/DC is required for
   that window. Direct500 W needs ≥37.25 V open circuit to deliver36 V, reducing
   ideal 50 V-window energy to2.31758 Wh (before further loss/reserve), versus
   the unguarded2.50833 Wh. Converted low-end discharge requires22.9485 A and
   loses47.3971 W in ESR; at doubled ESR these become25.8720 A/120.4853 W,
   terminal20.3430 V. These are instantaneous electrical corners, not temperatures.
   Charge at50 V open circuit with475 W terminal input gives9.3429 A,
   7.8560 W loss, and50.8409 V terminal: taper/inhibit before the selected
   **terminal** ceiling; a50 V sum cannot authorize further charging. Per-cell
   limits/balance remain mandatory (50/20=2.5 V nominal study ceiling).
5. **Confirmed operator boundaries:**120 kg is rider+luggage;140/150 kg are still
   total-mass assumptions. Electrical braking is rider-requested only, never an
   automatic means of filling storage. Rejected regen must preserve mechanical
   braking; generator surplus and bus protection are separate control obligations.

## Source and BOM boundaries

Re-downloaded manufacturer P28A V2 and Lithium Werks SF00008 rev3 (Aug2025)
PDFs using urllib + pdftotext. Verified P28A2.8 Ah/3.6 V/46 g/35 A discharge/
8.4 A max charge/20 mΩ DC at10 A1 s and0–60°C charge; verified ANR26650M1B
LFP2.6 Ah/3.3 V/76±1.5 g/52 A discharge/26 A continuous charge/40 A10 s charge,
3.6 V recommended fast-charge ceiling and AC-only impedance. Its special
<250 mA subzero note does not qualify ordinary cold regen. Series ceilings
are13*4.2=54.6 V and16*3.6=57.6 V, not generic58.4 V LFP charging.

Eaton SKU was accessible but extraction lacked detailed tables and rendered an
ESR unit as “mW”; do not copy that unit. Full XV PDF retry timed out. Toshiba
retry failed DNS. Thus Eaton/Toshiba detailed ratings retain the original
**indexed-primary-source, lower-confidence** status; not independently
supplier-revision-verified here. Do not turn SCiB calculated10 s power into
continuous-current or cold-charge qualification. No specific P28A cathode subtype
is established by its cited lithium-ion datasheet.

CSV bare-cell masses and quantities agree with the study: P28A0.598 kg,
LFP1.216 kg, SCiB3.000 kg, XV20s1.240 kg, XL20s10.300 kg. These are not assembled
pack weights. BMS, enclosure, protection and converter mass/cost remain unknown;
blank prices mean unknown, not free. No live stock or price was established.

**Recommendation remains provisional:** compare protected direct-bus LFP with
P28A; retain converter option, do not select chemistry from nominal Wh alone.
P28A's lower bare-cell mass competes with LFP's cited higher charge acceptance.
Neither has qualified pack-level current, cold/full-SOC acceptance or bus margin.

## Verification

Original eight tests rerun: PASS. Added regression tests first: missing excursion
output and invalid-input handling failed, then were implemented. Expanded suite:
12 tests PASS (`python3 -m unittest discover -s analysis/storage -v`), including
independent midpoint quadrature, signed-surplus excursion, ESR charge/discharge
power conservation, loaded bus guard and series-cell ceilings. Model CLI ran
successfully; no physical storage, BMS, converter or board was exercised.
