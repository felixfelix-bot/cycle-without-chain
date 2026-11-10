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

## RED -> GREEN, round 2: TOOL-01 and RAIL-12

Both gates were written test-first; the RED output below is the real failing run
captured before the implementation existed, and the failure in each case names
the missing behaviour rather than a typo in the test.

### RED: RAIL-12 (`tests/gates/test_netlist_parity_pair.py`, 12 failed, 2 passed)

```
$ PYTHONPATH=. python3 -m pytest tests/gates/test_netlist_parity_pair.py -q
FAILED test_both_artifacts_matching_one_expected_map_pass
FAILED test_single_artifact_mode_is_unchanged
FAILED test_negative_control_intra_rail_split_injected_into_xml_only_fails
FAILED test_negative_control_injection_into_sexpr_only_fails
FAILED test_negative_control_artifacts_disagree_with_each_other
FAILED test_negative_control_split_in_both_artifacts_against_stale_map_fails
FAILED test_negative_control_sexpr_pin_on_two_nets_fails
FAILED test_malformed_sexpr_artifact_fails
FAILED test_sexpr_without_nets_element_fails
FAILED test_real_sexpr_export_parses_to_the_committed_contract
FAILED test_real_both_artifacts_agree_with_the_committed_pin_map
FAILED test_real_xml_injection_is_caught_against_the_real_sexpr
12 failed, 2 passed
```

The two that passed are the ones asserting the *old* single-artifact contract
still works — they were supposed to pass, and they pin that contract so the new
wiring could not break it silently.

The defect itself, on the head this branch started from, is reproducible as a
one-shot script (`tools/gates/red_rail12_injection.py`, captured before the
change):

```
1. gate on the clean committed XML               -> 0 PASS
2. gate on that XML with a DRIVE12 split injected -> 1 FAIL  extra nets: ['DRIVE12_SPLIT']
3. gate pointed at the S-expression `.net`        -> 1 FAIL  usage error (reads XML only)
4. gate on BOTH artifacts at once                -> 2 NOT RUN  unrecognized arguments: --netlist-sexpr
5. files that invoke netlist_parity on this head -> none
```

Read 3 and 4 together with 5: the gate could not read the `.net` at all, could
not be handed both, and nothing on the head invoked it. A split injected into
the XML alone was therefore invisible to every check that actually ran. After
the change the same script prints 3 as `0` (the untouched `.net` still passes on
its own — that is the blind spot) and 4 as `1 FAIL` (the pair catches it).

### RED: TOOL-01 (`tests/gates/test_gate_wiring.py`, 19 failed)

```
$ PYTHONPATH=. python3 -m pytest tests/gates/test_gate_wiring.py -q
FAILED test_one_command_runs_the_gates_and_reports_what_it_cannot_run
FAILED test_the_one_command_is_the_documented_one
FAILED test_failing_gate_fails_the_runner
FAILED test_ci_mode_is_green_only_for_the_gates_that_ran
FAILED test_ci_mode_never_turns_a_failure_green
FAILED test_missing_board_is_not_run_with_a_reason_naming_the_board
FAILED test_board_present_but_tool_absent_is_not_run_naming_the_tool
FAILED test_release_manifest_without_a_packet_is_not_run
FAILED test_runner_works_from_another_cwd
FAILED test_summary_lists_every_selected_gate
FAILED test_gate_selection_limits_what_runs
FAILED test_unrunnable_selection_is_not_run_not_a_crash
FAILED test_real_tree_parity_gate_passes_on_the_committed_artifacts
FAILED test_workflow_runs_on_push_and_pull_request
FAILED test_workflow_invokes_the_tested_script_with_the_ci_summary_flag
FAILED test_workflow_has_no_continue_on_error_on_the_gate_step
FAILED test_workflow_does_not_swallow_the_exit_code_with_a_trailing_command
FAILED test_workflow_installs_only_what_it_needs_and_says_so
FAILED test_workflow_is_valid_yaml_and_has_a_job
19 failed, 2 passed
```

### Defects the tests found during implementation

| Failing test | Defect it exposed | Fix |
|---|---|---|
| `test_unrunnable_selection_is_not_run_not_a_crash` | `--ci` treated "every selected gate was skipped" as a green run | CI mode tolerates `NOT RUN` only when at least one gate actually graded |
| `test_negative_control_artifacts_disagree_with_each_other` | the first draft re-used one comparison result for both artifacts, so `sexpr_` checks duplicated the XML ones | `_grade_one()` grades one parsed artifact at a time |
| `test_malformed_sexpr_artifact_fails` | parse failures and structure failures were both reported under `sexpr_parseable` | separate `SexprParseError` / `SexprStructureError` and separate checks |

### GREEN

```
$ PYTHONPATH=. python3 -m pytest tests/gates -q
233 passed in 14.14s

$ PYTHONPATH=. python3 -O -m pytest tests/gates -q
233 passed, 1 warning in 16.70s

$ python3 analysis/gates/register_check.py docs/design/open-gates-register.md
PASS: ... well-formed, cited, counts agree (A=52 B=35 C=12 D=10)

$ actionlint .github/workflows/release-gates.yml
(clean)

$ python3 tools/gates/run_release_gates.py --ci
native_reports:   NOT RUN (no board file: ... .kicad_pcb does not exist ...)
netlist_parity:   PASS (13 checks)
release_manifest: NOT RUN (no release manifest ...)
aggregate: PASS     exit 0

$ python3 tools/gates/run_release_gates.py          # local mode
aggregate: NOT RUN  exit 2      # NOT RUN is a failure unless --ci
```

The workflow itself was observed running on GitHub on this branch
(`release-gates`, runs 42900758555, 42903005652, 42903800007, 42903808251 — all
`success`), with the gate step logging `netlist_parity: PASS` and the two
`NOT RUN` reasons above. The 198 tests that existed before this branch still
pass; the suite is 233 now.

## GREEN (round 1, unchanged)

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
