# Series-hybrid feasibility documentation report

## Delivered scope

[Current plan](docs/PLAN-parallel-hybrid.md) and [README](README.md) now prioritize independent-cadence series feasibility: PM generator, active rectifier, shared DC bus, hub inverter and storage branch. Parallel assistance/regen is only a baseline; its mechanical gears still control cadence and it offers no stationary charging. No build is purchased or tested. Series startup, stationary charging, cadence regulation, battery/BMS compatibility and independent friction braking require validation. Scope was revised on user instruction before any commit/merge.

CIXI 2026 catalog specifications were fetched directly; they are vendor claims, not measurements. The reported older professional-page table was not present in the live text extraction, so mass/power/version discrepancies remain unresolved. The 80% cruise target is illustrative; the pasted GaN 65%→86% system-efficiency claim is unsupported.

The plan supersedes historical purchasing recommendations and records unsupported product topology/efficiency claims, ambiguous “5%” claims, assumed rather than measured efficiency ceilings, direct-bus versus storage boundaries, the regen arithmetic/battery-factor error and the battery-deficit denominator error. Existing model and diagrams are deliberately unchanged, not endorsed.

## Checks performed

- Relative Markdown links resolve from their document directories; README/plan headings are unique.
- `git diff --check`: passed before landing.
- Arithmetic check: `0.86 ** 2 * 0.92 = 0.680432`; this checks arithmetic only, not physical efficiency.
- `chainless_drivetrain_model.py`, `make_blend_figure.py`, `make_explainer.py`: smoke-run from scratch copies, all exit 0.
- `render_diagram.py`: smoke-run with its hardcoded shared-checkout output path redirected in memory to scratch; exit 0. Repository script unchanged.
- Smoke logs/artifacts: `/home/c08r4d0r/.hermes/profiles/manager/cache/scratch/cycle-plan-smoke/` (local, ephemeral, not committed).
- No model rewrite, hardware measurements, procurement, legal determination or scientific validation performed. Exit 0 proves execution only; generated historical diagrams remain unvalidated.

## Landing and limitations

Concurrent default-branch update preserved by rebase onto `e6c6aa9a7d8d530c216d7fca3e5b468f0f9de1c2`: existing pedal-by-wire plan and README link retained, with an explicit companion-plan link and storage-comparison scope note.

Initial base: GitHub `master` at `76beaf1487583dc6b4f533172fb9e54c9637e783`. User authorized default-branch landing. Final commit, clean-tree state and live GitHub SHA are verified after commit and reported in the delivery summary rather than embedded circularly here.

ngit mirror is blocked by the reported unusable signing key. No key hunt or verification-hook bypass is authorized; this delivery makes no ngit synchronization claim.
