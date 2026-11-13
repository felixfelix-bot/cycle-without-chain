# Pad-level audit: housekeeping and analog parts (PCB-02, continued)

STATUS: `PARTIAL_NOT_SAFE_TO_ENERGIZE`. Continues
`pad-audit-power-parts.md`. Six further parts now have datasheet-read pin maps.
Three could not be verified and are named below rather than assumed.

## 1. Verified in this pass

Method as before: read the manufacturer pin-function table, compare to the pin
name order in `pin-net-map.csv`, and check the topology the netlist implies.
A part counts as audited only if the datasheet was read — never inferred from
"surely it's the standard SOT-23 order".

### 1.1 LM5164DDAR — the two bus bucks (U500, U501)

TI SNVSAU4D, Table 4-1:

| Pin | Name | Dir | Pin | Name | Dir |
|---|---|---|---|---|---|
| 1 | GND | G | 6 | PGOOD | O |
| 2 | VIN | P/I | 7 | BST | P/I |
| 3 | EN/UVLO | I | 8 | SW | P |
| 4 | RON | I | 9 | EP | — |
| 5 | FB | I |  |  |  |

Module order: `GND, VIN, EN_UVLO, RON, FB, PGOOD, BST, SW, EP` — **matches
exactly**, 9 pins including the exposed pad.

Two useful details the datasheet adds, neither currently exploited:

- **EN/UVLO has two thresholds, not one.** Below 1.1 V the part is in shutdown
  with everything disabled; between 1.1 V and 1.5 V it is in *standby* with the
  internal VCC regulator live but not switching. The schematic holds EN low with
  100 kΩ, which lands it in shutdown — correct intent, but the standby band is
  not an accident and a future divider must not park in it.
- **PGOOD is open-drain**, and the datasheet requires a 10 k–100 kΩ pullup.
  Worth confirming the fitted value sits in that window when PCB-02 is next
  revisited.
- The datasheet's own 12 V / 1 A reference design uses **68 µH**, the same value
  as L501 — a useful independent corroboration of that choice, separate from the
  TDK land work.

### 1.2 AP63203WU — the 3V3 buck (U502)

Diodes AP63200/01/03/05 datasheet: **1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 BST**.
Module order matches. FB tied to the output for the fixed-3.3 V variant, which is
what the part requires.

This one mattered: the netlist has `LOGIC3V3_EXT` on pin 1, which looks like
driving a rail into an input. Pin 1 is FB, so it is the feedback tap — correct.

### 1.3 OPA333AIDBVR — FSR front-end buffers (U26, U28)

TI SBOS351E, SOT-23-5 column: **+IN 3, −IN 4, OUT 1, V+ 5, V− 2**.

Module: `1=OUT, 2=V-, 3=+IN, 4=-IN, 5=V+` — matches. The netlist confirms the
topology is a **unity-gain follower** (pin 4 tied to pin 1), which is right for a
high-impedance FSR buffer: no gain network to inject error into a zero-drift amp
whose whole point is offset.

### 1.4 TLV3202IDR — the fast comparators (U18–U23)

TI SLVSBO2, "Pin Functions: TLV3202":

| Pin | Name | | Pin | Name |
|---|---|---|---|---|
| 1 | 1OUT | | 5 | 2IN+ |
| 2 | 1IN− | | 6 | 2IN− |
| 3 | 1IN+ | | 7 | 2OUT |
| 4 | GND | | 8 | VCC |

Module order matches exactly.

### 1.5 TMUX1511PWR — the FSR sample muxes (U27, U29)

TI, TSSOP-14 column: **1 SEL1, 2 S1, 3 D1, 4 SEL2, 5 S2, 6 D2, 7 GND, 8 D3,
9 S3, 10 SEL3, 11 D4, 12 S4, 13 SEL4, 14 VDD**.

Module: `1=SEL1, 2=S1, 3=D1, 4=SEL2, 7=GND, 10=SEL3, 13=SEL4, 14=VDD` — the
seven pins it populates all match. The gaps are deliberate: the unused switch
channels are marked no-connect and the existing FSR connectivity test asserts
they are NC (pins 5, 6, 8, 9, 11, 12), which is consistent with this table.

Note the datasheet says **SEL pins have internal 6 MΩ pull-downs**, so an
un-driven select means OFF. That is a safe default for a sample gate, and it
means the `FSR_SAMPLE_ENABLE` 100 kΩ pull-down is belt-and-braces rather than
load-bearing.

### 1.6 BAT54S — the analog clamps (D40, D43)

Nexperia BAT54S, Table 2 Pinning information:

| Pin | Symbol | Function |
|---|---|---|
| 1 | A1 | anode of diode 1 |
| 2 | K2 | cathode of diode 2 |
| 3 | K1; A2 | cathode 1 / anode 2 — the series junction |

Module wires `1→PGND, 2→MCU_VREF, 3→SENSE`. Traced against the pinning table:

- diode 1: A1 (PGND) → K1 (SENSE) — clamps SENSE from going **below** ground
- diode 2: A2 (SENSE) → K2 (MCU_VREF) — clamps SENSE from going **above** VREF

That is exactly a rail-to-rail clamp on an analog input, which is the intended
protection for the FSR sense node. **Correct.**

One cosmetic defect: the local symbol names these pins `A`, `K`, `COM` rather
than `A1`, `K2`, `K1/A2`. The pin *numbers* are what the netlist and the
footprint use, and those are right, so this is a readability issue in the symbol
rather than an electrical one. Recorded, not fixed.

## 2. Could not be verified — and why that stays open

| Part | Attempt | Outcome |
|---|---|---|
| `STPS30100ST` | ST datasheet URL | fetch returned **0 bytes** |
| `PESD3V3U1UL` | Nexperia asset URL | returned a 423-byte error page, not a PDF |
| `2N7002` | Vishay 2N7002K datasheet | PDF fetched but `pdftotext` yielded **0 characters** — scanned image, no text layer |
| `TLV1701AIDBVR` | TI SBOS589D | partial: **IN+ 1, OUT 4, V+ 5** recovered from the table; the remaining pins were not legibly extracted |

These are recorded as **unverified**. For `2N7002` the failure is specifically
one of text extraction — the datasheet loaded but is an image — so OCR would
likely resolve it; that is a tooling step, not an engineering blocker.

## 3. Parts already covered elsewhere, not re-audited

`UCC27511`, `TPS3823`, `LM339B`, `LM4040-N`, `TLV760`, `R-78HB12-0.5` have
entries in `datasheet-sources.json` with SHA-256 hashes and were read during
PROT-03 or PROT-07. Those checks were about **logic levels**, which is a
different question from pin-to-pad truth. Their pin maps are not independently
re-verified here and should not be described as audited.

## 4. Running tally for PCB-02

| Status | Count | Parts |
|---|---|---|
| Pin map read and matching | 10 | DRV8353S, CSD19532Q5B, IRFP4568PbF, TPSI3052, LM5164, AP63203, OPA333, TLV3202, TMUX1511, BAT54S |
| Fetch failed / unreadable | 4 | STPS30100ST, PESD3V3U1UL, 2N7002, TLV1701 (partial) |
| Not yet attempted | 1 | the SN74LVC1G family pin maps |

### 4.1 STM32G474VET6 LQFP-100 — audited, 61/61 pins match

The highest-consequence part in the design: 100 pins, 61 of them populated, and
a single wrong number is invisible in review and fatal after fabrication.

**Getting the datasheet took three attempts.** ST blocked every direct fetch —
`curl` returned `HTTP/2 stream not closed cleanly` then `Empty reply from server`
— so the document was recovered from the Wayback Machine (the same route as the
TDK catalogue). 236 pages, real, not a proxy summary.

**Extracting Table 12 took several more.** `pdftotext -layout` interleaves the
six package columns into unparseable fragments, and the vision tool was
unavailable (`tier/worker-heavy is not a valid model ID`), so the table was
parsed with `pdfplumber` using the header's own x-coordinates:

```
WLCSP81 x≈69   UFQFPN48 x≈87   LQFP48 x≈108   LQFP64 x≈130   LQFP80 x≈151
TFBGA100 x≈170  LQFP100 x≈193  UFBGA121 x≈216  Pin name x≈271
```

The LQFP100 column is x≈193 and the pin-name column x≈271. Three pin names wrap
to a continuation row (`PC14-`, `PC15-`, `PF1-`) and were resolved by walking
upward from their pin number, then checked against the datasheet's own
`PF0-OSC_IN` / `PF1-OSC_OUT` pairing.

**Result: all 100 pins extracted and stored as
`data/stm32g474ve-lqfp100-pins.json`, and all 61 populated pins match.**

| Check | Result |
|---|---|
| Pin 6 | VBAT ✓ |
| Pins 8, 9 | PC14 / PC15 ✓ |
| Pins 12, 13 | PF0-OSC_IN / PF1-OSC_OUT ✓ |
| Pin 14 | PG10-NRST ✓ |
| Pins 35–37 | VSSA / VREF+ / VDDA ✓ |
| Pins 99, 100 | VSS / VDD ✓ |

### 4.2 The comparison is scripted and mutation-tested, not eyeballed

`audit_pin_names.py` compares `pin-net-map.csv` against the stored table.
It deliberately does **not** accept prefix matches, because `PA1` must not
equal `PA10` — the off-by-one that would survive a human review. It does accept
a datasheet suffix (`PF0` vs `PF0-OSC_IN`), which is presentational.

`tests/test_pin_audit.py` has one positive test and nine negative controls.
Three mutations to the audit logic were applied and all were caught:

| Mutation | Caught by |
|---|---|
| prefix match instead of exact (`PA1` == `PA10`) | `test_prefix_collision_is_not_accepted` |
| no suffix handling | 3 tests |
| a pin absent from the table treated as a pass | `test_missing_pin_in_table_is_caught` |

A passing audit that cannot fail is worse than no audit, because it manufactures
confidence. That is why the negative controls outnumber the positive case.

### 4.3 What PCB-02 still owes

**11 of 16 parts audited, zero pin errors found.** Remaining:

- **4 unverified parts** (§2): STPS30100ST, PESD3V3U1UL, 2N7002, TLV1701.
- **SN74LVC1G family** (1G04, 1G08, 1G11, 1G32, 1G74, 3G17) — five SOT-23-5 and
  one VSSOP-8 pin maps, not yet read.

PCB-02 therefore **stays OPEN**, but the largest risk is now retired.

## 5. What this pass did not change

No net, no value, no footprint. Every part examined was already wired correctly,
which is worth stating plainly: the audit found zero pin errors, and its value is
the *evidence* that they are absent, not a fix. The one exception is cosmetic
(BAT54S symbol pin names).
