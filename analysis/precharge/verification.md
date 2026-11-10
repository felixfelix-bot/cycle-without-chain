# Executed verification

2026-11-10, Python 3.11.15, isolated feature worktree.

- RED: unittest discovery before model existed: ModuleNotFoundError: model, exit 1.
- Intermediate: 12 tests, hot-bus test FAILED because sink reduced voltage before CHECK. Initial condition now latches hot-bus fault.
- GREEN: `python3 -m unittest discover -s tests`: 13 tests, OK, 7.044 s.
- GREEN optimized: `python3 -O -m unittest discover -s tests`: 13 tests, OK, 9.433 s.
- `python3 model.py`: exit 0; actual stdout stored in results.json.
- `command -v ngspice`: /usr/bin/ngspice. Available, not used: this deliverable deliberately uses the permitted explicit source/R/C/load stdlib solver. No vendor MOSFET, converter or analog sequencer simulation is claimed.

Model sensor and switching decisions are ideal. Injected welded=True diagnosis is an oracle, not demonstrated fault detection. No source current limiter is supplied by the proposed FET drivers. Actual source limits, auxiliary envelopes, component analog pin implementation, SOA, sink cold-start and fault tolerances are qualification gaps.

Only analysis/precharge and docs/design/precharge-sequencing-design.md changed. No hardware/README files changed.

Publication: initial coherent commit 945d090127ebf47ee1602d4c436093ffe443fa8d pushed and independently matched github branch ref. Attempted ngit mirror failed: no repository announcement at existing remote coordinates. No init/key/remote changes made; parent should resolve mirror separately.
