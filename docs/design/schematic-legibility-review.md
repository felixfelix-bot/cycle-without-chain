# Schematic legibility presentation milestone

**NOT safe to energize, fabricate or ride.** This is a presentation repair, not
rail redesign, electrical approval or closure of any FSR safety qualification.
Baseline: `22ae0f4` (includes FSR review `3bb995d` and navigation consolidation).

## Changes and invariants

The generator limits its new layout policy to pages 20–27: brake interfaces,
dump logic, offboard switch harness, both FSR frontends and both FSR protection
sheets. Horizontal global-label bodies now extend away from pins; resistor and
capacitor fields sit to the right of vertical wiring; other reference/value
fields sit above the highest pins. No symbol location, wire endpoint, net,
component identity/value/footprint, pin type, NC, warning or component count was
changed. The other sheets retain their original geometry (SVG timestamps change
because the entire 27-page project was freshly exported with KiCad 9.0.9).

Native XML exports before and after are retained under
`hardware/powerboard-reva/exports/legibility-{before,after}.xml`.
`check_presentation_invariant.py` independently parses these with ElementTree,
not the generator or existing S-expression verifier. Its sorted exact
`(reference,pin,net)` lists match: **1007 rows = 956 connected endpoints plus
51 native unconnected-pin net entries**. All **314 reference/value/footprint
triples** match exactly, with no component growth. Canonical data is retained
in `exports/legibility-canonical.json`. This is an electrical *invariance*
check, not validation that the inherited circuit is electrically safe.

## Measured native SVG geometry

`check_legibility.py` measures actual KiCad stroked glyph bounds expanded by
0.0762 mm (half the rendered 0.1524 mm stroke), rather than assuming dimensions
from invisible SVG text fonts. It compares text/text and text/straight graphical
stroke bounds. All eight circuit regions are checked, with full bounds retained
in `exports/legibility-{before-bounds,bounds}.json`.

| Page | Before text/text | Before text/stroke | After both |
|---|---:|---:|---:|
| 20 LEFT binary brake | 3 | 17 | 0 / 0 |
| 21 RIGHT binary brake | 4 | 17 | 0 / 0 |
| 22 dump command | 7 | 20 | 0 / 0 |
| 23 offboard switch harness | 3 | 16 | 0 / 0 |
| 24 LEFT FSR | 13 | 47 | 0 / 0 |
| 25 LEFT FSR protection | 4 | 13 | 0 / 0 |
| 26 RIGHT FSR | 15 | 47 | 0 / 0 |
| 27 RIGHT FSR protection | 4 | 13 | 0 / 0 |

Example measured bounds (mm, xMin/yMin/xMax/yMax): R128 reference
`143.8473/51.3033/148.3540/52.7257`; its value
`143.7162/53.9798/160.9471/55.1482`. Both clear the vertical x=139.7 branch
by more than 3.9 mm including line half-width. J46 reference:
`49.2119/37.2729/52.3276/38.7557`; U26 reference:
`61.8514/146.5533/65.2091/147.9757`. RIGHT channel uses the same placement
with independently measured glyphs (J47/U28/U29/R135 etc.).

**Measurement limits:** circuit text region x>15 mm, y>30 mm, yMax<245 mm;
frame/title block and explanatory prose are outside this gate. Curved paths,
filled shapes, transforms other than KiCad's already-positioned stroked glyphs,
and no-connect crosses are not a general collision certificate. Global-label
outline strokes are tested, not their filled bounding rectangle: label text is
intentionally inside the outline. A first implementation falsely joined an AND
arc to its endpoint; curved paths are explicitly excluded rather than claiming
that false GND collision was real. These exclusions are not electrical ERC
suppressions. The gate is bounded to this native KiCad rendering format.

## Actual raster review and extent

Fresh PDF pages 20–27 were rasterized with `pdftoppm -scale-to 2100 -png`.
The image tool inspected full-size **24, 26 and 22**, and a 1050px-per-page
montage of **20,21,23,25,27**. It reported no visible J46/J47 or OPA/mux
label-to-pin collisions and no passive field-to-wire collisions on 24/26;
on 22 it reported the GND pin name inside U25 clear of the outside pin line.
The montage showed no definite collisions but explicitly could not conclusively
resolve connector and D36/D37/D40/D43 pin-level clearance. Those areas have
computational straight-stroke/text coverage; no full-resolution visual verdict
is claimed for them. Served model identity was not exposed by the tool, so no
cross-family visual approval is claimed. Its unsolicited component-value
transcription is not evidence (it misread one 10k as 10 ohms); exact values are
verified by native XML, not vision.

Reviewed raster SHA256:
- page24: `13ed03b55701970b30c63a6d656dac4ac9630dd730ad24fa250a7e2eb1525af7`
- page26: `ec803d6c03a7d81f6417bc593e7c9f22e2437bd35d0fbd2b9b4a93d7b05204b0`
- page22: `66859f7477773757c91023cd2c1f29e0542b5da1e0abc837c9da3d49ef69053a`

Rasters are temporary local scratch files, not promised remote attachments.
The committed fresh PDF and SVGs are the durable reviewable artifacts.

## Execution

From `hardware/powerboard-reva`:

```sh
python3 generate_schematic.py
kicad-cli sch export pdf -o exports/powerboard-reva.pdf powerboard-reva.kicad_sch
kicad-cli sch export svg -o exports/svg powerboard-reva.kicad_sch
kicad-cli sch export netlist --format kicadxml -o exports/legibility-after.xml powerboard-reva.kicad_sch
python3 check_presentation_invariant.py exports/legibility-before.xml exports/legibility-after.xml --out exports/legibility-canonical.json
python3 check_legibility.py exports/svg --out exports/legibility-bounds.json --check
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
kicad-cli sch erc --format json --exit-code-violations -o exports/legibility-erc.json powerboard-reva.kicad_sch
```

Results: **34 hardware tests passed normal (128.008s) and -O (102.192s)**,
including the two new presentation regressions. Evidence:
`exports/legibility-tests{,-O}.txt`. The regression compares frozen native
exports; rerun the native export command above before testing a new schematic.
The layout checker fails on baseline renders; endpoint mutation and synthetic
bounding-box overlap controls exercise the tests without relying on Python
`assert` statements.

Strict ERC remains **exit 5, five existing errors, zero warnings**, without
suppression: U1.24, U1.25, U3.1, U17.37, U26.5/MCU_VREF. Report:
`exports/legibility-erc.json`. All original power-source, precharge, thermal,
firmware, FSR mounting/calibration, backfeed/ESD and torque-authority blockers
remain. No electrical, manufacturing, whole-project visual or ride release is
implied. Feature milestone is for parent review before default publication.
