# Basin stability of democratic mechanisms

**Hypothesis:** Direct (PDD), representative (PRD), and liquid (PLD) democracy differ in
*basin stability* — the probability that a common-pool resource survives the run — as
adversarial agents grow from 0% to 60% of the population. Delegation-based mechanisms
give adversarial agents leverage that a flat median vote doesn't.

**Agents:** linear Q-learning (TD(0), epsilon-greedy over a per-agent linear Q-function;
see `policies.py` — pure JAX, vmappable). This superseded an earlier heuristic rule-based
design; that design's spec, `AGENT_ARCHITECTURE.md`, lives only on the archived branch
tag `archive/RL_Experiments` and is **not current** — do not resurrect it.

**Run:**

```bash
python -m experiments.basin_stability.run_experiment --quick                 # 10 seeds, sanity check
python -m experiments.basin_stability.run_experiment --n_seeds 500 --vmap --plot
```

**Expected output:** `results/summary_<timestamp>.csv` (one row per mechanism ×
adversarial-fraction condition, Wilson CI on survival probability) and
`results/trajectory_<timestamp>.csv`; with `--plot`, resource-vs-adversarial-fraction
and per-mechanism trajectory figures. Basin stability should decline with adversarial
fraction; the mechanisms separate in *how fast*.

**Status:** pre-dates the `_template/` contract — `run_experiment.py` does config +
sweep + save + plot inline rather than the `config.py`/`run.py`/`figures.py` split.
Migration to the template shape is a reasonable first contribution.
