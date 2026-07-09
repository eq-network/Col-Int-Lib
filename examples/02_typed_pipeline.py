"""Composing transforms: declare effects, let the compiler find the DAG.

Same lake as example 01, now governed. Agents vote a quota (median vote =
direct democracy), harvest under that quota, the lake regrows, and each agent's
wealth is scored. Four transforms, each declaring what it reads and writes —
`compile_pipeline` derives the execution order from those sets and batches
independent steps together, instead of you hand-writing the order.

    python examples/02_typed_pipeline.py             # full run
    python examples/02_typed_pipeline.py --smoke     # tiny run (used by tests)
"""
import argparse

import jax
import jax.numpy as jnp

from cilib.core import (
    GraphState, transform, sequential, compile_pipeline, get_execution_order,
    run_scan,
)


def main(n_agents: int, n_exploiters: int, n_steps: int, seed: int):
    # --- STATE ----------------------------------------------------------------
    # Per-agent data lives in node_attrs; shared scalars live in global_attrs.
    # Every field a transform will ever write must exist from t=0 — lax.scan
    # requires the pytree structure to stay constant across rounds.
    is_exploiter = (jnp.arange(n_agents) < n_exploiters)
    votes = jnp.where(is_exploiter, 30.0, 4.0)     # preferred per-agent quota
    init_state = GraphState(
        node_types=is_exploiter.astype(jnp.int32),
        node_attrs={
            "vote": votes,
            "last_harvest": jnp.zeros(n_agents),
            "wealth": jnp.zeros(n_agents),
        },
        adj_matrices={},
        global_attrs={"lake": jnp.array(1000.0), "quota": jnp.array(0.0)},
    )

    capacity, regrowth_rate = 2000.0, 0.15         # closed-over static config

    # --- FOUR TRANSFORMS, EFFECTS DECLARED -----------------------------------------
    @transform(reads=["vote"], writes=["quota"])
    def vote_pdd(state):
        """Direct democracy: the median vote becomes the per-agent quota."""
        return state.update_global_attr("quota", jnp.median(state.node_attrs["vote"]))

    @transform(reads=["quota", "vote", "lake"], writes=["lake", "last_harvest"])
    def harvest(state):
        """Each agent takes min(what it wants, the quota), capped by the stock."""
        lake, quota = state.global_attrs["lake"], state.global_attrs["quota"]
        desired = state.node_attrs["vote"]                     # wants what it voted for
        take = jnp.minimum(desired, quota)
        # If the lake can't cover the total, scale everyone down (jnp.where — no
        # data-dependent Python `if` inside a scanned round).
        total = take.sum()
        scale = jnp.where(total > lake, lake / jnp.maximum(total, 1e-9), 1.0)
        take = take * scale
        return (state
                .update_global_attr("lake", jnp.maximum(lake - take.sum(), 0.0))
                .update_node_attrs("last_harvest", take))

    @transform(reads=["lake"], writes=["lake"])
    def regrow(state):
        lake = state.global_attrs["lake"]
        return state.update_global_attr(
            "lake", lake + regrowth_rate * lake * (1.0 - lake / capacity))

    @transform(reads=["last_harvest", "wealth"], writes=["wealth"])
    def score(state):
        return state.update_node_attrs(
            "wealth", state.node_attrs["wealth"] + state.node_attrs["last_harvest"])

    steps = [vote_pdd, harvest, regrow, score]

    # --- THE COMPILER FINDS THE ORDER — AND THE PARALLELISM --------------------------
    # regrow (lake -> lake) and score (last_harvest -> wealth) touch disjoint
    # state, so they commute: the compiler puts them in the same batch on its own.
    print("derived execution order:")
    for i, batch in enumerate(get_execution_order(steps)):
        print(f"  batch {i}: {[t.name for t in batch]}")

    pipeline = compile_pipeline(steps)

    # --- RUN, AND VERIFY THE COMPILATION CHANGED NOTHING ------------------------------
    # CLAUDE.md's rule for composition changes, as executable code: the compiled
    # pipeline must be numerically identical to the hand-ordered sequential(...)
    # for a fixed seed.
    key = jax.random.PRNGKey(seed)
    run = lambda step: run_scan(lambda s, t, k: step(s), init_state, n_steps, key,
                                trace_fn=lambda s: s.global_attrs["lake"])
    seq_final, _ = run(sequential(*steps))
    pipe_final, lake_trace = run(pipeline)

    assert jnp.allclose(seq_final.global_attrs["lake"], pipe_final.global_attrs["lake"])
    assert jnp.allclose(seq_final.node_attrs["wealth"], pipe_final.node_attrs["wealth"])
    print("[OK] compile_pipeline matches sequential(...) exactly for a fixed seed")

    # --- PROOF IT WORKED ----------------------------------------------------------------
    wealth = pipe_final.node_attrs["wealth"]
    print(f"final lake after {n_steps} rounds: {float(pipe_final.global_attrs['lake']):.1f}"
          f"  (quota = median vote = {float(pipe_final.global_attrs['quota']):.1f})")
    print(f"mean wealth  sustainable: {float(wealth[~is_exploiter].mean()):.1f}"
          f" | exploiter: {float(wealth[is_exploiter].mean()):.1f}  (equal — the"
          f" quota binds everyone to the median vote)")
    print("governed, the commons survives; rerun example 01 to see it collapse ungoverned.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="tiny run for tests")
    args = parser.parse_args()
    if args.smoke:
        main(n_agents=4, n_exploiters=1, n_steps=5, seed=0)
    else:
        main(n_agents=10, n_exploiters=3, n_steps=150, seed=0)
