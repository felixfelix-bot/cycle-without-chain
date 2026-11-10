# DRIVE12 output protection, L501 qualification, and the PGOOD domain split

> **STATUS: DESIGN CHANGE ON AN UNSAFE PROTOTYPE. NOT SAFE TO ENERGIZE.**
> Schematic only. No PCB, no routing, no measurement, no energization, no
> purchase. The branch closes three review findings with circuits and tests; it
> does not make the board safe and it does not close the remaining gates.

Branch `pr/rail-ovp-pgood`, based on `github/master` = `6134e5f`
(`Merge pull request #11 from felixfelix-bot/pr/status-files-current`).
Worktree `~/worktrees/cycle-rail-ovp`.

This document covers the three findings quoted from
[`rail-partition-review.md`](rail-partition-review.md) §Defects found 3, 4, 5
and registered as RAIL-01, RAIL-02, RAIL-04 in
[`open-gates-register.md`](open-gates-register.md).

---

## 0. What changed, exactly

Nets that did not exist before this branch: `DRIVE_PG`, `DRIVE_OV_SENSE`.
Nets that changed membership: `ANALOG_OK` (lost `U501.6`), `DRIVE_UVLO` (gained
`U503.4`), `SINK12` (gained `R521.1`, `U503.5`), `REF2V5` (gained `U503.1`).

| Ref | Before | After |
|---|---|---|
| `U501.6` (PGOOD) | `ANALOG_OK` | `DRIVE_PG` |
| `U503` | did not exist | new `TLV1701AIDBVR` OVP comparator |
| `R521` | did not exist | 47k pull-up `SINK12` → `DRIVE_PG` |
| `R523` | did not exist | 649k 0.1 % `DRIVE12` → `DRIVE_OV_SENSE` |
| `R524` | did not exist | 118k 0.1 % `DRIVE_OV_SENSE` → `PGND` |
| `C523` | did not exist | 100p C0G `DRIVE_OV_SENSE` → `PGND` |
| `L501` | `68u MSS1246T-683MLC 20%` | `68u SPM10065VT-680M-D 20% AEC-Q200 candidate` |

Unchanged and re-asserted by tests: `R402`/`R412` 0 Ω inhibits on
`MAIN_EN`/`PRE_EN`, `R519` 0 Ω on `MAIN_PROVEN_IN`, and the fitted 0 Ω analog
links `R67`/`R68`. No pin type was edited. No `PWR_FLAG` was added. No ERC
violation was waived.

---

## 1. DEFECT 1 — no output OVP on `U501` → `DRIVE12`

### 1.1 What the LM5164 datasheet actually provides (and does not)

Verified in TI **SNVSAU4D** (SEP 2018, revised FEB 2026), which is the cached copy
at `docs/research/controller/lm5164.pdf`, SHA-256
`cce03619fbe13951eea47458cd45e140361637d8fef32ae143b82b16d597e32d`:

| Datasheet location | Mechanism | Covers an output over-voltage? |
|---|---|---|
| §6.3.6 Current Limit + Figure 6-1, §5.5 `IPEAK1`/`IPEAK2` 1.25/1.5/1.75 A, `IVALLEY` 0.95/1.2/1.4 A | cycle-by-cycle peak limit with valley foldback, "limits the average output current to less than 1.5 A" | **No.** It bounds *current*, not voltage. An unloaded runaway draws almost no current, so the limit never engages. |
| §6.3.11 Thermal Protection, §5.5 `TSD` 175 °C / 10 °C hysteresis | junction-temperature shutdown, non-latching | **No.** It protects the die from heat, at a die temperature the load-side parts would not survive. |
| §6.3.9 / §5.5 `VEN-RISING` 1.45/1.5/1.55 V, `VEN-FALLING` 1.35/1.4/1.44 V | precision enable / UVLO | **No.** It is an input, and it is the *handle* an external OVP can pull. |
| §6.3.10 PGOOD, §5.5 `VPG-UTH` 1.105/1.14/1.175 V, `VPG-LTH` 1.055/1.08/1.1 V | open-drain *indicator*, pull-up ≤ 14 V, 10k–100k | **No.** It is a status output with no actuator. To be precise: `VPG-UTH` trips on `VFB` **rising** past 1.14 V typ, i.e. the LM5164 does notice an over-voltage — and does nothing about it except release its open-drain pin. That is a monitor, not protection. |
| §6.3.3 Regulation Comparator, `VREF` 1.181/1.2/1.218 V | COT feedback comparator | **No.** This is the mechanism that *fails* when `R512` opens. |

There is no over-voltage protection block anywhere in the functional block
diagram (§6.2) or the feature list (§6.3). The datasheet's own vocabulary is
UVLO, current limit, thermal shutdown, soft start, PGOOD. **The defect is real
and the silicon does not cover it.**

### 1.2 The fault, quantified

`DRIVE12` setpoint is `VREF·(RFB1+RFB2)/RFB2` = 1.2 V × (453k+49.9k)/49.9k =
**12.10 V**. If `R512` (the lower leg) opens, no current flows in the divider,
`VFB = VOUT`, and the COT comparator sees `VFB > VREF` permanently — so it never
issues another on-pulse. The rail is then not *driven* to 58.4 V; it is
*undefended* and whatever charges it wins:

- the inductor and high-side FET are off, so the rail decays into its load; but
- the described fault is "FB floats to VOUT and DRIVE12 rises toward VIN, up to
  58.4 V", which is what happens once anything re-charges the node — a hot-plug,
  a bridge `VM` back-feed through `U1`/`U2`, or `L501` ringing at the next
  restart. The review's 58.4 V is the correct **upper bound** to design against,
  so this branch designs against 58.4 V regardless of which recharge path is
  eventually proven.

Against that bound:

- AP63203 `U502` absolute maximum: **35 V DC, 40 V for 400 ms** → 1.67× over.
- `C513`/`C514`/`C517` are rated **25 V** → 2.34× over.
- `U1`/`U2` `VM` absolute maximum is 80 V → they survive, which is exactly why
  the failure is invisible until `U502` and three capacitors are destroyed.

### 1.3 Option (a): second FB divider leg + comparator — **CHOSEN**

A comparator watches `DRIVE12` through its **own** divider, compared against the
board's existing 2.5 V reference, and pulls the LM5164 enable node low.

**Why the enable node and not the FB node.** Pulling `FB` low tells a COT
regulator "output is below setpoint" and makes it switch *harder* — the
opposite of protection. `FB` is also absolute-maximum 5.5 V (§5.1), so it is not
a node a 58 V-referenced detector may sit on. `DRIVE_UVLO` is the `EN/UVLO`
divider node: pulling it to ~0 V is below both `VEN-FALLING` (1.44 V max) and
`VSD-FALLING` (0.45 V), so the converter shuts down and stays down while the
fault persists.

**Why `DRIVE_UVLO` and not `DRIVE_EN`.** `DRIVE_EN` is driven by `U510.4` (a
push-pull `74LVC1G08` output). An open-drain comparator on that net would fight a
driven high. `DRIVE_UVLO` is a passive divider node (`R514` 82k from
`DRIVE_EN`, `R515` 100k to `PGND`), so an open drain can only pull it down. No
contention, and the OVP works even if `U510` is stuck high.

**Sizing.** Trip at 16.25 V nominal — clear of the 12.6 V worst-case normal
rail, and below the 25 V capacitor rating with 8.75 V of margin.

```
Rth(top)  = 649k, Rth(bot) = 118k
trip_nom  = 2.500 V x (649k + 118k) / 118k = 16.250 V
```

| Corner | Assumption | Trip |
|---|---|---|
| nominal | 2.500 V ref, exact resistors | **16.250 V** |
| low (earliest, safe side) | ref −0.1 %, 649k −0.1 %, 118k +0.1 % | **16.206 V** |
| high (latest) | ref +0.1 %, 649k +0.1 %, 118k −0.1 % | **16.294 V** |
| high + 1 mV comparator `VOS` | TLV1701 `VOS` 300 µV typ | 16.294 V |

Normal-rail headroom: `16.206 − 12.600 = 3.606 V`. Capacitor headroom at the
worst trip: `25.0 − 16.294 = 8.706 V`.

**Detection lag must be computed, not assumed.** Worst-case `dV/dt` if the
converter does keep sourcing is its peak current into the fitted bank:

```
dV/dt = IPEAK / COUT = 1.75 A / 54 uF = 32.4 V/ms
```

The sense filter is a real lag. With `C523 = 100 pF`:

```
Rth  = 649k || 118k        = 99.85 kohm
tau  = 99.85k x 100p       = 9.985 us
lag  = 5 x tau x dV/dt     = 1.62 V
Peak = 16.294 + 1.62 + 0.10 (propagation + tolerance)  = 18.02 V
```

18.02 V is **below** the 25 V capacitor rating by 7 V and **below** the AP63203
35 V DC absolute maximum by 17 V. This is the number the first draft of this
branch got wrong twice: with `C523 = 1 nF` the lag is 16.2 V (peak ≈ 32.5 V —
*above* the capacitor rating, i.e. the filter defeats the protection), and with
100 nF it is 324 V (protection entirely defeated). The filter is 100 pF C0G for
this reason, and the test recomputes `tau` from the exported values.

**Why this over option (b), a clamp/TVS.** See §1.4 — the clamp cannot be sized
to survive the same 58.4 V/54 µF energy in a credible SMB/SMA part without
becoming a second failure mode, and it protects only the capacitor bank, not
`U502`'s 35 V input. The comparator acts on the *source*, which protects every
downstream part at once.

**What this does NOT cover (residual risk), stated plainly:**

1. **It is not latching.** A permanently open `R512` produces a hiccup: the rail
   trips at ~16.3 V, `EN` falls, the rail decays, `DRIVE_UVLO` is released, the
   converter soft-starts (3 ms, §6.3.4), and if the divider is still open it
   trips again. The rail therefore *cycles* between roughly 0 and 18 V instead of
   sitting at 58.4 V. That is a large improvement and still not a safe state —
   the load sees repeated 18 V excursions. A latch is deliberately **not** added
   because latching a delayed rail into the always-on fault memory is exactly the
   coupling defect RAIL-04 is closing. **Open gate: decide where the latch
   belongs.**
2. **It cannot detect a fault that removes `SINK12`.** `U503` is powered from
   `SINK12`; with no `SINK12` there is no OVP. `SAFETY3V3` was rejected as the
   supply because it is a 3.3 V rail and the TLV1701 output must pull
   `DRIVE_UVLO` low against `R514` — a 3.3 V pull-up through 82k cannot hold the
   node below 1.44 V once the divider is considered. `SINK12` is the correct
   domain: it is the always-on rail and it is present whenever the OVP matters.
3. **It does not protect `DRIVE12` from a fault that also destroys `SINK12`.**
   A single-event over-voltage that takes out both rails together has no
   independent detector.
4. **`DRIVE12` is still not fused.** The OVP is a voltage detector, not a
   current interrupter. A short on `DRIVE12` still relies on the LM5164 current
   limit.
5. **Corners are computed, not measured.** Reference drift over temperature is
   taken as 0.1 % (LM4040A grade); the installed part's actual tempco is not
   calibrated, and `2.5 V` is the reference's nominal, not its measured value.

### 1.4 Option (b): clamp/TVS across `DRIVE12` — evaluated, rejected as primary

A TVS is the obvious reflexive answer and it is the wrong *primary* here.

- **Clamp voltage window is narrow and the standoff is close.** Standoff must
  exceed the 12.6 V worst-case rail with margin; the clamp must be below 25 V
  with margin. A 15 V standoff SMB-class part clamps around 24.4 V at its rated
  peak pulse current, i.e. essentially *at* the capacitor rating with no margin,
  and its clamping voltage rises with current. The window 12.6 V → 25 V leaves
  little room for a part whose `VCL` is specified at a pulse current we cannot
  bound.
- **The energy is not a transient.** The fault is a *continuous* over-voltage to
  58.4 V, not an 8/20 µs surge. A TVS asked to hold 58.4 V off a 54 µF bank
  continuously is a dissipation problem: at a clamp of ~20 V into a source that
  can deliver 1.75 A, `P = 20 V × 1.75 A = 35 W` in an SMB package, which it
  cannot survive. It would fail short, and a shorted TVS across `DRIVE12` is a
  new failure mode that the LM5164 current limit would then have to survive
  indefinitely.
- **It does not protect `U502`'s input.** A clamp at ≤25 V protects the
  capacitors. `U502`'s absolute maximum is 35 V DC, so the clamp "protects" a
  part that was never the binding constraint while doing nothing for the parts
  that are.
- **Both would be needed anyway.** The clamp cannot interrupt the source, so it
  is a supplementary energy absorber at best. This branch does not fit one,
  because fitting one without a bounded pulse current would be a part whose only
  justification is that TVS diodes are conventional.

A clamp is a legitimate **future** addition once the source impedance and the
required hold-off duration are bounded by measurement. It is recorded as an open
gate, not silently omitted.

### 1.5 Option (c): LM5164-integrated protection — **does not exist**

Covered in §1.1 with the exact table references. The only over-voltage-adjacent
behaviour in the part is the `PGOOD` `VPG-UTH` comparator (1.14 V typ on `VFB`
rising), which releases an open-drain *indicator* and takes no action. There is
no OVP, no hiccup-on-overvoltage, and no output clamp. Any claim otherwise would
be a marketing claim; the datasheet does not support one.

---

## 2. DEFECT 2 — `L501` not qualified against the converter's own limit

### 2.1 The old part, against a stated rule

`MSS1246T-683MLC` (Coilcraft Document 712): 68 µH, `Isat` 2.26 A at 10 % drop
(2.54 A at 20 %, 2.74 A at 30 %), `Irms` 1.30 A at 20 °C rise (1.80 A at
40 °C), `DCR` 167.3 mΩ typ / 185.9 mΩ max.

The margin rule applied in this branch, stated once and applied to both parts:

- **peak** ≤ 0.80 × `Isat`(10 % drop), because the LM5164 ceiling can be reached
  on any start-up into a discharged output;
- **sustained** ≤ 0.80 × `Irms`(40 °C rise), because the enclosure is sealed and
  the worst-case ambient applies.

Sustained current is taken as the mean of the peak and valley limits,
`(1.75 + 1.40)/2 = 1.575 A`, which is the datasheet's own averaging point
(§6.3.6: "limits the average output current to less than 1.5 A" at the *typical*
1.5/1.2 A thresholds; the arithmetic here uses the *maximum* window).

| Quantity | Old part | Rule | Verdict |
|---|---|---|---|
| peak `Isat` margin | 2.26 / 1.75 = **1.29×** | ≥ 1.25× (1/0.8) | fail |
| sustained `Irms`(40 °C) margin | 1.80 / 1.575 = **1.14×** | ≥ 1.25× | fail |
| `Irms`(20 °C) ratio at 1.75 A | 1.75 / 1.30 = **1.35×** | — | the review's number, reproduced |
| I²R at 1.75 A | 1.75² × 0.1859 = **0.569 W** | — | the review's 0.51 W used typ 0.167 Ω; max DCR is worse |

### 2.2 `L502` is out of scope

`L502` (the AP63203's 3.9 µH) is flagged by the milestone but is a different
converter with a different limit. This branch does not touch it and a test
asserts `L500`/`L502` are unchanged.

### 2.3 The reselected part

**TDK `SPM10065VT-680M-D`**, from the vendor datasheet
`inductor_automotive_power_spm10065vt-d_en.pdf` (20200702), characteristics table,
68 µH row:

```
68 uH ±20 %, 100 kHz, DCR 121 mOhm typ ±10 %
Isat 5.1 A typ (dL = -20 %)   7.0 A typ (dL = -30 %)
Itemp 3.4 A typ (dT = 40 deg C)
AEC-Q200, operating range -55 to +155 C including self-heating
```

| Quantity | New part | Rule | Verdict |
|---|---|---|---|
| peak vs `Isat`(−20 %) | 5.1 / 1.75 = **2.91×** | ≥ 1.25× | pass |
| peak vs `Isat`(−30 %) | 7.0 / 1.75 = **4.00×** | ≥ 1.25× | pass |
| sustained vs `Itemp`(40 °C) | 3.4 / 1.575 = **2.16×** | ≥ 1.25× | pass |
| I²R at 1.75 A | 1.75² × 0.121 = **0.371 W** | better than 0.569 W | pass |

Even taking the **most pessimistic** published saturation point (5.1 A at
−20 %) the part clears the 0.80 rule by 2.91×, so the selection does not depend
on which drop criterion is quoted.

### 2.4 What is still open about `L501`

- **The footprint is deliberately blank.** `SPM10065VT-680M-D` is 10.5 × 10 ×
  6.5 mm; no KiCad land pattern has been compared to the vendor's recommended
  pad geometry. Filling in a stock `L_12x12mm` land would be an unverified claim,
  so the field is left empty and this is an explicit gate.
- **"Candidate" is in the value string on purpose.** The part number, ratings and
  package are source-verified; **price and stock are not**, and this branch makes
  no availability claim.
- **`DCR` ±10 % means the 0.371 W is a typical, not a maximum,** figure.
- **Core loss at 300 kHz is not included** in the I²R number.
- **`L500` (the CTRL3V3 converter's identical old part) is untouched.** It is the
  same `MSS1246T-683MLC` on a converter with the same topology; RAIL-03 already
  records it as an open gate. Fixing it here would be an unrequested scope
  change, so it is called out instead.

---

## 3. DEFECT 3 — `U501.6` PGOOD gating the always-on `ANALOG_OK` chain

### 3.1 Why the old wiring was wrong

`U501.6` is `PGOOD`, open drain, pulled up by `R51` (4k7) to `SAFETY3V3`, and it
joined `U6`'s three open collectors on `ANALOG_OK` → `U11` → `ANALOG_CLEAN` →
`U13` → `FAULTS_OK` → `HEALTHY`.

`DRIVE12` is a **delayed** rail: it is gated by `DRIVE_EN = CTRL_PG AND
MAIN_PROVEN_IN`, and `MAIN_PROVEN_IN` is held low by the fitted `R519` 0 Ω
inhibit. So `DRIVE12` is off by construction in the default state → `VFB = 0` →
`PGOOD` pulls low → `ANALOG_OK` low → `HEALTHY` low.

The failure direction is safe, but the *architecture* is wrong: an always-on
safety chain whose verdict depends on a rail that is deliberately off cannot
report "the always-on safety domain is healthy" — it can only ever report "the
always-on domain is healthy **and** the drive domain happens to be up". That
conflates two domains and, worse, means a genuine sink-side fault and a
deliberately-inhibited drive rail produce the identical verdict. It also makes
the always-on chain depend on a part (`U501`) it was partitioned away from.

The write-up in the review offered two honest options: move `PGOOD` off the
chain, or state that a healthy verdict requires the drive domain. This branch
takes the first, because the second would have to explain why a sink-side fault
can be masked by drive state and there is no such explanation.

### 3.2 What was done

`U501.6` now drives `DRIVE_PG`, a drive-domain status net, pulled up by a new
`R521` (47k) to `SINK12`. Nothing on `DRIVE_PG` reaches `U11`/`U13` or any other
member of the safety chain; a test asserts exactly that, and a negative control
re-injects the old `ANALOG_OK` wiring and requires the test to fail.

**Pull-up choice.** §6.3.10 requires a pull-up "to a DC supply not greater than
14 V", 10k–100k, and the absolute maximum on the pin is 14 V. `SINK12` is
12.0 V nominal, 12.36 V worst case — inside 14 V. `SAFETY3V3` (3.3 V) would also
be legal and would be *safer against the 14 V limit*, but it is the wrong domain
for the same reason as above: a drive-domain status should not be pulled up by
the sink domain's rail, or the sink rail's loss becomes a drive status change.
`SINK12` keeps the status readable whenever the always-on domain is alive, which
is exactly the domain that needs to read it.

### 3.3 What a healthy-drive indication now depends on

`DRIVE_PG` high now means, and only means:

- `SINK12` is up (the pull-up source), **and**
- `U501` is regulating: `VFB > 0.95 × VREF` (`VPG-UTH` 1.14 V typ), i.e.
  `DRIVE12` is within ~5 % of its 12.10 V setpoint, **and**
- the LM5164's internal PGOOD switch is off and the 5 µs rising-edge deglitch has
  elapsed.

It does **not** mean: `DRIVE12` is within any tolerance the OVP agrees with
(the OVP trips at 16.25 V, well above `VPG-UTH`'s ~95 % band, so there is a real
window where `DRIVE_PG` is still high and the OVP has tripped — by design, the
OVP is a protection threshold, not a status threshold); the drive bridge is
enabled; the bridge is not faulted; or `DRIVE12` is free of ripple.

It is now a **pure status output with one consumer** and, deliberately, **no
consumer at all in the safety chain**. That is the point of the change. Where it
should be consumed — MCU GPIO, a drive-domain fault latch, or nothing — is left
as an open decision rather than invented, because inventing a consumer would be
re-introducing coupling under a new name.

### 3.4 The better option, and why it was not taken

The strictly better architecture is a **drive-domain fault latch** that takes
`DRIVE_PG`, the OVP state, and the DRV8353 `nFAULT` lines, and presents one
`DRIVE_FAULT` bit to the MCU — still outside `ANALOG_OK`. That is the right end
state.

It is not done here because it requires a latch with a defined reset domain, a
set/reset priority, and a decision about whether a drive fault may inhibit drive
re-enable without operator action. Those are design decisions the operator owns,
not implementation details. Doing it now would repeat the original defect at one
remove: a status net with an invented consumer. `DRIVE_PG` is therefore landed as
a clean, single-consumer status net, and the latch is recorded as the next gate.

---

## 4. Verification

Reproduced on `pr/rail-ovp-pgood`. Full detail in `REPORT.md`; the numbers:

| Check | Result |
|---|---|
| Hardware suite, normal | **49 tests, OK** |
| Hardware suite, `python3 -O` | **49 tests, OK** |
| RED run before implementation | 3 errors: `U501.6` on `ANALOG_OK`, no `U503`, `L501` unchanged |
| Native export | 387 components, 220 nets, 1142 connected pins, 51 explicit NC, 32 pages |
| Strict ERC | **exit 5, 10 errors, 0 warnings** — unchanged from `master`, not waived |
| Generator fidelity | netlist regenerated from source in this branch |

The ERC count is **10**, the same identities as `master` (enumerated in
`verify_exports.py`), and this branch adds none. Two of the ten are
`U1.3`/`U2.3` `VM` on `DRIVE12`, still an honest
`power_pin_not_driven` because `L501` is a passive inductor between `DRIVE_SW`
and `DRIVE12` — ERC cannot see a power source through it. Nothing was silenced:
no `PWR_FLAG`, no pin-type edits, no waivers.

Tests assert the topology through the **native KiCad XML export** by
`(ref, pin) → net`, not a manifest count, and each positive assertion has a
negative control that must fail.

---

## 5. Remaining unqualified items

Carried forward honestly, not closed by this branch:

1. **`DRIVE12` OVP is non-latching** and hiccups on a permanent divider-open.
   Where the latch lives is undecided (§1.3.1).
2. **`DRIVE12` clamp/TVS is not fitted.** Its energy and hold-off are unbounded
   without measurement (§1.4).
3. **`DRIVE12` is not fused.** A rail short still relies on LM5164 current limit.
4. **`L501` footprint unverified** against the vendor land pattern; price and
   availability unverified; core loss excluded; `DCR` ±10 %.
5. **`L500` (CTRL3V3) still carries the old `MSS1246T-683MLC`** — RAIL-03, same
   defect class, unrequested scope.
6. **`DRIVE_PG` has no latch consumer** — the drive-domain fault latch is the
   correct next step (§3.4).
7. **No measurement of any kind.** No thermal, no start-up, no effective
   capacitance at bias, no EMI, no SOA, no hot-plug. The board has never been
   built or energized.
8. **RAIL-11 ERC completeness** (10 undriven power pins) is unchanged and
   unresolved by design, per the existing register.
