# Entry publication review — UNSAFE partial design

Reviewed 2026-11-10 from feature `64b271755a78c5b93165ca21719c60beb142fdbe` in an isolated worktree. Fetched `github/master` at `77f3761`; it is already an ancestor, so the merge reported already up to date. Storage/braking updates are preserved. This is a bounded entry review, not electrical approval, a cross-family review, or permission to fabricate, energize or ride. The assembled system remains **NOT SAFE TO ENERGIZE**.

## Measured topology and limits

Read the entry change and `fast-oc-integration-review.md`, generator, native sheet and exported connectivity. F1 KLKD020CN connects SOURCE_POS to ENTRY_FUSED; J41 bypasses the J42/R116 100Ω branch to BUS_SHUNT_HI. R117 2mΩ joins DC_LINK. C73/C74 are each 470µF/100V (940µF nominal total); R118 is the always-connected 10kΩ bleeder. J43 pins 1/2 are the shunt-side sense nets, pin 3 DC_LINK, pin 4 PGND. These are high-common-mode instrument connections, not protected MCU inputs or proof of physical Kelvin routing. F1, connectors, resistor mounting and shunt remain candidates, not installed ratings.

D20 cathode is DC_LINK and anode PGND. It is a shunt reverse clamp, **not reverse isolation**. Fuse presence does not establish safe reverse-polarity operation: prospective source fault current, clearing time, diode surge survival, wiring and holder coordination remain unproved. No guaranteed battery protection is published.

## Independent arithmetic (nominal ideal model)

Using 58.4V, 100Ω and the explicit 1.5mF assembled capacitance ceiling:

- Stored energy 2.55792J; initial current 0.584A; resistor peak 34.1056W. These are requirements, not pulse/thermal acceptance.
- With no bleed/load, tau=0.150s and time to 1V mismatch=0.610097s.
- Including 10kΩ bleed, V∞=58.4×10000/10100=57.821782V, tau=(100Ω||10kΩ)×1.5mF=0.148515s; reaching 57.4V takes 0.730787s, not 0.610s.
- At the 57.4V threshold, available auxiliary current is (58.4−57.4)/100−57.4/10000=4.26mA. This corresponds to only 0.244524W of bus-input auxiliary power. A hypothetical constant 10mA auxiliary load gives V∞=(58.4−100×0.010)/1.01=56.831683V and can never reach the threshold. These examples are not a measured auxiliary load specification. Real converter startup, UVLO cycling, downstream capacitance and constant-power behavior remain unmodeled; no assembled-drive precharge claim follows.
- Isolated 10kΩ discharge from 58.4V to 5V takes 36.86817s nominal, 37.23685s at +1% resistance with the same capacitance ceiling. PM generation, another source or an open bleeder invalidates it; elapsed time does not prove safe terminals.
- At 15A the 2mΩ shunt gives 30mV and 0.45W, not proof of installed current capability.

Fresh `ngspice -b entry_transient.cir` returned bus at 0.99s=57.74804V, bus at 39s=4.585225V, peak source current magnitude=0.5839397A. This is a passive behavioral model, not vendor/fuse/contact/reverse-fault qualification.

## Safety-language finding corrected

The earlier manual instruction to close J41 at <1V difference and then remove J42 conflicted with DEAD ONLY and could imply energized connector manipulation. Withdrawn in the milestone and replaced in the generator/native schematic annotation with an explicit prohibition. PDF and entry SVG were re-exported using KiCad; no connectivity, values, flags or protection circuitry changed. There is **no approved manual operating sequence**. Voltage matching is not proof of dead terminals. Interlocked, appropriately rated switching and load inhibition are still missing; this review does not invent an operational workaround.

## Executed checks

Tests ran on a scratch copy of the reviewed board to prevent test-written SPICE logs from modifying historical evidence or another worker's checkout. Final commands, from that copy:

- `python3 -m unittest discover -s tests`: 27 tests, OK (89.077s).
- `python3 -O -m unittest discover -s tests`: 27 tests, OK (81.579s).
- KiCad 9.0.9 `kicad-cli sch erc --exit-code-violations --format json -o <scratch>/erc-final.json powerboard-reva.kicad_sch`: exit **5**, four errors, zero warnings. Exact unresolved power_pin_not_driven endpoints: U1.24 VREF, U1.25 AGND, U3.1 IN, U17.37 VDDA. No PWR_FLAG additions, waivers or fabricated clean ERC.

Local scratch evidence: `/home/c08r4d0r/.tmp/cycle-entry-review/{tests-final.log,tests-O-final.log,erc-final.json,entry-spice.log}`. Historical tracked logs are unchanged; this document records fresh results rather than silently replacing them. The fast-OC review's 25-test count describes its earlier snapshot, not this 27-test run. Its sink-drive/latency and supply-loss qualification blockers remain open.

## Publication disposition

Suitable only for publication as an explicitly **UNSAFE partial design**. Protected entry, reverse isolation, switching/interlocks, BMS charge/discharge permission, sink availability, fault/thermal qualification and physical assembly remain blocked. Braking-input topology is the next design owner's separate decision; this review neither resolves it nor expands implementation scope.
