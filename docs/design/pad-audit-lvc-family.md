# Pad-level audit: the SN74LVC1G family (PCB-02, final verifiable slice)

STATUS: `PARTIAL_NOT_SAFE_TO_ENERGIZE`. Completes the set of parts that can be
audited without a fabricated board. All six logic parts have datasheet-read pin
maps. One genuine documentation defect found; **no electrical errors**.

## 1. Verified — all six, all electrically correct

Source: TI datasheets fetched this session, hashes in `datasheet-sources.json`.

### 1.1 SN74LVC3G17DCUR — the Schmidt buffers (U11, U12)

TI SCES470F, "Pin Functions":

| Pin | Name | | Pin | Name |
|---|---|---|---|---|
| 1 | 1A | | 5 | 2Y |
| 2 | 3Y | | 6 | 3A |
| 3 | 2A | | 7 | 1Y |
| 4 | GND | | 8 | VCC |

Module order: `1A, 3Y, 2A, GND, 2Y, 3A, 1Y, VCC` — **matches exactly**. The
interleaved A/Y ordering (output 3 on pin 2, output 1 on pin 7) is the part's
real layout, not a transcription slip, so this is a good check of exactly the
kind of error a "natural order" assumption would introduce.

### 1.2 SN74LVC1G11DBVR — the 3-input AND gates (U13, U14, U16)

TI, SOT-23-6: **1 A, 2 GND, 3 B, 4 Y, 5 VCC, 6 C**. Module matches. Note pin 2 is
GND, not an input — the non-sequential numbering is correct for this package.

### 1.3 SN74LVC1G04DBVR — the inverter (U15)

TI: **1 NC, 2 A, 3 GND, 4 Y, 5 VCC**. Module matches, including pin 1 as NC.

`U15` pin 1 is tied to `PGND` rather than left floating. The datasheet marks pin 1
"no internal connection", so grounding it is permissible and is arguably better
than floating an unconnected lead; it is recorded here because "NC pin wired to
ground" is the sort of thing a reviewer should see stated rather than discover.

### 1.4 SN74LVC1G32DBVR — the OR gate (U24)

Datasheet package figure for DBV (SOT-23-5): **1 A, 2 B, 3 GND, 4 Y, 5 VCC**.
Netlist: pin 1 `OV_CMD`, pin 2 `BRAKE_DUMP_PERMITTED`, pin 4 `CHOP_CMD`.
An OR of two permissive sources driving the chopper command — correct.

### 1.5 SN74LVC1G08DBVR — the AND gates (U25, U510)

Same DBV pinout. `U25`: 1 `BRAKE_DUMP_PWM`, 2 `TIMER_BREAK_OK`, 4
`BRAKE_DUMP_PERMITTED`. `U510`: 1 `CTRL_PG`, 2 `MAIN_PROVEN_IN`, 4 `DRIVE_EN`.
Both AND of two conditions — correct.

### 1.6 SN74LVC1G74DCUR — the fault-latch DFFs (U7, U8)

TI: **1 CLK, 2 D, 3 Q̄, 4 GND, 5 Q, 6 CLR, 7 PRE, 8 VCC**. Module:
`CLK, D, Q_N, GND, Q, CLR_N, PRE_N, VCC` — matches, and the `_N` suffixes are
semantically right: the datasheet describes CLR and PRE as "pull low to set",
i.e. **active-low**, so naming them `CLR_N`/`PRE_N` is accurate rather than
decorative. Both are tied to `SAFETY3V3` on U7 and U8, which holds them
inactive — correct for a latch that must not be asynchronously forced.

## 2. The one real defect: three gates have unnamed pins

`U24`, `U25` and `U510` carry the **stock KiCad symbol** `74xGxx:74LVC1G32` /
`74LVC1G08`, whose pins are named `~` (unnamed). The netlist is electrically
correct, but the pin-name ledger records:

```
U24  pin 1: ~  -> OV_CMD
U24  pin 2: ~  -> BRAKE_DUMP_PERMITTED
U24  pin 4: ~  -> CHOP_CMD
```

That is a **documentation defect, not an electrical one** — the connections are
right — but it matters for two reasons:

1. `audit_pin_names.py` cannot compare `~` against a datasheet name, so these
   three parts are invisible to the automated check. The audit passes on them
   for the wrong reason.
2. A reviewer reading the schematic cannot tell which pin is A, B or Y, so a
   wrong connection would look identical to a right one.

The correct fix is to give them the project's own symbols with named pins, as
the other LVC parts already have (`protection_circuit.py` builds `LVC1G11`,
`LVC3G17`, `LVC1G74` with explicit pin-name lists; `brake_intent_circuit.py`
uses the stock symbol instead). **Not fixed here** — it changes symbol lib_ids in
a safety-signal path, and that deserves its own change with the FSR connectivity
tests re-run, not a drive-by edit at the end of an audit.

Recorded as an open item so it is not silently forgotten.

## 3. Running total for PCB-02

| Status | Count | Parts |
|---|---|---|
| Pin map read, matches | 16 | DRV8353S, CSD19532Q5B, IRFP4568PbF, TPSI3052, LM5164, AP63203, OPA333, TLV3202, TMUX1511, BAT54S, 3G17, 1G11, 1G04, 1G32, 1G08, 1G74 |
| Read but symbol pins unnamed | 3 | U24, U25, U510 — see §2 |
| Unverified (fetch failed) | 4 | STPS30100ST, PESD3V3U1UL, 2N7002, TLV1701 (partial) |

**Zero electrical pin errors found across every part audited.** The value of this
work is that the absence is now evidence.

## 4. What PCB-02 still owes

Three things, none of which a schematic-only pass can close:

1. **The 4 unverified parts.** Two need a different source (ST and Nexperia
   blocked or served error pages); `2N7002` needs OCR because the PDF has no text
   layer; `TLV1701` needs the pin table re-read from the correct page.
2. **The `~` pin names** in §2 — a symbol change, not a net change.
3. **Land patterns for the parts that have none verified.** Only L501 has a
   vendor-transcribed land. The TO-247 is a KiCad library default and the QFN-40,
   HSOP-8 and VSSOP-8 lands are library defaults too. PCB-02's claim is "pin and
   pad truth"; the *pad* half is unverified for every part except L501, and
   cannot be verified against vendor drawings until those drawings are fetched.

That last item is the honest reason PCB-02 stays OPEN rather than closing on a
clean pin sweep: half the gate's name is about pads, and pads are almost entirely
unaudited.
