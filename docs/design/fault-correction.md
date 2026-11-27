# Fault correction — UNSAFE DRAFT / NO ENERGIZATION / NO PCB

2026-11-10. This is a bounded implemented schematic correction and primary-datasheet audit,
not electrical approval. **Do not energize the power stage, fabricate a PCB,
release layout, or ride this design.** Existing protected-entry, fast-current
trip, auxiliary-loss bus-sink, supply-sequencing and ERC blockers remain open.
A schematic/checker/behavioral-simulation pass is not proof of safe hardware.
The generator, native schematics, BOM, pin manifest and real KiCad netlist implement the topology below. Behavioral simulation is not silicon validation.

## Implemented release-before-rearm circuit

Define `R` as the conditioned active-high manual RESET_REQUEST, not the
supervisor's active-low RESET output. Define `H` as healthy only when every
required fault source is healthy. Use two SN74LVC1G74 positive-edge DFFs:

- FF1: D=1, CLK=NOT R, active-low CLR=H, active-low PRE tied high.
- FF2: D=FF1.Q, CLK=R, active-low CLR=H, active-low PRE tied high.
- Permission is FF2.Q. Final enable must additionally require H and ARM,
  using SN74LVC1G11 AND logic with qualified input edges.
- Condition slow/offboard inputs with SN74LVC3G17 non-inverting Schmitt
  buffers. **This part is not an inverter.** U15 is SN74LVC1G04DBVR (TI SCES214AF pin table: A=2, GND=3, Y=4, VCC=5, NC=1). Its NC is tied to ground; inverter timing/skew remains a qualification obligation.

The DFF truth table gives asynchronous clear priority regardless of CLK/D
when PRE stays inactive; PRE and CLR must not both be asserted.[1]
By logical analysis, H=0 clears both memories. H returning high alone cannot
set either. If R stays high across fault clearance, neither FF can rearm.
A subsequent R falling edge records release in FF1; a later R rising edge
transfers that permission to FF2. If R was low throughout the fault, the first
post-fault rising edge still samples FF1=0: release and a second rising edge
are required. A reset pulse made wholly during a fault is discarded.

This is edge sequencing, **not debouncing, synchronization, or a proof against
arbitrary transients**. Bounce can supply release/press edges. FF1 remains set
until the next fault; it is not a fresh-release token for each subsequent ARM
cycle. Require a qualified operator command/debounce and separately specified
ARM sequence. Recovery of asynchronous CLR near either clock edge can violate
setup/recovery requirements: do not represent that event as a deterministic
Boolean transition. The fault must still directly inhibit the final enable.
Proof obligations include startup initialization, brownout, R stuck high/low,
bounce, runt pulses, simultaneous R/H edges, short faults, ARM held high and
repeated watchdog recovery. Ideal event-level simulation alone cannot close
these obligations.

## Fault aggregation: separate inputs, no diode level shifts

Supervisor RESET and each driver nFAULT must enter separate LVC input paths;
do not wire a push-pull supervisor output onto an open-drain fault bus. Remove
the proposed series diode drops from these signal paths. Comparator outputs
connect directly to their receiving input/pullup node (no series diode).
Open-collector comparator combination, where used, needs a sink-current and
pullup budget for every connected collector. A slow comparator/pullup node
must reach a Schmitt input before a non-Schmitt AND or DFF input.

Use cascaded AND stages as necessary: a three-input gate cannot aggregate an
arbitrary number of distinct fault sources. Each fault must have an explicit
path to H and disable, with polarity, powered/unpowered states, loading and
latency traced. Removal of diode drop improves the voltage budget but does
not qualify driver output specifications or power-off behavior; the driver
primary datasheet was not re-audited in this bounded task.

## Actual primary-table limits (not typical-value guarantees)

The PDFs below were downloaded from TI and read as pdftotext tables. Relevant
revisions are SCES794G (September 2021), SCES470F (August 2015), SCES487I
(November 2024), SLVS165O (March 2025),
and SLCS006Z (May 2025). Table scope and test conditions travel with each limit.

| Device / table | Retrieved bound | Design consequence |
|---|---|---|
| SN74LVC1G74 §6.3 | VCC operating 1.65–5.5 V; at VCC=3–3.6 V VIH≥2.0 V, VIL≤0.8 V; input transition ≤10 ns/V at 3.3±0.3 V | DFF inputs are not Schmitt; condition slow edges. Data-retention voltage is not an operating guarantee.[1] |
| SN74LVC1G74 §6.6, 3.3 V columns | CLK pulse width and PRE/CLR-low pulse width ≥2.7 ns; D setup ≥1.3 ns, D hold ≥1.2 ns, PRE/CLR inactive setup ≥1.2 ns | Respect pulse and asynchronous-clear release timing, including inverter/buffer skew. These are pin timing requirements, not a system debounce specification.[1] |
| SN74LVC1G74 §6.7 | At 3.3 V, CLK→Q max 5.9 ns and CLR/PRE→Q max 5.9 ns at −40…85 °C; corresponding maxima 7.9 ns at −40…125 °C | Do not reuse 85 °C maxima at 125 °C; RSE/DQE packages are only specified to 85 °C in §6.3, DCT/DCU to 125 °C.[1] |
| SN74LVC3G17 §6.5 | At VCC=3 V: VT+ 1.50…1.87 V, VT− 0.84…1.14 V, hysteresis 0.56…0.87 V, in both temperature columns | Falling input must go below the minimum VT−; rising input must exceed maximum VT+. These are **3 V table points**, not a silently interpolated 3.3±tolerance guarantee.[2] |
| SN74LVC3G17 §6.5 | At VCC=2.3 V: VT+ 1.11…1.56 V, VT− 0.58…0.87 V; at 4.5 V: VT+ 2.16…2.74 V, VT− 1.41…1.79 V | Do not interpolate these into a guaranteed continuous-supply threshold envelope. Obtain manufacturer confirmation or select a device with explicitly sufficient range bounds.[2] |
| SN74LVC3G17 §6.6 | 3.3±0.3 V, −40…85 °C: propagation maximum 5.4 ns (30 pF) / 6.4 ns (50 pF), per Figure 3 loads | Table shown is limited to 85 °C; the 125 °C typical plot is not a guaranteed maximum timing table.[2] |
| SN74LVC1G11 §5.3 | VCC 1.65–5.5 V; at 3–3.6 V VIH≥2.0 V, VIL≤0.8 V; input transition ≤10 ns/V at 3.3±0.3 V | Non-Schmitt AND needs conditioned inputs.[3] |
| SN74LVC1G11 §§5.6–5.8 | At 3.3±0.3 V: tpd max 4.1 ns at 15 pF/85 °C; 4.9 ns at 50 pF/85 °C; 6.2 ns at 50 pF/125 °C | Pick the actual load/temperature column, and add every stage plus receiver delay.[3] |
| LM339B §6.7 | VOL max 400 mV at 25 °C; **550 mV at −40…85 °C**, ISINK≤4 mA, VID=−1 V; table default VS=5 V | Use .55 V rather than .4 V in the temperature screening calculation. This does not establish VOL/propagation at infinitesimal threshold overdrive or every supply condition.[5] |

At their 3 V output test point, the DFF and AND tables specify VOH≥2.4 V
at −16 mA and VOL≤0.4 V at 16 mA; at ±24 mA the bounds are 2.3 V and
0.55 V. LVC3G17's 24 mA VOL limit becomes 0.75 V in the 125 °C column.
Use actual load currents, not headline drive ratings.[1][2][3]

A direct .55 V comparator output against the AND/DFF .8 V low limit leaves
only .25 V before ground offset/noise; against the Schmitt VT− minimum at
exactly 3 V it leaves .29 V. These subtractions are screening arithmetic,
not approval of the comparator test condition or the whole rail range.
Schmitt input hysteresis is not a substitute for the missing supply-corner
qualification. LVC Ioff limits in the tables cover specified VCC=0 tests,
not all intermediate brownout voltages or every board-level backfeed path.[1][2][3]

## Retain TPS3823-33 non-A: negative edges and fail-disabled reset

The inspected family datasheet §7.3.4 explicitly says the TPS3823 watchdog
must be triggered by **negative transition at WDI**. A rising edge alone is
not credited as service. Disconnecting WDI can disable the watchdog; TI
explicitly recommends **1 kΩ to ground** when this is unwanted. An existing
10 kΩ pulldown has been replaced with 1 kΩ in the actual generator/BOM. The MCU must source approximately 3.3 mA when WDI is high; pin selection/current budget remains open.[4]

§6.7 specifies WDI pulse width ≥100 ns and MR pulse width ≥1 µs. §6.3 specifies
WDI/MR VIH≥0.7VDD, VIL≤0.3VDD and transition time ≤100 ns/V. §6.8 gives watchdog
timeout min/nom/max 0.9/1.6/2.5 s and reset delay 120/200/300 ms. **The timing
tables' header says RL=1 MΩ, CL=50 pF, TA=25 °C unless otherwise noted.** Do
not turn these numbers into an unstated full-temperature guarantee.[4]

Critically, §7.3.4 warns that WDI transitions during asserted RESET can leave
the non-A part's RESET **stuck low after supply recovery**. We retain non-A
and explicitly accept this as **fail-disabled availability loss**, not a
resolved silicon behavior. Never bypass RESET or force H high to restore use.
This classification assumes the downstream hardware really remains disabled;
power-collapse invalid logic states still need physical verification.[4]

Proposed firmware/operator protocol (requirements, not tested implementation):

1. On boot or observed supervisor RESET low, command ARM low and hold WDI
   statically low. Do not use an autonomous timer/PWM/DMA heartbeat that can
   continue after application failure. The watchdog output must also inhibit
   hardware independently of firmware.
2. After RESET is observed high and supplies/references are qualified, start
   deliberate high→low WDI pulses from successful safety-control-cycle checks.
   Use comfortably longer-than-100 ns high/low states (e.g. 10 µs) and a falling
   edge interval ≤100 ms as a provisional firmware target; verify worst-case
   scheduler jitter and temperature coverage before relying on it.
3. Stop transitions on reset/fault detection. Firmware polling cannot eliminate
   a pulse coincident with reset: accept a resulting stuck-low state as disabled.
   If RESET fails to recover, record a fault, require diagnosis/controlled power
   cycling, and do not promise that merely waiting or pulsing MR clears it.
4. After any recovery, maintain ARM low and require a qualified release then
   new manual reset press through the two DFFs, followed by the separate ARM
   procedure. Supervisor timeout/release is never itself a manual reset command.
5. Test frozen WDI high, low, open, autonomous toggling, transitions during reset,
   slow/fast rail ramps and stuck-reset recovery with current-limited logic-only
   fixtures before any power-stage test. TPS3823A is not an implicit substitute.

## Calculation change and its limits

Only the existing `corners()` high-VOL endpoint changes from .4 to .55 V in
`hardware/powerboard-reva/protection_calculations.py`. Executing it returned:

- nominal on/off: 60.3181818182 / 58.2045454545 V;
- screened on min/max: 59.3153867661 / 61.2259428259 V;
- screened off min/max: 57.3562920021 / 59.0581904968 V;
- illustrative 10 µs, 500 W rise from 60 V into 100 µF: 60.8276253030 V.

No claim that the 10 µs delay is guaranteed. The nominal low=.2 remains a
nominal assumption. Existing corner enumeration couples high-output and
low-output endpoint selection through one variable; it is not a complete
independent-corner/Monte-Carlo certification. The old `latch_next()` remains a
legacy level-reset model, **not a model of the two DFF correction**. Neither
issue is claimed closed by the calculation edit; new DFF behavior is tested separately in real ngspice.

## Independent bus-sink alternative — bounded proposal, not selected hardware

Disabling bridge gate drive does not prove elimination of energy entering a
DC bus from permanent-magnet machines. The current auxiliary-powered chopper
cannot be called independent of auxiliary loss. A candidate alternative is a
separately bus-powered emergency clamp with independent regulator, reference,
detection, gate drive and dump element, optionally backed by sized hold-up
energy. This is a design direction only, not a circuit/BOM ready to fabricate.

Before selection, bound worst continuous source power, BMS-open transient
energy, maximum mechanical speed, Cbus minimum, safe bus ceiling, detection
and turn-on latency, and minimum/maximum clamp resistance. For continuous
containment require Vclamp²/Rmax to exceed bounded input power after thermal
derating; for transients integrate net incoming energy and resistor pulse
energy. Calculate hold-up from rail consumption and the required interval
until qualified isolation or source energy cessation—not an arbitrary capacitor.

Independence risks include shared bus/ground/connector, common regulator surge
failure, startup dead zone, reference invalidity, reverse/backfeed paths,
short/open dump switch, resistor open/short, overtemperature, wiring inductance,
MOSFET SOA/avalanche and branch-fuse clearing. A bus-powered clamp still shares
the bus it protects. A battery-backed one adds battery state/charging/common
BMS failures. Source isolation must interrupt the actual rectification path
and contain inductive energy; gate disable alone is not isolation. No claim of
single-fault tolerance or regulatory safety compliance is made.

**Release remains BLOCKED:** independent cold review, complete electrical
margins/latency/energy analysis, real supply/entry/MCU/fast-trip completion,
zero unresolved ERC errors, and approved staged fault-injection tests are
required. No PCB and no energization approval follows from this document.

## Executed milestone evidence

- Native KiCad regeneration/export: 11 pages, 144 parts, 495 endpoints, 112 nets, 16 ICs. Checker retains exact endpoint/value/footprint comparison and unchanged three-error ERC identity checks; both normal and `-O` invocations pass. Native ERC `--exit-code-violations` exits 5: three errors, zero warnings, no new violations. No PWR_FLAG was added.
- Real ngspice negative old NAND fixture reproduces held-reset automatic enable at 3.3 V. Corrected two-DFF fixture reports 12 inhibit checkpoints at 0 V and five fresh-cycle enables at 3.3 V. Includes startup held reset, persistent fault, brownout/supervisor recovery, short bounce, stuck-high and stuck-low. Logs are `hardware/powerboard-reva/exports/restart-*-spice.log` and RED proof is `restart-old-contract-red.txt`.
- RC reset input is 10k 1% / 10n 5%, nominal 100 us, product endpoints 94.05–106.05 us excluding parasitics. This rejects the tested 10 us pulses, NOT arbitrary mechanical bounce; longer bounce can create legitimate clock edges. Manual-interface qualification remains open. Behavioral Schmitt thresholds are illustrative, not vendor-model proof.
- 15 tests pass in each normal and optimized run, including independently asserted actual exported DFF/fault-interface pin connectivity. `exports/fault-correction-tests.txt` records both runs. No transistor/vendor simulation, layout validation or hardware energization was performed.
- U7/U8 DCU pin assignment checked against TI table: Q=5, inverted Q=3 (do not swap based on lost PDF overbars). Inverter primary source: https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf .

### Explicit residual scope limits

The demonstrated level-held reset defect is corrected in the actual circuit. Full supply-corner Schmitt thresholds, ramp/power-off behavior, asynchronous-clear recovery/removal and arbitrary bounce are NOT closed; do not relabel this as a qualified power-on safety circuit. The two-DFF digital startup default assumes the supervisor asserts clear while logic becomes valid; analog collapse/startup still requires testing. Separate faults remove the diode margin defect, but the continuous rail-range guarantee remains unqualified as documented above. Sink independence remains a bounded design alternative, not an implemented second clamp.

## Sources

[1] https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf
[2] https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf
[3] https://www.ti.com/lit/ds/symlink/sn74lvc1g11.pdf
[4] https://www.ti.com/lit/ds/symlink/tps3823.pdf
[5] https://www.ti.com/lit/ds/symlink/lm339b.pdf
