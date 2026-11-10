# RED -> GREEN evidence

Recorded while building this package. The RED run below was taken with the
test suite complete and the gate modules absent (the tests were written first,
as required by the task); every subsequent RED shown was a real failing test
that exposed a defect in the code, not a typo in the test.

## RED: no gate modules exist yet

The suite was written first. With `tools/gates/` holding only `__init__.py`,
the first run failed on the very first test because the module did not exist:

```
$ PYTHONPATH=. python3 -m pytest tests/gates -x -q
E   ModuleNotFoundError: No module named 'tools.gates.native_reports'
1 failed in 0.11s
```

Replaying that now (the suite has grown since) reproduces it across the whole
package, in a copy of this tree with the implementation modules removed:

```
$ PYTHONPATH=. python3 -m pytest tests/gates -q \
      --ignore=tests/gates/test_input_validation.py \
      --ignore=tests/gates/test_native_reports_parsers.py
111 failed, 2 passed in 5.23s
```

The two collection errors in the ignored files are the same missing modules:
those two files import the gate package directly. The two tests that pass are
the ones that only assert on the *absence* of a gate (`--list` on an argument
parser with no gate list) and on a fixture helper.

## RED -> GREEN defects the tests found during implementation

Each of these was a genuine defect, found by a test, fixed in the module:

| Failing test | Defect it exposed | Fix |
|---|---|---|
| `test_erc_without_sheets_fails` | ERC "objects scanned" came only from the report's sheet count, so a report covering no sheet could still pass | `report_covers_sheets` check; objects counted from the schematic hierarchy |
| `test_count_symbols_handles_both_spellings` | `_count_symbols` added two substring counts that overlapped, double-counting every symbol | single regex `SYMBOL_RE` |
| `test_negative_control_duplicate_row_inside_one_net_fails` | A duplicate `(ref,pin)` row inside one net was silently de-duplicated by set semantics | explicit `duplicate_free` check on the parsed rows |
| `test_negative_control_extra_net_fails_even_when_endpoints_match` | A declared net with no rows vanished from the comparison | declared net names compared as their own set |
| `test_negative_control_nc_pin_that_is_connected_fails` | The NC assertion compared `(ref,pin,net)` triples against `(ref,pin)` pairs, so it could never fire | compare against `{(ref,pin)}` built from the endpoints |
| `test_check_gerber_*` | The `%FSLAX` regex demanded an `X` that KiCad does not emit (`%FSLAX46Y46*%`) | corrected pattern |
| `test_negative_control_tiny_gerber_fails` | Size floor was checked before content, so a placeholder reported only "too small" | content diagnosis first, size floor as fallback |
| `test_load_manifest_requires_each_required_kind` | A copper-count contradiction was reported as a missing-kind error | explicit `copper_layers=` message, kept `NOT RUN` |

A **real** KiCad 9.0.9 run then found one more, which no fixture had: see
`README.md` "Real-tool evidence" — a hierarchical root sheet holds no symbols,
so `_count_symbols` on the named file alone reported 0 objects for a populated
design. Fixed by counting across the project's sheets.

## GREEN

```
$ PYTHONPATH=. python3 -m pytest tests/gates -q
198 passed in 11.82s

$ PYTHONPATH=. python3 -O -m pytest tests/gates -q
198 passed, 1 warning in 11.54s     # warning: pytest's own assert-rewrite notice

$ coverage (branch), subprocesses measured via a sitecustomize hook
TOTAL  854 stmts  96%
  _common.py          94%
  native_reports.py   97%
  netlist_parity.py   99%
  release_manifest.py 98%
  run_all_gates.py    92%
```
