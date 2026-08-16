#!/usr/bin/env python3
"""Phase 1 power/reliability check: many independent replications at a
REAL, achievable cohort size (12-16 animals/group, matching your actual
behavioral cohorts) rather than one inflated simulated cohort.

Rationale: bumping the simulated cohort past what you could ever actually
collect (e.g. 40+/group) would answer "could this reach significance with
unlimited power" -- a different and less honest question than "is this
effect plausible/detectable at the sample sizes you actually work with."
Instead, this script re-runs the Phase 1 comparison many times, each with
an independent random draw, at n_animals_per_group=16 (the top of your
stated 12-16 range), and reports:

  - the distribution of Cohen's d and p-values across replications
  - the fraction of replications where young > old kappa (direction)
  - the fraction reaching nominal significance (p<0.05) on their own
  - a Fisher's-method combined one-sided p-value across all replications
    (a legitimate meta-analytic combination of independent evidence, not
    the same thing as inflating any single simulated cohort)

Usage: python scripts/run_phase1_replications.py [--n-replications N] [--quick]
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.params import NetworkParams, TaskParams, scaled_params
from sst_pv_model.simulate import simulate_group
from sst_pv_model.qlearning_fit import fit_session_level

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def animal_level(fit_df):
    return fit_df.groupby("Mouse ID")["kappa"].mean()


def one_sided_p_young_gt_old(ay, ao):
    """One-sided p-value for the directional hypothesis young > old,
    derived from the two-sided t-test (sign of t determines which tail)."""
    t, p_two = stats.ttest_ind(ay, ao)
    if t > 0:
        return p_two / 2.0
    else:
        return 1.0 - p_two / 2.0


def run_one_replication(rep_idx, task, base_net, n_starts, n_animals):
    young_params = scaled_params("young", base_net)
    old_params = scaled_params("old", base_net)

    seed_y = 1000 + 2 * rep_idx
    seed_o = 1001 + 2 * rep_idx
    df_y = simulate_group(young_params, task, n_animals=n_animals, seed=seed_y, age_label="young")
    df_o = simulate_group(old_params, task, n_animals=n_animals, seed=seed_o, age_label="old")

    fit_y = fit_session_level(df_y, n_starts=n_starts)
    fit_o = fit_session_level(df_o, n_starts=n_starts)

    def session_number(session_id):
        return int(session_id.rsplit("_s", 1)[1])

    fit_y = fit_y.assign(sess_num=fit_y["Session ID"].map(session_number))
    fit_o = fit_o.assign(sess_num=fit_o["Session ID"].map(session_number))
    half = task.n_sessions // 2

    def summarize(fy, fo, window):
        ay = animal_level(fy).values
        ao = animal_level(fo).values
        t, p_two = stats.ttest_ind(ay, ao)
        p_one = one_sided_p_young_gt_old(ay, ao)
        pooled_sd = np.sqrt((ay.var(ddof=1) + ao.var(ddof=1)) / 2)
        d = (ay.mean() - ao.mean()) / pooled_sd if pooled_sd > 0 else np.nan
        return dict(
            replication=rep_idx, window=window,
            young_mean=ay.mean(), old_mean=ao.mean(), diff=ay.mean() - ao.mean(),
            cohend=d, p_two_sided=p_two, p_one_sided=p_one,
        )

    rows = [summarize(fit_y, fit_o, "all")]
    rows.append(summarize(fit_y[fit_y.sess_num < half], fit_o[fit_o.sess_num < half], "early"))
    rows.append(summarize(fit_y[fit_y.sess_num >= half], fit_o[fit_o.sess_num >= half], "late"))
    return rows


def fisher_combined_p(p_values):
    """Fisher's method: combine independent one-sided p-values into a
    single chi-square statistic / combined p-value."""
    p_values = np.clip(np.asarray(p_values, dtype=float), 1e-300, 1.0)
    stat = -2.0 * np.sum(np.log(p_values))
    df = 2 * len(p_values)
    return stats.chi2.sf(stat, df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-replications", type=int, default=15)
    ap.add_argument("--n-animals", type=int, default=16, help="matches the top of your real 12-16/group range")
    ap.add_argument("--n-starts", type=int, default=8)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    base_net = NetworkParams()
    if args.quick:
        task = TaskParams(n_sessions=3, n_trials_per_session=80)
        n_reps = min(args.n_replications, 3)
        n_starts = 5
    else:
        task = TaskParams()
        n_reps = args.n_replications
        n_starts = args.n_starts

    print(f"Running {n_reps} independent replications, n_animals={args.n_animals}/group, "
          f"{task.n_sessions} sessions x {task.n_trials_per_session} trials, n_starts={n_starts}")
    print("(each replication is an independent simulated cohort at your REAL achievable "
          "sample size, not one inflated cohort -- see script docstring)")

    all_rows = []
    t_start = time.time()
    for rep in range(n_reps):
        t0 = time.time()
        rows = run_one_replication(rep, task, base_net, n_starts, args.n_animals)
        all_rows.extend(rows)
        elapsed = time.time() - t0
        all_row = [r for r in rows if r["window"] == "all"][0]
        print(f"  replication {rep+1}/{n_reps} ({elapsed:.0f}s): "
              f"all-sessions diff={all_row['diff']:+.3f} d={all_row['cohend']:+.3f} "
              f"p_one_sided={all_row['p_one_sided']:.3f}", flush=True)

    print(f"\nTotal time: {time.time()-t_start:.0f}s")

    df = pd.DataFrame(all_rows)
    df.to_csv(OUT_DIR / "phase1_replications_raw.csv", index=False)

    summary_lines = []
    summary_lines.append(f"Phase 1 replication study: {n_reps} independent cohorts, "
                          f"n_animals={args.n_animals}/group (matches your real 12-16/group range)\n")
    for window in ["all", "early", "late"]:
        sub = df[df.window == window]
        frac_direction = (sub["diff"] > 0).mean()
        frac_sig_one_sided = (sub["p_one_sided"] < 0.05).mean()
        combined_p = fisher_combined_p(sub["p_one_sided"].values)
        summary_lines.append(
            f"--- {window} sessions ---\n"
            f"  mean Cohen's d: {sub['cohend'].mean():+.3f} (median {sub['cohend'].median():+.3f}, "
            f"range [{sub['cohend'].min():+.3f}, {sub['cohend'].max():+.3f}])\n"
            f"  fraction of replications with young>old direction: {frac_direction:.2f} ({int(frac_direction*n_reps)}/{n_reps})\n"
            f"  fraction reaching one-sided p<0.05 individually: {frac_sig_one_sided:.2f} ({int(frac_sig_one_sided*n_reps)}/{n_reps})\n"
            f"  Fisher's-method combined one-sided p-value across all {n_reps} replications: {combined_p:.2e}\n"
        )
    summary = "\n".join(summary_lines)
    print("\n" + "=" * 78)
    print(summary)
    (OUT_DIR / "phase1_replications_summary.txt").write_text(summary)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(9, 4))
        for ax, window in zip(axes, ["all", "late"]):
            sub = df[df.window == window]
            ax.hist(sub["cohend"], bins=max(5, n_reps // 3), color="#4c72b0", alpha=0.8)
            ax.axvline(0, color="gray", ls="--", lw=1)
            ax.axvline(sub["cohend"].mean(), color="black", lw=1.5)
            ax.set_title(f"{window} sessions")
            ax.set_xlabel("Cohen's d (young - old kappa)")
        axes[0].set_ylabel("replications")
        fig.suptitle(f"Phase 1: Cohen's d across {n_reps} independent {args.n_animals}/group replications")
        fig.tight_layout()
        fig.savefig(OUT_DIR / "phase1_replications_cohend_hist.png", dpi=150)
        print(f"Saved plot: {OUT_DIR / 'phase1_replications_cohend_hist.png'}")
    except Exception as e:
        print(f"Plotting failed (non-fatal): {e}")


if __name__ == "__main__":
    main()
