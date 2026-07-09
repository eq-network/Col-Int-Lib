# Governed commons harvest

**Hypothesis:** An earlier, smaller CPR study than `basin_stability/` — the same
PDD/PRD/PLD governance family plus an ungoverned baseline, on a bandit/vote harvest
game with Fehr-Schmidt inequality-averse rewards, swept over adversarial concentration.
Governed regimes should survive longer than the baseline as adversarial share rises.

**Run:**

```bash
python -m experiments.governed_harvest.run_experiment
```

**Expected output:** `results/sweep_<timestamp>.json` plus a printed mean-survival-time
table (mechanism × adversarial fraction).

**Status:** prototype pre-dating both the `_template/` contract and
`@transform`/`compile_pipeline` (its `transforms.py` composes with plain `sequential`).
Superseded in scope by `basin_stability/` — kept as a smaller, older reference, not the
one to extend.
