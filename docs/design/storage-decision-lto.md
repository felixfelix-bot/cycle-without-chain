> **STATUS: OPERATOR DECISION RECORD — NOT A PURCHASE, PACK OR BOARD RELEASE.**
> Chemistry is frozen by the operator. Cell model, BMS part, thresholds, pack
> assembly and cold/full charge acceptance are NOT frozen. Nothing in this
> document authorises energising the powerboard, assembling a pack or riding.

# Storage decision: LTO pack plus supercapacitor buffer

| Provenance | Value |
|---|---|
| Date / branch | 2026-11-10 / `pr/storage-lto-decision` |
| Decision owner | Operator (`c08r4d0r`) |
| Inputs | `docs/design/short-buffer-storage.md`, `docs/design/storage-review.md`, `docs/design/open-gates-register.md` |
| Reproduce | `python3 analysis/storage/model.py`; `python3 -m unittest discover -s analysis/storage -v` |
| Scope exclusions | BMS part selection, pack mechanical/thermal build, charge-acceptance testing, cost commitment |

## 0. Decision

**D0 — Direction: LTO battery for usable energy plus a supercapacitor buffer for
power.** Chosen by the operator from four options; recorded here as a decision,
not as an engineering result.

The split follows the duty the project has already fixed: storage is a
**short-duration buffer for starts, stops and brief deficits**, with no
powered-range target. Two different problems are therefore being solved:

- **Energy** (sustaining a deficit for tens of seconds): a battery.
- **Power** (absorbing and delivering brief peaks, and surviving very frequent
  partial cycles): supercapacitors.

LTO was chosen over LFP for cycle life, cold-charge tolerance and safety, at a
higher cost per Wh. That trade is the operator's, and this record does not claim
LTO is cheaper, lighter or better on every axis.

**D1 — Preferred LTO series count to evaluate first: 20s.** Using Toshiba SCiB
2.9 Ah high-power cells at 2.4 V nominal, 2.8 V maximum and 1.8 V minimum
(catalogue values, not a qualified pack specification):

| String | Max V | Nominal V | Min V | Cells-only Wh | Cells-only kg |
|---|---:|---:|---:|---:|---:|
| 18s | 50.4 | 43.2 | 32.4 | 125 | 2.70 |
| **20s** | **56.0** | **48.0** | **36.0** | **139** | **3.00** |
| 22s | 61.6 | 52.8 | 39.6 | 153 | 3.30 |

**20s is the notable result:** its maximum of 56.0 V sits inside the current
36–58.4 V bus envelope, its nominal of 48.0 V matches the 13s lithium-ion
nominal used elsewhere in the design, and its minimum of 36.0 V coincides with
the declared bus minimum. 22s exceeds the 58.4 V ceiling and 18s sits below the
nominal the rest of the design is built around.

This is a **window fit, not a compatibility proof.** Loaded terminal voltage under
pulse current, tolerance stack-up, fuse and disconnect behaviour and the
converter question below all remain open.

**D2 — Supercapacitor buffer remains a separate, optional branch.** Retain the
Eaton XV3550 20s string screened in `short-buffer-storage.md` as the candidate
power buffer (1.24 kg cells, ~3.9 Wh usable between 50 and 25 V). It is **not
additive by default**: `D4` of that document still stands — do not add the buffer
unless repeated braking demonstrably exceeds LTO charge acceptance or cold
operation requires it. LTO's acceptance is high enough that the cap bank may not
earn its mass.

**D3 — Do not select the buffer or its converter before charge acceptance is
measured.** The order of work is LTO pack interface first, then a measured
acceptance test, then a decision on whether the cap branch and any bidirectional
converter are worth their mass.

## 1. What LTO buys and what it costs

Cited from the manufacturer and reseller pages in the storage analysis:

- **Cycle life:** Toshiba states the 2.9 Ah SCiB cell keeps over 80% capacity
  after **40,000 cycles at 10C and 35 °C**. The high-energy SCiB cells are
  quoted at 20,000 cycles to 70%, not 80% — do not mix the two figures.
- **Charge rate:** the same cell is offered for 10C charge and discharge, which
  is the property that makes it plausible as a regen sink without a large
  parallel count.
- **Cold behaviour:** LTO is the chemistry usually claimed to accept charge well
  below 0 °C, where LFP and graphite cells must be inhibited. **This claim is
  NOT qualified for the 2.9 Ah cell here.** A generic LTO cold-charge claim does
  not transfer to a specific part; STO-03 stays open until the exact cell is
  tested.
- **Cost:** LTO is the most expensive option per Wh of the four considered. No
  price is adopted in this record — the BOM's cost fields remain
  "unverified quote required".

Honest counterweights, recorded so this decision is not later misread as an
efficiency win:

- **Mass per Wh is poor.** 139 Wh of cells for 3.0 kg is roughly 46 Wh/kg at cell
  level, before BMS, enclosure, fusing and mounting. An LFP pack of comparable
  energy would be lighter.
- **Low nominal voltage per cell** means more cells, more interconnects and more
  balance channels for a given bus voltage.
- **40,000 cycles is a datasheet figure at a stated temperature and rate**, not a
  guarantee for this duty. If the buffer never cycles heavily, the cycle-life
  advantage buys nothing and the cheaper chemistry would have been correct.
  That risk is accepted knowingly.

## 2. Which gates this closes and which it does not

| Gate | Effect of this decision |
|---|---|
| ARCH-06 (storage chemistry and BMS) | **Partially addressed.** Chemistry and series count direction are now frozen. BMS part, thresholds, disconnect behaviour and cold/full acceptance remain OPEN. |
| CX-02 (bus maximum contradiction) | **Narrowed, not closed.** A 20s LTO ceiling of 56.0 V maximum is *below* the 58.4 V contract figure. The bus maximum should be reconciled to the selected pack's real ceiling rather than left at 58.4 V. |
| STO-01 (converter option) | **Unchanged and still blocking.** Whether the buffer can deliver into a 36 V bus without a converter depends on the final window and loaded voltage. |
| STO-02 (cell pulse/thermal maps) | **Open.** Series count is chosen; pulse and thermal derating for this duty are not. |
| STO-03 (cold and full-SOC acceptance) | **Open and now more important**, because cold tolerance is part of why LTO was chosen. It must be measured, not assumed. |
| STO-04 (supplier revisions) | **Open.** The cell figures above rest on catalogue text; re-fetch exact revisions and confirm units before purchase. |
| STO-05 (chronological transient model) | **Open.** Net integrals are still not capacity. |
| STO-06 (recovery after refusal) | **Open.** |

**No gate moves to closed by this record.** A chemistry choice removes an option,
not a risk.

## 3. Next actions, in order

1. Re-fetch the Toshiba SCiB 2.9 Ah datasheet and confirm nominal/maximum/minimum
   voltage, continuous and pulse current, temperature limits and cycle-life
   conditions against the exact order code.
2. Obtain quotes for LTO cells and BMS; record them in the storage BOM rather than
   assuming cost.
3. Decide whether the bus maximum becomes 56.0 V (20s LTO) and propagate that to
   the charge-control and clamp thresholds — resolving CX-02.
4. Characterise charge acceptance at temperature on the selected cell before
   deciding whether the supercapacitor branch is justified.
5. Only then revisit converter sizing (STO-01).

## 4. Sources

- Toshiba SCiB high-power 2.9 Ah cell: 40,000 cycles at 10C/35 °C to 80%,
  2.4 V nominal — https://global.toshiba/ww/products-solutions/battery/scib/product-next/product/cell/high-power
- Cell electrical detail (2.4 V nominal, 2.8 V/1.8 V limits, ~7 Wh) —
  https://lifepo4cells.eu/en/cell/toshiba-scib-2-9ah-lto-cell
- LTO versus LFP cycle-life distinction (20,000 to 70% for high-energy cells) —
  https://pacific-battery.com/blog/when-to-use-lithium-titanate
- Eaton XV3550-2R7307-R supercapacitor datasheet —
  https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-xv%20supercapacitor-cylindrical-snap-in-data-sheet.pdf
- Prior analysis: `docs/design/short-buffer-storage.md`,
  `docs/design/storage-review.md`
