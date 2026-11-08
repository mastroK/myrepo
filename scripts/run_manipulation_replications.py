#!/usr/bin/env python3
"""Full-scale confirmatory REPLICATION of a single inhibition-manipulation
scenario, for the two scenarios that reached significance in the one-cohort
full-scale run (scripts/run_manipulations.py, outputs/phase1_manipulations.csv):

  young / higher_total_inhibition (x1.5): diff=+0.558, d=+2.07, p<0.0001
  old   / lower_total_inhibition  (x0.5): diff=+0.252, d=+1.20, p=0.002

Mirrors scripts/run_phase1_replications.py's established convention exactly
(same task scale -- TaskParams() defaults: 10 sessions x 150 trials,
n_animals_per_group=16 -- and the same reduced n_starts=8 restarts-per-fit
tradeoff that makes running many independent full-scale cohorts tractable),
but compares a manipulated cohort against that SAME age's own unmanipulated
baseline (both freshly drawn per replication, matching the single-cohort
comparison's logic) instead of young vs. old.

Adds the inverse-variance-weighted pooling + Hedges' approximate SE used
for the headline young-vs-old forest plot (reports/phase1_report.html),
so this single-scenario replication study can be summarized the same way:
a per-replication Cohen's d with an approximate 95% CI, plus one pooled
estimate across all replications.

Usage: python scripts/run_manipulation_replications.py --age young --manipulation higher_total_inhibition
       python scripts/run_manipulation_replications.py --age old --manipulation lower_total_inhibition
       (add --quick for a fast smoke test; --n-replications/--n-starts to override)
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.params import TaskParams, scaled_params
from sst_pv_model.manipulations import apply_manipulation
from sst_pv_model.simulate import simulate_group
from sst_pv_model.qlearning_fit import fit_session_level

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def animal_level(fit_df):
    return fit_df.groupby("Mouse ID")["kappa"].mean()


def one_sided_p_manip_gt_baseline(a_base, a_manip):
    """One-sided p-value for the directional hypothesis manip > baseline
    (the direction already found significant at single-cohort full scale
    for both scenarios this script replicates), from the two-sided t-test."""
    t, p_two = stats.ttest_ind(a_manip, a_base)
    if t > 0:
        return p_two / 2.0
    else:
        return 1.0 - p_two / 2.0


def hedges_se(d, n1, n2):
    """Approximate SE of Cohen's d (Hedges & Olkin 1985), used for the
    per-replication CI and as the inverse-variance weight when pooling."""
    return np.sqrt((n1 + n2) / (n1 * n2) + d ** 2 / (2 * (n1 + n2 - 2)))


def fisher_combined_p(p_values):
    p_values = np.clip(np.asarray(p_values, dtype=float), 1e-300, 1.0)
    stat = -2.0 * np.sum(np.log(p_values))
    df = 2 * len(p_values)
    return stats.chi2.sf(stat, df)


def run_one_replication(rep_idx, age, manipulation, task, n_starts, n_animals):
    baseline_params = scaled_params(age)
    manip_params = apply_manipulation(baseline_params, manipulation)

    seed_base = 3000 + 2 * rep_idx
    seed_manip = 3001 + 2 * rep_idx
    df_base = simulate_group(baseline_params, task, n_animals=n_animals, seed=seed_base, age_label=f"{age}_baseline")
    df_manip = simulate_group(manip_params, task, n_animals=n_animals, seed=seed_manip, age_label=f"{age}_{manipulation}")

    fit_base = fit_session_level(df_base, n_starts=n_starts)
    fit_manip = fit_session_level(df_manip, n_starts=n_starts)

    a_base = animal_level(fit_base).values
    a_manip = animal_level(fit_manip).values

    t, p_two = stats.ttest_ind(a_manip, a_base)
    p_one = one_sided_p_manip_gt_baseline(a_base, a_manip)
    pooled_sd = np.sqrt((a_base.var(ddof=1) + a_manip.var(ddof=1)) / 2)
    d = (a_manip.mean() - a_base.mean()) / pooled_sd if pooled_sd > 0 else np.nan
    se_d = hedges_se(d, len(a_base), len(a_manip))

    return dict(
        replication=rep_idx, age=age, manipulation=manipulation,
        kappa_baseline=a_base.mean(), kappa_manip=a_manip.mean(),
        diff=a_manip.mean() - a_base.mean(), cohend=d, se_d=se_d,
        p_two_sided=p_two, p_one_sided=p_one,
        n_baseline=len(a_base), n_manip=len(a_manip),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--age", choices=["young", "old"], required=True)
    ap.add_argument("--manipulation", required=True)
    ap.add_argument("--n-replications", type=int, default=15)
    ap.add_argument("--n-animals", type=int, default=16)
    ap.add_argument("--n-starts", type=int, default=8)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    if args.quick:
        task = TaskParams(n_sessions=3, n_trials_per_session=80)
        n_reps = min(args.n_replications, 3)
        n_starts = 5
    else:
        task = TaskParams()
        n_reps = args.n_replications
        n_starts = args.n_starts

    print(f"Replicating {args.age}/{args.manipulation}: {n_reps} independent full-scale cohorts, "
          f"n_animals={args.n_animals}/group, {task.n_sessions} sessions x {task.n_trials_per_session} "
          f"trials, n_starts={n_starts}{' (QUICK)' if args.quick else ''}")

    rows = []
    t_start = time.time()
    for rep in range(n_reps):
        t0 = time.time()
        row = run_one_replication(rep, args.age, args.manipulation, task, n_starts, args.n_animals)
        rows.append(row)
        print(f"  replication {rep+1}/{n_reps} ({time.time()-t0:.0f}s): "
              f"diff={row['diff']:+.3f} d={row['cohend']:+.3f} (SE={row['se_d']:.3f}) "
              f"p_one_sided={row['p_one_sided']:.4f}", flush=True)
    print(f"Total time: {time.time()-t_start:.0f}s")

    df = pd.DataFrame(rows)
    tag = f"{args.age}_{args.manipulation}"
    raw_path = OUT_DIR / f"phase1_manip_replications_{tag}_raw.csv"
    df.to_csv(raw_path, index=False)
    print(f"Saved {raw_path}")

    frac_direction = (df["diff"] > 0).mean()
    frac_sig = (df["p_one_sided"] < 0.05).mean()
    combined_p = fisher_combined_p(df["p_one_sided"].values)

    weights = 1.0 / df["se_d"].values ** 2
    pooled_d = np.sum(weights * df["cohend"].values) / np.sum(weights)
    pooled_se = np.sqrt(1.0 / np.sum(weights))
    ci_lo, ci_hi = pooled_d - 1.96 * pooled_se, pooled_d + 1.96 * pooled_se

    summary = (
        f"Manipulation replication study: {args.age} / {args.manipulation}\n"
        f"{n_reps} independent full-scale cohorts, n_animals={args.n_animals}/group, "
        f"{task.n_sessions} sessions x {task.n_trials_per_session} trials, n_starts={n_starts}\n\n"
        f"mean Cohen's d: {df['cohend'].mean():+.3f} (median {df['cohend'].median():+.3f}, "
        f"range [{df['cohend'].min():+.3f}, {df['cohend'].max():+.3f}])\n"
        f"fraction of replications with manip>baseline direction: {frac_direction:.2f} ({int(frac_direction*n_reps)}/{n_reps})\n"
        f"fraction reaching one-sided p<0.05 individually: {frac_sig:.2f} ({int(frac_sig*n_reps)}/{n_reps})\n"
        f"Fisher's-method combined one-sided p-value across all {n_reps} replications: {combined_p:.2e}\n"
        f"Pooled inverse-variance-weighted estimate: d = {pooled_d:.3f}, 95% CI [{ci_lo:.3f}, {ci_hi:.3f}]\n"
    )
    print("\n" + "=" * 78)
    print(summary)
    summary_path = OUT_DIR / f"phase1_manip_replications_{tag}_summary.txt"
    summary_path.write_text(summary)
    print(f"Saved {summary_path}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 0.4 * n_reps + 2))
        ys = np.arange(n_reps, 0, -1)
        colors = ["#4c72b0" if p < 0.05 else "#999999" for p in df["p_one_sided"]]
        ax.errorbar(df["cohend"], ys, xerr=1.96 * df["se_d"], fmt="o", color="black",
                    ecolor="gray", capsize=3, markerfacecolor="none")
        for y, d, c in zip(ys, df["cohend"], colors):
            ax.plot(d, y, "o", color=c, zorder=3)
        ax.axvline(0, color="gray", lw=0.8, ls="--")
        ax.axvline(pooled_d, color="#c44e52", lw=1.2)
        ax.plot(pooled_d, 0, "D", color="#c44e52", markersize=10)
        ax.set_yticks(list(ys) + [0])
        ax.set_yticklabels([f"rep {i+1}" for i in range(n_reps)] + ["Pooled"])
        ax.set_xlabel("Cohen's d (manip - baseline)")
        ax.set_title(f"{args.age} / {args.manipulation}: {n_reps} replications")
        fig.tight_layout()
        fig_path = OUT_DIR / f"phase1_manip_replications_{tag}_forest.png"
        fig.savefig(fig_path, dpi=150)
        print(f"Saved plot: {fig_path}")
    except Exception as e:
        print(f"Plotting failed (non-fatal): {e}")


if __name__ == "__main__":
    main()
