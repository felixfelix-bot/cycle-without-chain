# Pin provenance

- DRV8353S: TI SLVSDY6A (June 2019), pp6–7, 40-pin RTA SPI pin table; https://www.ti.com/lit/gpn/DRV8353 . Exposed pad represented as pad41 to PGND; footprint/package thermal-pad verification remains a release gate.
- CSD19532Q5B: installed KiCad 9 stock Transistor_FET symbol inherits Q_NMOS_SSSGD_AvalancheRated. Source1/2/3, gate4, drain5 (PowerPAD footprint convention). https://www.ti.com/lit/gpn/CSD19532Q5B . Stock footprint is candidate, not manufacturing qualification.
- DRV recommended capacitors follow pin table: CPL–CPH 47nF VDRAIN-rated; VCP–VDRAIN 1uF16V; VGLS–GND 1uF16V; DVDD–GND 1uF; VM–GND 100nF +10uF; VREF–AGND100nF.
- VM deliberately uses bus-fed auxiliary12V rather than unrestricted DC link; VDRAIN uses DC_LINK. VREF uses3V3, not1V65; CSA midpoint is internal VREF/2.
- Resistor values, DC-link capacitance, connectors and passive footprints are provisional or unselected. No validated thermal, ripple, transient, clearance or interrupt ratings.
