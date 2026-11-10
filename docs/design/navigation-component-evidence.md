# Optional navigation: bounded component evidence

Retrieved 2026-11-10. Candidate research only: no board, firmware, procurement, or population decision. Main rail assumed 3.3 V. Prices are not a complete BOM quote. Blank CSV prices mean unverified, not free. Exactly one IMU is fitted; BMP390 is optional/DNP.

## Power numbers to use (and not misuse)

| Candidate / mode | Published current | Qualification | One-hour 3.3 V planning arithmetic |
|---|---:|---|---:|
| MAX-M10S default GPS+Galileo+BeiDou B1I, continuous tracking | 9.5 mA VCC + 2.3 mA V_IO = 11.8 mA | Typical, **measured at 3.0 V**, 25 °C, 1 Hz navigation; not a 3.3 V measurement or maximum | 11.8 mAh / 38.94 mWh, **proxy only** |
| Same GNSS, acquisition | 11.5 + 2.3 = 13.8 mA | Typical average startup-to-first-fix at 3.0 V; not startup peak | 13.8 mAh / 45.54 mWh if acquisition persisted for an hour; proxy only |
| Same GNSS, cyclic tracking power-save | 5 + 2 = 7 mA | Typical at 3.0 V; configuration dependent, not a blanket continuous-navigation assumption | 7 mAh / 23.1 mWh, proxy only |
| MAX-M10S startup | up to 100 mA inrush | Supply-delivery requirement, **not** continuous worst-case current | Do not multiply by one hour |
| LSM6DSO32 or LSM6DSOX, combo high performance | 0.55 mA | Manufacturer product-page claim; electrical-table conditions and maximum not retrieved | 0.55 mAh / 1.815 mWh, provisional typical-like planning value only |
| BMP390, 1 Hz forced, pressure ×1 / temperature ×1 | 3.2 µA typical; 7.4 µA max | Table 22; includes explicit separate 4.3 µA calculated-forced-mode column, not interchangeable with measured typical | 0.0032 mAh / 0.01056 mWh typical; 0.0074 mAh / 0.02442 mWh max |
| BMP390 pressure conversion peak | 660 µA typical / 730 µA max | Table 2, instantaneous conversion load | Not one-hour average |

The GNSS rail currents must be **added** when both VCC and V_IO use the same rail. The front-page 25 mW claim is not a universal 3.3 V/default-constellation budget. At the actual published 3.0 V condition default continuous tracking is 35.4 mW. A combined GNSS + IMU + optional low-rate barometer proxy is 12.3532 mA, or 40.76556 mWh for one hour at 3.3 V. This is **not a guaranteed maximum or battery-input estimate**: exclude antenna current only if passive, and add regulator loss, host processing, connectors/LEDs and any breakout regulators. Bench-measure the chosen 3.3 V configuration before using it as an endurance claim.

## Primary source register

### G — u-blox MAX-M10S-00B

[Manufacturer PDF](https://content.u-blox.com/sites/default/files/MAX-M10S_DataSheet_UBX-20035208.pdf), **UBX-20035208 R08, 30-Jan-2026**, downloaded and text-extracted in full. Table 25 (p21) identifies MAX-M10S-00B as the global ordering code; MAX-M10S-00B1 is regional, not an automatically accepted substitution. Applicable global type number MAX-M10S-00B-01, ROM SPG 5.10.

- Table 13 (pp11–12): VCC operating 1.76–3.6 V; V_IO with VIO_SEL open 2.7 V to VCC (maximum 3.6 V), suitable for tied 3.3 V supplies. VIO_SEL grounded selects 1.8 V IO, **not** the requested rail. V_BCKP 1.65–3.6 V.
- Table 10 (p9): TXD pin 2, RXD pin 3, TIMEPULSE pin 4, V_BCKP pin 6, V_IO pin 7, VCC pin 8, RF_IN pin 11, LNA_EN pin 13, VCC_RF pin 14, VIO_SEL pin 15. TIMEPULSE is linked to SAFEBOOT_N through 1 kΩ; do not hold it low during startup.
- Table 1 (p4): default 1PPS; configurable 0.25 Hz–10 MHz. Table 18 (p14): UART 9600–921600 bit/s, no hardware flow control. Table 20 (p16): default 9600 8N1, NMEA output / UBX and NMEA input. PPS timestamps are not a position solution; associate them with receiver message time.
- Table 15 (p13) gives the currents above; section 4.3 explicitly calls them indicative sample measurements. Footnotes: 1 Hz navigation, internal LNA low gain, simulated −130 dBm signals, 25 °C. Table 17: hardware backup 28 µA typical at V_BCKP=3.3 V with VCC/V_IO off; software standby 46 µA on V_IO plus 120 nA on VCC at 3.3 V. No guaranteed continuous maximum was found.
- Section 1.1 (p4): integrated LNA followed by SAW filter supports passive-antenna designs; **no antenna is integrated**. Table 13: RF_IN 50 Ω, built-in DC block; external gain maximum 30 dB in default low-gain mode. VCC_RF output typically VCC−0.1 V, operating output limit 50 mA (not the 250 mA absolute-maximum rating). A passive L1 antenna with suitable ground plane and 50 Ω routing is the cost/power-first candidate. An active antenna requires its own verified current and bias/feed/protection design; VCC_RF is not proof that arbitrary antennas can be connected directly to RF_IN. Antenna MPN, connector and enclosure RF performance remain unselected.

### I32 — ST LSM6DSO32TR (preferred if 32 g headroom is required)

[Manufacturer product page](https://www.st.com/en/mems-and-sensors/lsm6dso32.html) fetched successfully. [Primary datasheet URL](https://www.st.com/resource/en/datasheet/lsm6dso32.pdf) **not retrieved**: extraction rejected its resolved address; direct requests timed out. Product-page resource list identifies **DS12941, version 1.0, 16-Mar-2020** (another displayed metadata field says 1.1; PDF revision unresolved).

Confirmed from manufacturer's page: 0.55 mA combo high-performance claim; analog supply 1.71–3.6 V; independent IO supply advertised as 1.62 V (full IO limits **not verified**); SPI/I²C/I3C; ±4/8/16/32 g; ±125/250/500/1000/2000 dps; 9 KB FIFO. Product is marked active. Page lists LSM6DSO32TR tape/reel ordering candidate. Do not infer live stock from its September inventory snapshot.

SPI plus a data-ready interrupt is the intended integration, but exact DRDY pin/register mapping, IO upper limit, SPI timing, decoupling and electrical-table current conditions must be checked in DS12941 before schematic release. No guaranteed maximum current is established here. Do not treat generic interrupt advertising as verification of the proposed DRDY wiring.

### IX — ST LSM6DSOXTR (baseline candidate, not a qualified selection)

[Manufacturer product page](https://www.st.com/en/mems-and-sensors/lsm6dsox.html) fetched successfully; [primary PDF](https://www.st.com/resource/en/datasheet/lsm6dsox.pdf) unavailable despite extraction, IPv4 curl and HTTP/1.1 attempts. Resource list identifies **DS12814 version 4.0, 04-Jun-2024**, not a verified PDF read.

Manufacturer-page facts: 0.55 mA combo high-performance claim; analog supply 1.71–3.6 V; independent IO advertised at 1.62 V, full range unverified; SPI/I²C/I3C; ±2/4/8/16 g; same listed gyro scales as I32; FIFO 9 KB, machine-learning core and auxiliary OIS SPI. Do not assume drop-in firmware equivalence or identical register scaling. DRDY pin routing and detailed current conditions remain the same release gate as I32.

[ST direct store](https://estore.st.com/en/lsm6dsoxtr-cpn.html) fetched: quantity **1–4 table says $6.11/unit**, 5–9 $5.15, 10–49 $4.78, 50–99 $4.18, 100–250 $4.03. Page says “In stock” but also displays standalone $5.99 alongside $6.11; therefore the CSV records the explicit quantity-table figure, **not a settled checkout quote**. Currency is presented with `$`; USD interpretation should be confirmed at checkout. Taxes, delivery to Germany, freight and actual order allocation were not verified. The page lists LGA 14L 2.5×3×0.86 mm; overview copy says 0.83 mm, so package drawing must settle height.

### B — Bosch BMP390 (optional, DNP by default)

[Manufacturer PDF](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp390-ds002.pdf), **BST-BMP390-DS002-07 revision 1.7, March 2021**, downloaded and text-extracted in full.

- Table 2 (p7): VDD 1.65–3.6 V, VDDIO 1.2–3.6 V; both may use 3.3 V. VDD ripple maximum 50 mVpp. Current typical values at 25 °C; min/max currents at −40/+85 °C. Sleep 1.4 µA typical at 1.8 V, 1.5 µA at 3.6 V; **no exact 3.3 V sleep figure** supplied.
- Table 1 (p3): I²C up to 3.4 MHz or 3-/4-wire SPI up to 10 MHz; 2×2 mm LGA, pressure range 300–1250 hPa. Use an independent CS if sharing SPI; pressure port must communicate with ambient air while managing water, dirt and dynamic-pressure error.
- Table 22 (p26): 1 Hz forced-mode ×1/×1 = 3.2 µA typical / 7.4 µA max; standard ×4/×1 = 7.8 / 12.8 µA; highest ×32/×2 = 46.4 / 59.2 µA. Current depends on ODR/oversampling: do not quote the minimum-current mode for an arbitrary high-resolution configuration. Table 2 peak pressure current 660/730 µA typical/max; temperature conversion 240/320 µA.
- Table 1's typical relative ±3 Pa (approximately ±0.25 m under stated conditions) is **not absolute elevation accuracy**. Atmospheric weather drift needs referencing; no claim of solving GNSS-denied horizontal navigation.

## Small upgrade/trade ledger

| Choice | Gain | Cost or limitation | Default disposition |
|---|---|---|---|
| MAX-M10S + passive antenna | Absolute outdoor position/time without active antenna draw | RF layout/enclosure/ground-plane validation; GNSS blocked indoors | Candidate baseline; antenna still open |
| Active antenna instead | Potential placement/sensitivity improvement | Extra current, bias/protection parts, cable/connector and cost | Only after passive antenna tests fail |
| DSO32 over DSOX | ±32 g range for shocks | No ±2 g range; scaling must be explicit | Prefer only when shock requirement justifies it |
| DSOX over DSO32 | ±2 g option, MLC/OIS features | Only ±16 g; unused features do not justify premium | Baseline after interface audit; compare actual quotes |
| Add BMP390 | Relative climb/descent aid at low current | Weather drift, venting, extra assembly/driver burden | DNP until a vertical-navigation need exists |
| Add magnetometer / RTK / dual-band GNSS | Potential heading/position improvement | More calibration, RF/power/cost and scope | Out of this bounded shortlist |

## Retrieval and procurement caveats / release gates

1. ST PDFs remain inaccessible; manufacturer HTML is primary evidence but **not a substitute for electrical tables**. Retrieve DS12941 or DS12814 and verify VDDIO, DRDY, SPI, current conditions and application circuit before release.
2. MAX and BMP full PDFs were read via direct HTTP and `pdftotext`; initial web extraction returned only opening sections, so it was insufficient alone. PDF copies are transient research cache, not vendored into the repo.
3. A guessed DigiKey numeric product URL resolved to a different LEMO part and was rejected; it is not a sourcing reference. No verified price for MAX-M10S, DSO32 or BMP390 was obtained. ST direct-store price is the only captured candidate figure and is caveated above. No BOM total is defensible yet.
4. Complete antenna, decoupling, optional power switch/backup, RF/ESD and connector selection only against the actual add-on schematic. CSV support rows are explicit unresolved requirements, not orderable invented MPNs.
5. No hardware tests, 3.3 V current measurements, availability reservations or supplier qualification were performed. This document cannot establish a working navigation subsystem or guaranteed one-hour runtime.
