# `analysis/cx` — the two closed contradictions

Two documents each printed two mutually exclusive numbers with nothing saying
which one was current. Neither was resolved by picking a side: both were resolved
by recomputing from the network/model the corpus already contains.

| gate | what was contradictory | how it was resolved | result |
|---|---|---|---|
| CX-01 | OV minimum turn-on: `protection-milestone-report.md` printed 59.417 V from a 0–0.4 V comparator output-low corner; `protection-integration-review.md` said 0.4 V is the 25 °C limit and the full-temperature limit is 0.55 V | `ov_threshold.py` re-sweeps the same divider/reference network from the same datasheet limits, at both low corners | qualified minimum **59.315 V**, band 59.315–61.226 V, shift **0.1018 V**, margin **0.915 V** to the provisional 58.4 V bus maximum |
| CX-03 | Regen recovery: §0/§2 printed 8.2 Wh at 65 % single hop; §12 recomputed a two-hop 0.791² chain to 7.9 Wh and called 8.2 Wh superseded, while both stayed printed | `regen_recovery.py` reruns the committed model's arithmetic, and a test parses the real model stdout so the two cannot drift | current figure **7.88 Wh = 14.2 %** of trip; the 8.2 Wh figure is marked superseded in place everywhere it appears, with a pointer to §12 |

```sh
python3 analysis/cx/ov_threshold.py
python3 analysis/cx/regen_recovery.py
python3 -m unittest discover -s analysis/cx -p 'test_*.py' -v      # 20 tests
python3 -O -m unittest discover -s analysis/cx -p 'test_*.py' -v   # 20 tests
```

`evidence/` holds the RED runs taken before each helper existed
(`ov-red.log`, `regen-red.log`) and the green runs and script output in both
modes.

## What these scripts do not do

They are corner arithmetic on datasheet limits, not electrical qualification.
Neither closes PROT-07 (the OV band still assumes a VOL limit specified at
VID = −1 V also holds at the threshold's ~0 V overdrive, and still ignores
tracking, ageing and reference load regulation) or DRV-01 (the 86 %/92 % regen
hops are CITED/ESTIMATE, not measured). They decide which of two printed numbers
is current; they do not make either one a measurement.
