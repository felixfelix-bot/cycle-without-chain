# Custom powerboard concept report

Delivered [bounded concept](docs/evaluation/custom-powerboard-concept.md), [candidate BOM](docs/evaluation/custom-powerboard-bom.csv), [block diagram](docs/evaluation/custom-powerboard-block.svg) and reproducible arithmetic model. Not a PCB, fabrication release or procurement BOM.

Key findings: 48 V-class packs can reach58.4 V; DRV8353 VM recommended limit is75 V despite100 V headline. Generator nominal torque and gear ratio are a significant open constraint. No measured machine map or80% efficiency result obtained. Preserve two mechanical brakes and reversible mounting; no clamp torque specified.

Primary TI/ST PDFs and manufacturer/vendor machine listings checked; maxon direct fetch failed, manufacturer indexed catalog/shop evidence retained with explicit availability caveat. Only maxon price is recorded, as an indexed indicative price, not a quote. Safety-critical parts and optional storage DC/DC are intentionally unresolved release blockers.

Validation: arithmetic model run, SVG XML and CSV structure checked, git whitespace check. No hardware tests. GitHub feature branch only; parent review required before any merge. ngit not attempted: existing report records unusable signing key; no bypass authorized.
