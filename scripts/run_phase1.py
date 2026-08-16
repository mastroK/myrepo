#!/usr/bin/env python3
"""Phase 1: behavioral sufficiency test.

Simulates young (SST-high/PV-low) and old (SST-low/PV-high) competing-pools
networks performing the 80-20 bandit task, fits each simulated session with
the (vendored) sticky Q-learning model, and checks whether young shows
higher fitted kappa (perseveration) than old -- the direction reported in
the real behavioral data. Also runs a coarse one-at-a-time robustness sweep
over the model's free/unconstrained parameters.

Usage: python scripts/run_phase1.py [--quick]
  --quick uses a much smaller cohort/trial count for a fast smoke-test run.
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.params import (
    NetworkParams,
    TaskParams,
    scaled_params,
    print_assumption_report,
    SST_FOLD_CHANGE_OLD_OVER_YOUNG,
    PV_FOLD_CHANGE_OLD_OVER_YOUNG,
)
from sst_pv_model.simulate import simulate_group
from sst_pv_model.qlearning_fit import fit_session_level
from sst_pv_model.sensitivity import run_robustness_suite, summarize_robustness

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def animal_level(fit_df):
    return fit_df.groupby("Mouse ID")["kappa"].mean()


def compare_groups(fit_y, fit_o, label=""):
    ay = animal_level(fit_y).values
    ao = animal_level(fit_o).values
    t, p_t = stats.ttest_ind(ay, ao)
    u, p_u = stats.mannwhitneyu(ay, ao)
    pooled_sd = np.sqrt((ay.var(ddof=1) + ao.var(ddof=1)) / 2)
    cohend = (ay.mean() - ao.mean()) / pooled_sd if pooled_sd > 0 else np.nan
    print(f"\n--- {label} (n_young_animals={len(ay)}, n_old_animals={len(ao)}) ---")
    print(f"  young kappa (animal-mean): {ay.mean():.3f} +/- {ay.std():.3f}")
    print(f"  old   kappa (animal-mean): {ao.mean():.3f} +/- {ao.std():.3f}")
    print(f"  diff (young-old): {ay.mean()-ao.mean():+.3f}   Cohen's d: {cohend:+.3f}")
    print(f"  t-test p={p_t:.4f}   Mann-Whitney p={p_u:.4f}")
    return dict(label=label, young_mean=ay.mean(), old_mean=ao.mean(), diff=ay.mean() - ao.mean(),
                cohend=cohend, p_ttest=p_t, p_mwu=p_u, n_young=len(ay), n_old=len(ao))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fast smoke-test scale")
    ap.add_argument("--n-starts", type=int, default=None)
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    print_assumption_report()

    base_net = NetworkParams()
    if args.quick:
        task = TaskParams(n_sessions=3, n_trials_per_session=80, n_animals_per_group=6)
        n_starts = args.n_starts or 6
    else:
        task = TaskParams()
        n_starts = args.n_starts or 15

    print(f"\nTask structure: {task.n_sessions} sessions x {task.n_trials_per_session} trials, "
          f"{task.n_animals_per_group} animals/group (ASSUMED defaults, see report above)")
    print(f"SST fold-change old/young = {SST_FOLD_CHANGE_OLD_OVER_YOUNG} (PLACEHOLDER)")
    print(f"PV fold-change old/young  = {PV_FOLD_CHANGE_OLD_OVER_YOUNG} (PLACEHOLDER)")

    young_params = scaled_params("young", base_net)
    old_params = scaled_params("old", base_net)

    t0 = time.time()
    df_y = simulate_group(young_params, task, n_animals=task.n_animals_per_group, seed=1, age_label="young")
    df_o = simulate_group(old_params, task, n_animals=task.n_animals_per_group, seed=2, age_label="old")
    print(f"\nSimulated {len(df_y)+len(df_o)} trials in {time.time()-t0:.1f}s")
    print(f"Reward rate young/old: {df_y['Reward'].mean():.3f} / {df_o['Reward'].mean():.3f}")

    t0 = time.time()
    fit_y = fit_session_level(df_y, n_starts=n_starts)
    fit_o = fit_session_level(df_o, n_starts=n_starts)
    print(f"Fit {len(fit_y)+len(fit_o)} sessions in {time.time()-t0:.1f}s")
    print(f"beta_at_bound fraction young/old: {fit_y['beta_at_bound'].mean():.2f} / {fit_o['beta_at_bound'].mean():.2f}"
          " (real cohort's own diagnostic flags ~30% of sessions this way; kappa is not a clean continuous"
          " estimate at the boundary, per the real pipeline's own caveat)")

    fit_y.to_csv(OUT_DIR / "phase1_session_fits_young.csv", index=False)
    fit_o.to_csv(OUT_DIR / "phase1_session_fits_old.csv", index=False)

    results = []
    results.append(compare_groups(fit_y, fit_o, label="All sessions"))

    # Early (first half) vs late (second half) session split, mirroring the
    # real analysis where the kappa age-effect was specific to late sessions.
    def session_number(session_id):
        return int(session_id.rsplit("_s", 1)[1])

    fit_y = fit_y.assign(sess_num=fit_y["Session ID"].map(session_number))
    fit_o = fit_o.assign(sess_num=fit_o["Session ID"].map(session_number))
    half = task.n_sessions // 2
    results.append(compare_groups(fit_y[fit_y.sess_num < half], fit_o[fit_o.sess_num < half], label=f"Early sessions (0-{half-1})"))
    results.append(compare_groups(fit_y[fit_y.sess_num >= half], fit_o[fit_o.sess_num >= half], label=f"Late sessions ({half}-{task.n_sessions-1})"))

    summary_df = pd.DataFrame(results)
    summary_df.to_csv(OUT_DIR / "phase1_kappa_comparison.csv", index=False)

    # --- plot ---
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        ay = animal_level(fit_y)
        ao = animal_level(fit_o)
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.boxplot([ay.values, ao.values], tick_labels=["young", "old"])
        ax.scatter(np.full(len(ay), 1) + np.random.uniform(-0.05, 0.05, len(ay)), ay.values, alpha=0.5, s=15)
        ax.scatter(np.full(len(ao), 2) + np.random.uniform(-0.05, 0.05, len(ao)), ao.values, alpha=0.5, s=15)
        ax.axhline(0, color="gray", lw=0.5, ls="--")
        ax.set_ylabel("fitted kappa (animal mean)")
        ax.set_title("Phase 1: simulated perseveration by age")
        fig.tight_layout()
        fig.savefig(OUT_DIR / "phase1_kappa_by_age.png", dpi=150)
        print(f"\nSaved plot: {OUT_DIR / 'phase1_kappa_by_age.png'}")
    except Exception as e:
        print(f"Plotting failed (non-fatal): {e}")

    # --- robustness sweep ---
    print("\n" + "=" * 78)
    print("Robustness / sensitivity sweep (reduced trial count for speed)")
    print("=" * 78)
    sweeps = run_robustness_suite(n_animals=8 if not args.quick else 5)
    report = summarize_robustness(sweeps)
    print(report)
    (OUT_DIR / "phase1_robustness_report.txt").write_text(report)
    for name, df in sweeps.items():
        df.to_csv(OUT_DIR / f"phase1_sweep_{name}.csv", index=False)

    print("\nDone. See outputs/ for CSVs and plot.")


if __name__ == "__main__":
    main()
