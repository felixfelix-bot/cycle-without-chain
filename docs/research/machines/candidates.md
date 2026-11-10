# Commercial machine candidates — reversible Villiger series-electric conversion

Research date: 2026-11-10. **Candidate shortlist, not a fit approval or an efficiency demonstration.** No photographs, frame/fork material, dropout dimensions, wheel diameter, brake geometry, or crank attachment measurements were supplied. The provisional rider envelope is **75–250 W at 50–100 rpm**; 500 W transients are **not approved** and are not a sizing requirement here. “Reversible” means removable conversion, not permission to modify the original bicycle permanently.

## Outcome

- **Best documented compact generator to investigate:** maxon **EC 90 flat, 500267**, with a separately supported speed-increasing gear drive. It is a purchasable motor identity, not a validated 250 W generator solution. Its published 87% maximum motoring efficiency makes it a challenging starting point for an 80% whole-path goal.
- **Best documented hub-generator benchmark:** Grin **front All-Axle, standard 6T**, driven through its shell. Accessible constants and low-speed construction make modelling easier, but approximately 4 kg and fixed losses are serious disadvantages at human power.
- **Light wheel-drive shortlist:** Bafang **G311 front / G310 rear** sold by Grin; next compare Shengyi **SX1 front / SX2 rear**. These geared, freewheeling motors are wheel-drive candidates, not straightforward forward-driven shell generators.
- **Direct-drive wheel alternative:** Grin **All-Axle front** if mounting and low-power operating-point losses are acceptable. Rear versions are not presumed to fit an old road frame.
- **CIXI PERS:** real commercial integrated benchmark, with a Standalone OEM offering as well as kits. It is not simply an exposed PM machine for a custom generator bridge. Manufacturer calls the system open/versatile at powertrain/CAN level; this does **not** establish open internal controls or raw winding access.
- **No candidate combination is demonstrated to achieve 80% crank-to-wheel cruise efficiency.** Wheel size, cruise speed/load, bus voltage, winding, gear ratio and measured generator maps remain missing.

## 1. What the pedal envelope actually requires

Calculated using `T = 60 P / (2π n)`:

| Pedal input | 50 rpm crank torque | 100 rpm crank torque |
|---|---:|---:|
| 75 W | 14.32 N·m | 7.16 N·m |
| 250 W | 47.75 N·m | 23.87 N·m |

These are average torques, not peak torque within a pedal stroke. A clamp/bracket must handle reaction torque and cyclic loads without crushing tubing or slipping. A rider standing on a stopped pedal is a separate structural load case, not an approved 500 W electrical operating point.

For speed increase `r = generator rpm / crank rpm`, generator speed is `r n`, and approximate generator shaft torque is `ηgear Tcrank/r`. A ratio is **not selected here**: allowable current, back-EMF, losses at both cadence endpoints, gear geometry, guarding, shaft loads and bus topology must be solved together. Electronic loading can decouple cadence from wheel speed, but does not remove generator torque/speed limits.

## 2. Generator candidates

### A. CIXI PERS Standalone — integrated OEM alternative, not the custom-machine route

**Manufacturer catalogue values:** 2026 catalogue lists PERS Standalone at **3.7 kg**, **96.20 × 208.80 × 162.96 mm**, maximum **100 rpm**, maximum torque **185 N·m**, **360 W maximum continuous**, **2000 W peak**, and efficiency **“higher than 80%”**; CAN, Bluetooth/4G and embedded IoT are listed. These maximum ratings are not permission to use those powers and are not necessarily simultaneous operating points. [S1]

**Important source discrepancy:** CIXI's professional web page reports **3.4 kg**, **613 W maximum producible power**, and **80% efficiency**, versus the catalogue above. Treat these as unresolved version/specification differences and obtain a dated quotation/datasheet for the exact unit. [S2]

**Commercial evidence:** CIXI invites professional enquiries/quotes and lists Standalone. Steintrikes lists a **€3,850 PERS chainless system set**, including PERS, mounting, motor wheel, battery, controller and accessories, explicitly for **Rebel models**. This establishes a commercial product, not a Villiger retrofit kit or a quoted standalone retail price. [S2–S3]

**Integration judgement:** useful if abandoning most custom generator electronics in favour of supplier controls. CAN compatibility is not proof that a custom dual power board may directly drive its machine. Ask about minimum quantity, supply voltage, startup without battery, pedal resistance commands, generator DC output interface, faults, firmware dependencies and licensing. Its crank housing/mount needs a bespoke reversible support; it is not established to screw into the Villiger bottom bracket.

**Efficiency limitation:** no cadence × torque × temperature map or defined crank-to-wheel measurement boundary was found in these public sources. An “80%” PERS figure must not be relabelled 80% for generator + controller + wheel motor. If it describes generator-unit conversion at a point, any downstream losses lower whole-path efficiency.

### B. maxon EC 90 flat Ø90 mm, 260 W, Hall sensors — part **500267**

**Manufacturer data / shop identity:** 48 V winding; **41.3 rpm/V**; **231 mN·m/A** torque constant; **0.844 Ω** terminal resistance; **1.07 mH** inductance; **1960 rpm / 278 mA no-load**; **1670 rpm**, **0.964 N·m**, **4.06 A** nominal continuous values; **5000 rpm mechanical maximum**; **985 g**; published **maximum efficiency 87%**. Shop listing exposes quantity pricing (observed €276.73 for 1–4, excluding tax/shipping; quote/live availability must be checked). [S4]

This is a complete bearing-supported brushless machine, unlike maxon's frameless kits. It offers a credible starting point for a compact, gear-driven PM generator with a custom active rectifier. The **260 W family label does not mean 260 W continuously at every speed**: the listed nominal torque and speed multiply to approximately **169 W mechanical output**. Generator thermal limits must be evaluated separately.

**Sizing implication, not a ratio prescription:** before allowance for gear loss, 250 W at 0.964 N·m requires approximately **2477 rpm**. Combining this speed with 50 rpm cadence would imply approximately **49.5:1**; at 100 rpm it would approach **4950 rpm**, very close to the listed 5000 rpm limit. This illustrates why an arbitrary 10:1/20:1 ratio or an unexamined “260 W” rating is insufficient. This simple constant-torque screen is not a generator efficiency/thermal map; real losses and operating constraints change the admissible region.

**Mechanical caution:** manufacturer lists maximum radial load **130 N at 10 mm from flange**, dynamic axial load **34 N**. An overhung pinion cannot be assumed safe; use an externally supported gear shaft/coupling if necessary. Need sealed housing, thermal path, guards and a positive reaction structure without damaging bicycle tubing.

**Data gap:** scalar maximum motoring efficiency and motor constants are available, but no validated generator map over this pedal envelope was found. The 87% figure is neither guaranteed generating efficiency nor a whole-system figure. Ask maxon for regeneration modelling/thermal conditions before buying.

### C. Grin front All-Axle standard 6T as generator

**Manufacturer values:** direct-drive PM hub, **10 rpm/V**, phase-to-phase **145 mΩ**, **380 µH**, **23 pole pairs**, approximately **4.05 kg front**. Other listed winds: **7.5 rpm/V (8T)** and **12 rpm/V (5T)**. Published common drag model: **0.45 N·m hysteresis + 0.0005 N·m per rpm**. Product family explicitly offered through Grin/dealers, including a named Swiss dealer. [S5]

With axle restrained and shell gear-driven, a direct-drive hub can act as generator without defeating a freewheel. Shell/pinion attachment, bearing loads and torque restraint need actual engineering; do not assume a disc mount/spoke flange is automatically suitable for an external gear. Its lower speed constant allows a lower shaft speed for a given back-EMF than the maxon winding, but **rpm/V is not a guaranteed loaded rectified bus voltage**.

**Calculated illustration only:** at 300 rpm the published drag model gives 0.60 N·m, or **18.85 W rotational loss**, before copper/converter losses. That equals 25% of a 75 W input. This is not the selected speed or a measured generator result; it illustrates why a traction-sized DD hub may be poor at low human power despite attractive copper resistance. Grin pages/product versions can have different fitted drag constants: use the exact motor revision, not mixed values.

**Judgement:** excellent accessible bench reference; unattractive clamped-bike generator mass/diameter unless packaging deliberately accepts it. A small geared hub is not an automatic remedy: normal forward shell motion on a freewheeling geared hub does not back-drive its rotor. Locking its clutch is a modification, adds gear losses and requires durability validation; it is not recommended as the initial reversible machine choice.

## 3. Wheel-motor candidates — every fit remains conditional

| Specific purchasable family | Published evidence | Why investigate | Blocking fit/performance questions |
|---|---|---|---|
| **Bafang G311 front / G310 rear, via Grin** | About **2.3 kg**; G310 large **11:1** internal gearing. Grin G311 and G310 kit shop listings expose winding choices and in-stock kit status at retrieval. [S6–S8] | Best first lightweight traction candidates for low rider-derived power. Freewheel avoids direct-drive drag while coasting. | Obtain exact dimensional drawing for chosen SKU; front/rear axle flats, spacing, cable exit, fork clearance, torque arm, rim brake surface and spoke pattern. Rear road-frame width is not assumed compatible. No normal regen through a freewheel. |
| **Shengyi SX1 front / SX2 rear, via Grin** | Grin describes **100 mm front / 135 mm rear** standard slotted-dropout application. SX2 standard-wind shop data: **3.2 kg**, **7.4 rpm/V**, **135 mm OLD**, **36 holes**, **0.119 Ω** phase resistance, power range labelled **350–700 W**. [S9–S10] | More robust alternative if duty/thermal needs justify added mass. | Bigger than necessary on label alone; assess actual 60–200 W wheel-output operating points. Same dropout, torque restraint and rim compatibility gates. Do not adopt higher electrical power just because motor supports it. |
| **Grin front All-Axle, 6T/8T/5T** | **4.05 kg**, **32 holes**, integrated torque arm and fork clamp; adapters for multiple front QR/thru-axle standards. Rear approximately **4.30 kg** with 135 mm QR / 142 / 148 mm families (revision dependent). [S5] | Direct drive, regen capability, public constants and simulator support; no internal reduction clutch. | Adaptable is not universal clearance or fork-strength approval. Added mass and fixed drag may undermine human-power efficiency. Exact winding requires wheel circumference and cruise speed/bus data. Rear road spacing may not match. |

**Reversibility gate:** no cold-setting/spreading, filing dropouts, drilling or welding is authorized. Do not infer steel from the brand/age; do not clamp thin or unknown tubing casually. Front mounting avoids rear-spacing issues only if the fork and torque-arm installation are safe. Replace/lace a separate wheel with the correct actual bead-seat diameter and rim brake track, retaining original parts. A nominal “road wheel” label is insufficient: 622 and 630 mm rims, for example, are not interchangeable for brake reach/tyres. Keep effective mechanical brakes independently of electrical braking.

## 4. What 80% would require

For direct bus transfer, define:

`ηcrank→wheel = ηgear × ηgenerator × ηgenerator bridge/DC conversion × ηmotor inverter × ηwheel motor`

Do not multiply an inverter factor again if using Grin's simulator green efficiency curve: it already includes **controller + motor** losses, and excludes battery internal loss. Grin says model parameters come from dynamometer measurements; this is substantially better evidence than a generic motor headline, but is not a measurement of this custom dual board or its generator. [S11]

**Calculated target checks, not predictions:**

- 80% of 75–250 W means **60–200 W wheel output**, total permitted loss **15–50 W**.
- If gear efficiency were 98%, generator bridge 98%, and motor inverter 98% (all **illustrative assumptions**, not measured), generator × wheel-motor efficiency must be **0.80 / 0.98³ = 84.9986%**. If equal, each machine must be about **92.20%** at the actual operating point.
- If generator efficiency were only 87% at the selected point, those same illustrative three factors would require wheel-motor efficiency **97.70%**. This is a warning, not proof from a motor-mode maximum that a generator cannot ever differ.
- An optimistic illustrative pair of 95% machines and the same three 98% stages gives **84.94%**. Thus 80% is not algebraically impossible, but the shortlisted public data does not establish those operating efficiencies. Fixed losses at 75 W are particularly restrictive.

A battery buffer makes low-speed/acceleration operation possible without matching instantaneous pedal and wheel power. To substantiate crank-to-wheel efficiency, measure simultaneous crank and wheel mechanical energy and account for battery energy change; a draining battery can make a misleading ratio exceed 100%. If all generated energy is stored and later discharged, include storage round-trip losses rather than silently assuming direct-bus operation.

## 5. Data to request / cheapest decisive work before bike hardware

1. Obtain bike photographs and measurements: frame/fork material/condition, front/rear inside-dropout spacing and slot size, brake type/reach, tyre ISO size, crank/BB and chainring bolt geometry, safe mounting regions and full steering/pedal clearances. No candidate presently has confirmed fit.
2. Request vendor **generator-mode torque–speed–efficiency data at 75/150/250 W crank-equivalent input**, winding/temperature conditions and allowable radial loads; for CIXI additionally obtain interface documentation and exact procurement terms. Ask Grin for the exact motor revision/constants and matching simulator model.
3. Bench a supported motor and gear mechanism, initially with an appropriate commercial regenerative controller/load rather than making a custom board the first unknown. Measure input shaft torque/speed, DC power and temperature at 50/75/100 rpm crank-equivalent. No 500 W test is in scope.
4. Characterize selected wheel motor at actual cruise rpm and 60–200 W mechanical load, then test the custom dual power board with current, thermal, bus-overvoltage and loss-of-load protection. Battery-full/unplugged states need a controlled energy sink or torque shutdown; generator PM voltage remains present when rotating.
5. **Falsifiable acceptance:** accept 80% only for a declared cruise point/range with matched battery state/energy accounting and measurement uncertainty. Reject a candidate if its measured losses consume the budget before the remaining stages are added. The initial research supports testing, not purchase of a complete drivetrain.

## Sources and evidence limits

Primary manufacturer/designer sources unless explicitly identified otherwise. Product identities, values and commercial pages were retrieved via web-search backend excerpts, some extensive; direct `web_extract` was unavailable because the configured backend is search-only. Accordingly, shop prices/status are discovery evidence, not a completed stock/checkout verification. No supplier was contacted and no physical tests or simulator sweeps were performed.

- **[S1] CIXI, PERS KIT Catalog 2026 (English):** https://static.cixi.life/9349ba9b-0ebb-4713-897f-c2338b6e0385-PERS-Catalog-2026-EN-Rehacare.pdf
- **[S2] CIXI professional PERS page:** http://www.cixi.life/pers-technology-pro
- **[S3] Steintrikes retailer, CIXI PERS chainless system set:** https://steintrikes.com/product/47-cixi-pers-chainless-system-set
- **[S4] maxon shop/datasheet, part 500267:** https://maxongroup.com/maxon/view/product/motor/ecmotor/ecflat/ecflat90/500267
- **[S5] Grin All-Axle technical overview and ordering links:** https://ebikes.ca/product-info/grin-products/all-axle-hub-motor.html
- **[S6] Grin Bafang G310/G311 technical overview:** https://ebikes.ca/product-info/grin-kits/bafang-g310-g311.html
- **[S7] Grin G311 Front Minimal Kit shop:** https://ebikes.ca/shop/kits-by-type/minimal-kits/g311-front-minimal-kit.html
- **[S8] Grin G310 Rear Minimal Kit shop:** https://ebikes.ca/shop/electric-bicycle-kits/g310-rear-minimal-kit.html
- **[S9] Grin Shengyi SX1/SX2 technical overview:** https://ebikes.ca/product-info/grin-kits/shengyi-sx-geared-hubs.html
- **[S10] Grin SX2 Rear Barebones Kit specifications:** https://ebikes.ca/other-kits/shengyi-sx-kits/sx2-rear-barebones-kit.html
- **[S11] Grin motor simulator, definitions and accuracy/limitations:** https://ebikes.ca/resources/web-tools/simulator.html

Not promoted to shortlist: maxon EC60 **167132** is marked **NRND** and still has a published 87% motoring maximum; EC60 **408057** explicitly says it can no longer be ordered. These are not stronger current-sourcing answers than 500267. Generic RC outrunners and untraceable “low-rpm PM generators” are intentionally omitted rather than pretending their efficiency, winding or continuous thermal data is known.
