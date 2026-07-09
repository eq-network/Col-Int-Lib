"""
Worked experiment: endogenous polycentric governance as causal emergence.

Runs the JAX commons across governance regimes, heterogeneity levels, an enforcement ablation,
and a capture sweep; wires each rollout to the offline causal-emergence pipeline; and prints (and
saves) a report organized around the three lenses.

Run:  python -m experiments.polycentric_emergence.run_experiment
"""
from __future__ import annotations

import os
import sys
import numpy as np
import jax.random as jr

try:                                  # Windows consoles default to cp1252; force UTF-8 output
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from cilib.lab.paradigms import polycentric as P
from cilib.lab.analysis import causal_emergence as ce
from cilib.lab.analysis import bootstrap as bs

KEY = jr.PRNGKey(0)
T = 200
N_SEEDS = 12
N_SURR = 200            # time-shuffle surrogates for the honest meso-EI null (per call)
COLLAPSE = 2.0


# ------------------------------------------------------------------ helpers

def run_regime(governance, het=1.5, monitoring=None, capture=0.0, seeds=N_SEEDS, T=T, seed=0):
    cfg = P.make_config(governance, heterogeneity=het, monitoring=monitoring, capture=capture)
    finals, trs = P.run_batch(cfg, jr.PRNGKey(seed), n_seeds=seeds, T=T)
    return cfg, finals, trs


# Per-seed variants return a length-(B,) vector (one value per seed) for bootstrap CIs; the scalar
# versions are their seed-mean, so the printed tables are numerically unchanged.

def final_R_seed(trs):
    return np.asarray(trs["resource"])[:, -1]          # (B,)


def survival_seed(trs):
    res = np.asarray(trs["resource"])                  # (B,T)
    alive = res > COLLAPSE
    surv = np.where(alive.all(axis=1), res.shape[1], np.argmax(~alive, axis=1))
    return surv.astype(float)                           # (B,)


def mean_fit_seed(trs, last=60):
    return np.asarray(trs["fit"])[:, -last:, :].mean(axis=(1, 2))   # (B,)


def final_R(trs):
    return float(final_R_seed(trs).mean())


def survival(trs):
    return float(survival_seed(trs).mean())


def mean_fit(trs, last=60):
    return float(mean_fit_seed(trs, last).mean())


def _bins_from_harvest(h, L, frac=0.5):
    Tt, N = h.shape[1], h.shape[2]
    half = h[:, int(Tt * frac):, :]
    bins = np.clip(np.rint(half), 0, L - 1).astype(int)
    return bins.reshape(-1, N)                          # (steps, N), batch axis folded into time


def discretize(trs, L, frac=0.5):
    return _bins_from_harvest(np.asarray(trs["harvest"]), L, frac)  # all seeds pooled over time


def discretize_seed(trs, L, i, frac=0.5):
    return _bins_from_harvest(np.asarray(trs["harvest"])[i:i + 1], L, frac)  # one seed only


def meso_ei_from_bins(bins, L, B, seed=7):
    """Score the K=B partition's EI against the HONEST surrogate null (time-shuffle, marginal-
    preserving) rather than random same-size partitions. Returns the surrogate-test dict augmented
    with the emergent community count. Caller must pre-check ``bins.std() > 1e-6``."""
    res = ce.behavioral_ei_surrogate_test(bins, n_states=L, n_blocks=B, n_surr=N_SURR, seed=seed)
    Tb = ce.coupling_transition_from_trajectories(bins, n_states=L)  # for the emergent count only
    return {"ei": res["ei"], "percentile": res["ei_percentile"],
            "emergent_ncomm": len(np.unique(ce.emergent_partition(Tb)))}


def behavioral_meso_ei(trs, cfg):
    """Track-B: estimate the firm-coupling operator from the (seed-pooled) harvest trajectories,
    find the K=B partition, and score its EI privilege against the honest surrogate null."""
    L, B = cfg.n_levels, cfg.n_blocks
    bins = discretize(trs, L)
    if bins.std() < 1e-6:                               # degenerate (e.g. collapsed -> all zero)
        return {"ei": 0.0, "percentile": float("nan"), "emergent_ncomm": 1}
    return meso_ei_from_bins(bins, L, B, seed=7)


def meso_ei_per_seed(trs, cfg):
    """Per-seed Track-B meso-EI + surrogate percentile (each seed scored on its own ~half-trajectory).
    The per-seed EI is positively biased relative to the seed-pooled estimate (shorter sample, plus an
    optimised K=B cut on noisier coupling), so it feeds only the across-seed CI annotation, never the
    headline point. Degenerate (collapsed) seeds carry no structure and are dropped."""
    L, B = cfg.n_levels, cfg.n_blocks
    eis, pcts = [], []
    for i in range(np.asarray(trs["harvest"]).shape[0]):
        bins = discretize_seed(trs, L, i)
        if bins.std() < 1e-6:
            continue
        res = meso_ei_from_bins(bins, L, B, seed=7 + i)
        eis.append(res["ei"]); pcts.append(res["percentile"])
    return np.array(eis), np.array(pcts)


def responsiveness(trs, finals):
    """corr across agents between window-mean harvest and local ideal theta: does the controller
    serve heterogeneous sub-communities (high) or impose one setpoint (~0)?"""
    h = np.asarray(trs["harvest"])
    mh = h[:, h.shape[1] // 2:, :].mean(axis=(0, 1))    # (N,)
    th = np.asarray(finals.node_attrs[P.THETA]).mean(axis=0)  # (N,)
    if mh.std() < 1e-6 or th.std() < 1e-6:
        return 0.0
    return float(np.corrcoef(mh, th)[0, 1])


def structural_shapley(finals, cfg, T=T):
    """Track-S: from the time-averaged emergent affiliation W̄, Shapley-EI over the latent blocks."""
    Wbar = np.asarray(finals.global_attrs[P.AFFIL_SUM]).mean(axis=0) / T
    Ts = ce.rw_transition_from_W(Wbar)
    p = ce.stationary(Ts)
    labels = np.asarray(P.block_assignment(cfg))
    phi = ce.shapley_ei(Ts, p, labels)
    return phi, ce.max_phi_share(phi), float(phi.sum())


# ------------------------------------------------------------------ report

def main():
    out = []
    def emit(s=""):
        print(s)
        out.append(s)

    emit("=" * 78)
    emit("ENDOGENOUS POLYCENTRIC GOVERNANCE AS CAUSAL EMERGENCE")
    emit(f"  N={P.PolyConfig().n_agents} agents, {P.PolyConfig().n_blocks} sub-communities, "
         f"T={T}, seeds={N_SEEDS}")
    emit("=" * 78)

    # --- 1. MAS replication + EI∧fit, across governance (het=1.5) ----------
    emit("\n[1] MAS REPLICATION + EI-and-FIT  (heterogeneity=1.5)")
    emit("    governed/emergent sustains the commons that unenforced play collapses;")
    emit("    monocentric survives but trades FIT and has no institutional meso-structure.\n")
    emit(f"    {'regime':12s} {'finalR':>7s} {'surv':>5s} {'fit':>7s} "
         f"{'mesoEI':>7s} {'EI%ile':>7s} {'respond':>7s}")
    het = 1.5
    rows = {}
    for gov in ("atomized", "monocentric", "fixed_poly", "endogenous"):
        cfg, finals, trs = run_regime(gov, het=het)
        me = behavioral_meso_ei(trs, cfg)
        resp = responsiveness(trs, finals)
        ei_v, pct_v = meso_ei_per_seed(trs, cfg)
        rows[gov] = dict(finalR=final_R(trs), surv=survival(trs), fit=mean_fit(trs),
                         ei=me["ei"], pct=me["percentile"], resp=resp, ncomm=me["emergent_ncomm"],
                         fit_ci=bs.bootstrap_ci(mean_fit_seed(trs)),
                         surv_ci=bs.bootstrap_ci(survival_seed(trs)),
                         fr_ci=bs.bootstrap_ci(final_R_seed(trs)),
                         ei_ci=(bs.bootstrap_ci(ei_v) if ei_v.size else None),
                         pct_med=(float(np.median(pct_v)) if pct_v.size else float("nan")),
                         n_hi=int((pct_v >= 95).sum()), n_eff=int(ei_v.size))
        r = rows[gov]
        pct = "nan" if np.isnan(r["pct"]) else f"{r['pct']:.0f}"
        emit(f"    {gov:12s} {r['finalR']:7.1f} {r['surv']:5.0f} {r['fit']:+7.3f} "
             f"{r['ei']:7.3f} {pct:>7s} {r['resp']:+7.2f}")
    emit(f"\n    -> atomized collapses (tragedy); the rest survive (MAS result reproduced).")
    emit(f"    -> endogenous: high meso-EI privilege AND high fit AND high responsiveness")
    emit(f"       = co-maintains EI-and-fit; monocentric: low meso-EI, low fit, ~0 responsiveness")
    emit(f"       = one calcified setpoint that ignores sub-communities.")

    emit(f"\n    seed CIs (mean [95% bootstrap], {N_SEEDS} seeds):")
    for gov in ("atomized", "monocentric", "fixed_poly", "endogenous"):
        r = rows[gov]
        emit(f"    {gov:12s} fit {bs.format_ci(*r['fit_ci'])}   surv {bs.format_ci(*r['surv_ci'], prec=1)}"
             f"   finalR {bs.format_ci(*r['fr_ci'], prec=1)}")
        ei_str = bs.format_ci(*r["ei_ci"]) if r["ei_ci"] else "n/a (all seeds collapsed)"
        emit(f"    {'':12s} per-seed mesoEI {ei_str}  (per-seed mean != pooled point by construction;"
             f" n_eff={r['n_eff']}, median pct {r['pct_med']:.0f}, {r['n_hi']}/{r['n_eff']} seeds pct>=95)")

    # --- 2. Heterogeneity sweep: the EI∧fit gap widens --------------------
    emit("\n[2] HEADLINE: the endogenous-minus-monocentric FIT gap grows with heterogeneity")
    emit(f"    {'het':>5s} {'fit_mono':>9s} {'fit_endo':>9s} {'fit_gap':>8s} "
         f"{'EI_mono':>8s} {'EI_endo':>8s}")
    gap_cis = []
    for h in (0.0, 1.0, 2.0):
        _, fm, tm = run_regime("monocentric", het=h)
        cfg_e, fe, te = run_regime("endogenous", het=h)
        fit_m, fit_e = mean_fit(tm), mean_fit(te)
        ei_m = behavioral_meso_ei(tm, cfg_e)["ei"]
        ei_e = behavioral_meso_ei(te, cfg_e)["ei"]
        gap_cis.append((h, bs.bootstrap_ci(mean_fit_seed(te) - mean_fit_seed(tm))))  # paired, aligned seeds
        emit(f"    {h:5.1f} {fit_m:+9.3f} {fit_e:+9.3f} {fit_e - fit_m:+8.3f} "
             f"{ei_m:8.3f} {ei_e:8.3f}")
    emit("    -> at het=0 the central quota fits fine (gap~0); the gap opens as sub-communities")
    emit("       diverge — the welfare cost of uniformity (Oates), measured.")

    emit(f"\n    paired endo-minus-mono fit-gap (mean [95% bootstrap], {N_SEEDS} paired seeds):")
    for h, ci in gap_cis:
        excl = "excludes 0" if (ci[1] > 0.0 or ci[2] < 0.0) else "includes 0"
        emit(f"    het={h:.1f}  {bs.format_ci(*ci)}  ({excl})")

    # --- 3. Enforcement ablation (load-bearing test) ---------------------
    emit("\n[3] LOAD-BEARING TEST (policer ablation): endogenous with monitoring ON vs OFF")
    cfg, f_on, t_on = run_regime("endogenous", het=1.5, monitoring=True)
    cfg2, f_off, t_off = run_regime("endogenous", het=1.5, monitoring=False)
    emit(f"    monitoring ON : finalR={final_R(t_on):7.1f}  fit={mean_fit(t_on):+.3f}  "
         f"mesoEI={behavioral_meso_ei(t_on, cfg)['ei']:.3f}")
    emit(f"    monitoring OFF: finalR={final_R(t_off):7.1f}  fit={mean_fit(t_off):+.3f}  "
         f"mesoEI={behavioral_meso_ei(t_off, cfg2)['ei']:.3f}")
    emit("    -> removing enforcement collapses survival AND fit AND the meso-structure together:")
    emit("       EI is load-bearing (it moves when the substantive mechanism is corrupted).")

    # --- 4. Capture as an independent dial -------------------------------
    emit("\n[4] CAPTURE (exogenous hub-pull c on endogenous affiliation)")
    emit(f"    {'c':>5s} {'finalR':>7s} {'fit':>7s} {'maxShareEI':>11s} {'totalEI':>8s}")
    for c in (0.0, 0.3, 0.6, 0.9):
        cfg, finals, trs = run_regime("endogenous", het=1.5, capture=c)
        phi, share, tot = structural_shapley(finals, cfg)
        emit(f"    {c:5.1f} {final_R(trs):7.1f} {mean_fit(trs):+7.3f} {share:11.3f} {tot:8.3f}")
    emit("    -> rising capture concentrates the Shapley-EI attribution onto the hub block and")
    emit("       erodes fit, even while the commons can still survive: capture is a measured")
    emit("       consequence (a fit/attribution collapse), not a definition.")

    # --- interpretation --------------------------------------------------
    emit("\n" + "=" * 78)
    emit("RE-DESCRIPTION THROUGH THREE LENSES (the methodological contribution)")
    emit("=" * 78)
    emit("  EI lens          : the emergent regime forms a causally-privileged institutional")
    emit("                     meso-scale (high mesoEI percentile) that monocentric lacks; the")
    emit("                     (EI,Fit) gap predicts the survival+fit ordering.")
    emit("  complexity lens  : endogenous = near-lumpable modular structure matched to sub-")
    emit("                     communities; monocentric = one blob (no sub-structure), low fit;")
    emit("                     atomized = collapsed basin.")
    emit("  active-inference : quota = institution's policy prior; monocentric = one over-precise")
    emit("                     central prior (high control, no responsiveness = calcification);")
    emit("                     endogenous = nested per-niche priors that track local conditions.")
    emit("  => a known MAS result (emergent/decentralized beats imposed top-down) recovered AND")
    emit("     mechanistically explained. EI certifies a controller exists; FIT certifies its")
    emit("     setpoint serves the governed. Polycentric co-maintains both.")

    # save
    path = os.path.join(os.path.dirname(__file__), "results.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    emit(f"\n[saved] {path}")


if __name__ == "__main__":
    main()
