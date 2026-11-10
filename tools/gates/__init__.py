"""Fail-closed quality gates for the pedal-by-wire board artifacts.

Design contract (see README.md in this directory):
  * exit 0  -> PASS, and only when every precondition was actually verified
  * exit 1  -> FAIL, the gate ran and the artifact did not survive it
  * exit 2  -> FAIL, the gate could not run (usage, missing/unreadable input)

Every module prints one machine-readable JSON object on stdout and human
readable detail on stderr. No module relies on ``assert``: the suite is also
run under ``python3 -O`` where assertions are stripped.
"""

GATE_PACKAGE_VERSION = "1.0.0"
