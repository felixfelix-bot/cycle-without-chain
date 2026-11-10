# `analysis/gates` — document consistency checks

Not to be confused with [`tools/gates`](../../tools/gates/), which holds the
fail-closed **PCB release** gates (ERC/DRC, netlist parity, release manifest).

This directory holds checks on **documents**, not on hardware artifacts.

## `register_check.py`

Lints [`docs/design/open-gates-register.md`](../../docs/design/open-gates-register.md):

* every gate row has an ID of the form `PREFIX-NN`, unique across the table;
* every row has exactly the declared number of columns;
* every row's bucket is one of `A`, `B`, `C`, `D` and is not empty;
* every row cites a document (`*.md`, `*.csv`, `*.py`, ...) **and** a section
  (`§`);
* the bucket-summary table's counts equal the counts of rows per bucket.

Exit codes follow the same contract as `tools/gates`: `0` PASS, `1` FAIL,
`2` NOT RUN (no register, no gate table, no summary table). No module uses
`assert`, so normal and `-O` execution behave identically.

**This is a well-formedness check, not an engineering proof.** It cannot tell
whether a gate is in the right bucket, whether the cited section really raises
that gate, or whether a `D` row was honestly closed. Those are review
judgements. A green run must never be cited as evidence that the design is
electrically safe, road legal or manufacturable.

```sh
python3 analysis/gates/register_check.py docs/design/open-gates-register.md
python3 -m unittest discover -s analysis/gates/tests -v      # 16 tests
python3 -O -m unittest discover -s analysis/gates/tests -v   # 16 tests
```

`evidence/` keeps the RED run captured before the implementation existed
(`register-check-red.log`, 13 of 16 failing) and the green runs in both modes.
