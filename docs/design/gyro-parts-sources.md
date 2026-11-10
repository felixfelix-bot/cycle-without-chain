# Gyroscopic balance: bounded primary-vendor candidate search

Checked 2026-11-10. Research only: no purchase, hardware integration, modification, construction instructions, rider testing, or safety/medical guarantees. Companion machine-readable shortlist: [gyro-candidate-bom.csv](gyro-candidate-bom.csv).

## Outcome

**No qualified, purchasable bicycle-scale contained CMG module was established in this bounded search. This is not proof that none exists on the market.** Six candidates/leads are recorded, not a procurement-ready system BOM. A qualified module would need vendor momentum, rated rotor speed, complete mass, gimbal torque/rate/travel, power/cooling, documented failure containment, control/fault interface and an actual supply channel. An enclosure alone does not establish rotor-burst containment.

The study basis is 120 kg rider plus luggage, with 140/150 kg total bicycle-system cases before any newly added module unless the parent model explicitly includes it. The unknown bicycle is not certified by this research. Sensors and servos do not substitute for a qualified momentum-producing module.

## Primary sources and verified claims

### G1 — Seakeeper 1: engineered marine comparator, reject for bicycle scale

- [Manufacturer product and specifications](https://www.seakeeper.com/seakeeper-products/seakeeper-1/): **166 kg**, 0.582 × 0.598 × 0.403 m; maximum rated speed **9,750 rpm**; angular momentum **1,000 N m s** at that speed; **12 VDC**; spool-up maximum **600 W / 50 A**; operating power **225–600 W**, sea-state dependent; 35 minutes to maximum speed and 18 minutes to stabilization at 7,310 rpm. The page targets approximately 23–30 ft boats up to approximately 5.5 tons.
- [Manufacturer technology description](https://www.seakeeper.com/technology/): vacuum-encapsulated flywheel, bearings and motor; glycol/seawater cooling; active control; fore/aft precession generates port/starboard torque. These are vendor claims, not measurements here. Vacuum isolation is **not** a verified burst-containment rating. Do not transfer generic family maximum claims to a different SKU.
- This is a real commercial marine product with a dealer channel, not a bicycle module. Stock, delivery and suitability were not verified. No price is used in the study.
- Its **166 kg bare product mass exceeds either 140 or 150 kg baseline system mass**. Adding it would make the nominal cases at least 306/316 kg before ancillary hardware, power or cooling. It is therefore a scale comparator, not a candidate installation. Marine roll suppression does not demonstrate standstill balance of an inverted-pendulum bicycle.

### G2 — Lit Motors AEV: unqualified technology/preorder lead

[Manufacturer homepage](https://www.litmotors.com/) explicitly describes a self-balancing vehicle, a **CMG system**, and a **Pre-Order** channel. It does not establish standalone CMG sales or provide the module's voltage, speed, torque, momentum, mass or containment specification in the fetched page. Treat this as a vehicle-development/marketing lead, not a purchasable bicycle component or proof of production deliveries. The site's safety and performance claims are not adopted by this study.

The requested **“Veelo”** name could not be resolved to a primary-vendor gyro-module specification in the bounded name search. Do not silently substitute similarly named companies. [Veleon](https://veleon.de/) was actually extracted and describes a leaning cargo/family cycle with a lever-operated standing lock, not a CMG module. A guessed `https://www.gyro.bike/` lead failed DNS resolution; that is an inaccessible lead, not evidence about its past or present products. Historical Jyrobike coverage surfaced during discovery, but no current primary-vendor orderable module specification was established, so it is not counted as a sourced part.

### S1 — Adafruit BNO085 breakout, product 4754

- [Product page](https://www.adafruit.com/product/4754): accelerometer, angular-rate sensor, magnetometer and onboard SH-2 fusion processor; **2.5 g**, 25.6 × 22.7 × 4.6 mm. The fetched retail page says **In stock / Add to Cart**; this is only a dated page observation, not a delivery commitment.
- [Manufacturer pinout documentation](https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/pinouts): **3–5 VDC VIN**, with UART, SPI and I2C pin functions documented.
- This measures orientation/motion; it produces no stabilizing mechanical torque. Report rate, end-to-end latency, vibration response, magnetic interference, dynamic tilt estimation and host compatibility remain unqualified. No claimed closed-loop bandwidth is inferred from the product name.

### C1 — PJRC Teensy 4.1 controller

[Manufacturer page](https://www.pjrc.com/store/teensy41.html) specifies an ARM Cortex-M7 at **600 MHz**, **5 V VIN** when not USB-powered, and **3.3 V GPIO that is not 5 V tolerant**. CPU clock is not a mechanical speed or a proven control-loop update rate. The page documents serial/SPI/I2C interfaces; no direct electrical compatibility with the actuator is assumed. Board mass, current stock, delivery, real-time deadline behavior, watchdog design and fault response were not verified. This is a general controller candidate, not a safety controller.

### A1 — ROBOTIS DYNAMIXEL XM430-W350-T/R

[Manufacturer eManual](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/) specifies **82 g**, **10.0–14.8 V input**, recommended **12 V**, **4.1 N m stall torque at 12 V / 2.3 A**, and **46 rpm no-load speed at 12 V**. These are different operating points: **stall torque is not a continuous rating, and no-load speed is not the speed available at stall torque**. The same page gives 40 N radial load at 10 mm from the horn and 20 N axial load, reinforcing that structural loads cannot be ignored.

T and R are interface variants (TTL versus RS-485), not interchangeable wiring assumptions. No final variant is selected. This is only a low-speed laboratory actuator lead; continuous torque, loaded speed, thermal duty, backlash, loss-of-power behavior and gimbal reaction-load compatibility remain open. An actuator casing provides no containment for a separate flywheel. Documentation availability is not stock verification.

### E1 — TEDCO Gravitron Space Gyro, SKU 00020: educational HOLD

[Manufacturer retail listing](https://tedcotoys.com/products/gravitron-space-gyro-pvc-box.html) describes an **internal gyroscope**, a manual **zip strip**, included pedestal and educational use (vendor age recommendation 5+). A retail listing and quantity selector were accessible; stock count and delivery were not established. “PVC Box” describes packaging, not an engineering containment specification.

**Only a guarded, demonstrably LOW ENERGY, unmodified educational demonstration is in scope. This candidate does not yet meet that evidence gate.** Manual toy-scale operation suggests a lower-energy class than marine equipment, but the vendor page does not publish rotor inertia, maximum rated speed, mass, stored energy, guard coverage or containment testing. Consequently there is no quantified low-energy claim and no approved demonstration procedure here. Keep it HOLD until manufacturer documentation establishes the energy/guard constraints and appropriate supervision. Do not add motors, accelerate beyond manufacturer use, remove guards, mount it to a bicycle, or extrapolate its demonstration to a rider-load system. An open-frame gyro or exposed bicycle wheel is not substituted for the guarded requirement.

## Open qualification gates

1. Obtain a bicycle-scale commercial module specification and evidence of supply; distinguish an OEM enquiry/preorder/demo from an orderable delivered part.
2. Require documented momentum, speed, complete installed mass, gimbal travel/rate/torque and power/cooling. Missing values remain unknown, not zero.
3. Require containment/failure evidence, overspeed and power-loss behavior, and limits on loads and interfaces; neither a vacuum sphere nor a toy shell alone closes this gate.
4. For any future controller/sensor/actuator study, qualify latency, saturation, thermal duty, communication and fault behavior separately from nominal catalogue values.
5. For education, verify a guarded low-energy product before approving even a tabletop demonstration. No educational candidate in this search is a bicycle actuator.
6. No prices, stock quantities, EU shipping, delivery dates or purchases were inferred. Only the Adafruit page's explicit dated stock wording is reported.

## Retrieval method and limitations

Primary pages were fetched and read on the date above. `web_extract` returned Adafruit, ROBOTIS, Veleon and Adafruit pinout content, but its ROBOTIS excerpt omitted some specification rows. Direct HTTPS HTTP-200 retrieval plus HTML-to-text extraction recovered those rows and the Seakeeper, PJRC, Lit Motors and TEDCO pages. The latter sites had been rejected by the extraction service as private/internal-address targets; direct requests to their public vendor URLs succeeded. No reseller reviews or search snippets were used as quantitative specifications. A guessed old TEDCO singular `/product/` URL returned not found; the verified source is the plural `/products/` URL above.

Search was intentionally limited to the named marine/vehicle leads, one IMU, one controller, one actuator and an enclosed educational-toy lead. Claims are vendor-stated and were not experimentally validated. Unknown fields are explicit in the CSV; torque/speed fields distinguish N/A electronics from genuinely missing mechanical specifications. This is a feasibility evidence inventory, not a recommendation to buy or build.
