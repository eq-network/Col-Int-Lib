"""vmap over seeds + agents that learn: the JAX value proposition.

Same lake, third variant: no fixed rules anymore. Every agent has its own
linear Q-function and picks an extraction level by epsilon-greedy selection,
updated by TD(0) after every round. Then the whole episode — all agents, all
rounds — runs for MANY independent seeds as ONE compiled program:
`run_scan_batch` = `jax.vmap(lax.scan(...))`, not a Python loop over runs.

The printed result is a toy version of `experiments/basin_stability`:
basin stability = the fraction of seeds whose commons survives.

    python examples/03_vmap_seeds_and_learning.py            # full run
    python examples/03_vmap_seeds_and_learning.py --smoke    # tiny run (tests)
"""
import argparse

import jax
import jax.numpy as jnp
import jax.random as jr

from cilib.core import GraphState, run_scan_batch

# --- Q-LEARNING PRIMITIVES (pure JAX, vmappable) --------------------------------
# Inlined in spirit from experiments/basin_stability/policies.py so this example
# never depends on experiments/ (which is not part of the installed package).
# Q(s, a) = w_a . s + b_a — one linear Q-function per agent.

ACTIONS = jnp.array([2.0, 6.0, 12.0])          # extraction levels: low / med / high


def q_select(q_w, q_b, state_vec, key, epsilon):
    """Epsilon-greedy action for ONE agent; vmapped across agents below."""
    qvals = q_w @ state_vec + q_b                              # (A,)
    k_explore, k_action = jr.split(key)
    greedy = jnp.argmax(qvals)
    rand = jr.randint(k_action, (), 0, ACTIONS.shape[0])
    return jnp.where(jr.uniform(k_explore) < epsilon, rand, greedy)


def q_update(q_w, q_b, state_vec, action, reward, next_vec, alpha, gamma):
    """TD(0) on the chosen action's weights only."""
    target = reward + gamma * jnp.max(q_w @ next_vec + q_b)
    td_err = target - (q_w[action] @ state_vec + q_b[action])
    q_w = q_w.at[action].add(alpha * td_err * state_vec)
    q_b = q_b.at[action].add(alpha * td_err)
    return q_w, q_b


def main(n_agents: int, n_seeds: int, n_steps: int, seed: int) -> float:
    capacity, regrowth_rate = 2000.0, 0.15
    epsilon, alpha, gamma = 0.1, 0.05, 0.9
    state_dim = 2                                              # [stock, own last take]

    def obs(lake, last_take):
        """Per-agent observation matrix (N, D), normalized to ~[0, 1]."""
        stock = jnp.full((n_agents,), lake / capacity)
        return jnp.stack([stock, last_take / ACTIONS[-1]], axis=1)

    def init_fn(key):
        """Per-seed initial state — runs under vmap, so no dynamic shapes."""
        q_w = 0.01 * jr.normal(key, (n_agents, ACTIONS.shape[0], state_dim))
        return GraphState(
            node_types=jnp.zeros(n_agents, dtype=jnp.int32),
            node_attrs={
                "q_w": q_w,
                "q_b": jnp.zeros((n_agents, ACTIONS.shape[0])),
                "last_take": jnp.zeros(n_agents),
            },
            adj_matrices={},
            global_attrs={"lake": jnp.array(1000.0)},
        )

    def round_fn(state, t, key):
        # Stochastic policies use the per-round key run_scan threads in — RNG is
        # part of the scan discipline, so the round stays a pure function.
        lake = state.global_attrs["lake"]
        q_w, q_b = state.node_attrs["q_w"], state.node_attrs["q_b"]
        s_vec = obs(lake, state.node_attrs["last_take"])                   # (N, D)

        keys = jr.split(key, n_agents)
        actions = jax.vmap(q_select, in_axes=(0, 0, 0, 0, None))(
            q_w, q_b, s_vec, keys, epsilon)                                # (N,)
        take = ACTIONS[actions]
        # Cap the total draw by the stock (jnp.where — no Python `if` on traced values).
        scale = jnp.where(take.sum() > lake, lake / jnp.maximum(take.sum(), 1e-9), 1.0)
        take = take * scale

        new_lake = jnp.maximum(lake - take.sum(), 0.0)
        new_lake = new_lake + regrowth_rate * new_lake * (1.0 - new_lake / capacity)

        # Reward: own harvest plus a share of the commons' health — enough signal
        # for TD(0) to feel the externality of over-extraction.
        reward = take + 0.02 * new_lake
        next_vec = obs(new_lake, take)
        q_w, q_b = jax.vmap(q_update, in_axes=(0, 0, 0, 0, 0, 0, None, None))(
            q_w, q_b, s_vec, actions, reward, next_vec, alpha, gamma)

        return (state
                .update_global_attr("lake", new_lake)
                .update_node_attrs("q_w", q_w)
                .update_node_attrs("q_b", q_b)
                .update_node_attrs("last_take", take))

    # --- ONE PROGRAM, MANY WORLDS ----------------------------------------------------
    seed_keys = jr.split(jr.PRNGKey(seed), n_seeds)
    batch_final, lake_traces = run_scan_batch(
        round_fn, init_fn, n_steps, seed_keys,
        trace_fn=lambda s: s.global_attrs["lake"])                         # (B, T)

    survived = (batch_final.global_attrs["lake"] > 50.0)
    p_survival = float(survived.mean())
    print(f"{n_agents} learning agents x {n_steps} rounds x {n_seeds} seeds")
    print(f"{int(survived.sum())}/{n_seeds} seeds survived collapse "
          f"(P survival = {p_survival:.2f})")
    print(f"mean final stock across seeds: "
          f"{float(batch_final.global_attrs['lake'].mean()):.1f}")
    print("this ran as a single jax.vmap(lax.scan) program, "
          "not a Python loop over seeds.")
    return p_survival


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="tiny run for tests")
    args = parser.parse_args()
    if args.smoke:
        main(n_agents=4, n_seeds=4, n_steps=5, seed=0)
    else:
        main(n_agents=10, n_seeds=200, n_steps=300, seed=0)
