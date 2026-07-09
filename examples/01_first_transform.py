"""The whole CI Lib pattern in one file: a state, one transform, run it.

A shared lake: N agents draw from a common stock every round; the stock regrows
logistically. Sustainable agents take a fixed small amount; exploiters take a
fraction of whatever is left. Run it and watch whether the commons survives.

    python examples/01_first_transform.py            # full run
    python examples/01_first_transform.py --smoke    # tiny run (used by tests)

Try N_EXPLOITERS = 0 vs 3 — with 3 the take outruns regrowth and the lake
collapses; with 0 it settles at a high equilibrium. That one-line change is the
tragedy of the commons.
"""
import argparse

import jax
import jax.numpy as jnp

from cilib.core import GraphState, transform, run_scan


def main(n_agents: int, n_exploiters: int, n_steps: int, seed: int) -> float:
    # --- STATE ----------------------------------------------------------------
    # Everything that EVOLVES lives in GraphState (a JAX pytree):
    #   node_types: 0 = sustainable, 1 = exploiter        (static per-agent label)
    #   global_attrs["lake"]: a JAX array -> DYNAMIC state (it changes every round)
    # Static config (regrowth rate, capacity) is CLOSED OVER by the transform
    # below — never stored in global_attrs. That's one of the functional
    # imperatives: swept/per-step data in global_attrs forces recompiles.
    node_types = jnp.arange(n_agents) < n_exploiters          # bool: first k exploit
    init_state = GraphState(
        node_types=node_types.astype(jnp.int32),
        node_attrs={},
        adj_matrices={},
        global_attrs={"lake": jnp.array(1000.0)},
    )

    # --- THE ONE TRANSFORM ------------------------------------------------------
    # A Transform is a pure function GraphState -> GraphState. @transform declares
    # what it reads and writes so the pipeline compiler (example 02) can order it.
    capacity, regrowth_rate = 2000.0, 0.15                    # closed-over config

    @transform(reads=["lake"], writes=["lake"])
    def lake_step(state: GraphState) -> GraphState:
        lake = state.global_attrs["lake"]
        is_exploiter = state.node_types == 1
        # jnp.where, not a Python `if` — a traced value can't drive Python control
        # flow inside lax.scan (functional imperative #4).
        per_agent_take = jnp.where(is_exploiter, 0.02 * lake, 5.0)
        stock = jnp.maximum(lake - per_agent_take.sum(), 0.0)
        regrown = stock + regrowth_rate * stock * (1.0 - stock / capacity)
        return state.update_global_attr("lake", regrown)

    # --- RUN ---------------------------------------------------------------------
    # run_scan compiles the round into a single lax.scan — the body is traced once,
    # not Python-looped n_steps times. round_fn's contract is (state, t, key);
    # this deterministic round needs neither t nor key, but must match the shape.
    def round_fn(state, t, key):
        return lake_step(state)

    final_state, lake_trace = run_scan(
        round_fn, init_state, n_steps, jax.random.PRNGKey(seed),
        trace_fn=lambda s: s.global_attrs["lake"],
    )

    # --- PROOF IT WORKED -----------------------------------------------------------
    final = float(final_state.global_attrs["lake"])
    low, low_at = float(lake_trace.min()), int(lake_trace.argmin())
    print(f"agents: {n_agents} ({n_exploiters} exploiters) | rounds: {n_steps}")
    print(f"initial lake: 1000.0")
    print(f"final lake:   {final:.1f}")
    print(f"lowest point: {low:.1f} at round {low_at}")
    print("status:", "COLLAPSED" if final < 1.0 else "SURVIVED")
    return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="tiny run for tests")
    args = parser.parse_args()
    if args.smoke:
        main(n_agents=4, n_exploiters=1, n_steps=5, seed=0)
    else:
        main(n_agents=10, n_exploiters=3, n_steps=150, seed=0)
