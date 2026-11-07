#!/usr/bin/env python3
"""Phase 1 extension: finer sweep of the "total inhibition" multiplier,
around each age's OWN baseline, for the two manipulations that reached
significance at full scale (scripts/run_manipulations.py,
outputs/phase1_manipulations.csv):

  young: higher_total_inhibition (x1.5) significantly INCREASED kappa
  old:   lower_total_inhibition  (x0.5) significantly INCREASED kappa

Those two results were each measured at a single multiplier point (0.5 or
1.5x baseline gain). This script asks: is each age's own baseline sitting
at a local minimum of perseveration, with kappa rising smoothly in BOTH
directions away from it (a true U-shape), or is there a sharper
threshold/transition in the direction that was significant?

Uses sst_pv_model.manipulations.scale_total_inhibition(p, multiplier) to
scale g_pv, g_sst, AND g_sst_to_pv together by an arbitrary multiplier
(generalizing the two fixed x0.5/x1.5 points already tested), and compares
each swept point against that SAME age's own multiplier=1.0 baseline.

Deliberately run at the project's REDUCED/sensitivity-sweep scale (see
sst_pv_model/sensitivity.py: n_animals=8, 3 sessions x 100 trials, 8
restarts/fit) rather than full scale -- this is a shape-mapping /
direction-checking sweep across many points, not a single confirmatory
comparison, so the established convention is to trade precision at any one
point for coverage across many.

Usage: python scripts/run_total_inhibition_sweep.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.params import TaskParams, scaled_params
from sst_pv_model.manipulations import scale_total_inhibition
from sst_pv_model.simulate import simulate_group
from sst_pv_model.qlearning_fit import fit_session_level

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"

N_ANIMALS = 8
N_STARTS = 8
TASK = TaskParams(n_sessions=3, n_trials_per_session=100, n_animals_per_group=N_ANIMALS)

# Centered on 1.0 (=own baseline), denser near 1.0, spanning further in the
# direction that was significant for each age (old: down to 0.2x; young: up
# to 2.2x) but covering both directions for both ages so a U-shape vs.
# threshold can actually be distinguished either way.
MULTIPLIERS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 2.0, 2.2]


def animal_level(fit_df):
    return fit_df.groupby("Mouse ID")["kappa"].mean()


def run_one(params, seed, label):
    df = simulate_group(params, TASK, n_animals=N_ANIMALS, seed=seed, age_label=label)
    return fit_session_level(df, n_starts=N_STARTS)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    print(f"Task structure (reduced/sensitivity scale): {TASK.n_sessions} sessions x "
          f"{TASK.n_trials_per_session} trials, {N_ANIMALS} animals/group, {N_STARTS} restarts/fit")
    print(f"Multipliers: {MULTIPLIERS}")

    rows = []
    seed = 500
    for age in ["young", "old"]:
        base = scaled_params(age)
        baseline_fit = run_one(base, seed, f"{age}_m1.00")
        seed += 1
        a_base = animal_level(baseline_fit).values
        print(f"\n=== {age} baseline (g_pv={base.g_pv:.2f}, g_sst={base.g_sst:.2f}, "
              f"g_sst_to_pv={base.g_sst_to_pv:.2f}) : kappa={a_base.mean():+.3f} ===")

        for m in MULTIPLIERS:
            params_m = scale_total_inhibition(base, m)
            if m == 1.0:
                a_m = a_base
            else:
                fit_m = run_one(params_m, seed, f"{age}_m{m:.2f}")
                seed += 1
                a_m = animal_level(fit_m).values

            if m == 1.0:
                t, p, cohend = np.nan, np.nan, 0.0
            else:
                t, p = stats.ttest_ind(a_base, a_m)
                pooled_sd = np.sqrt((a_base.var(ddof=1) + a_m.var(ddof=1)) / 2)
                cohend = (a_m.mean() - a_base.mean()) / pooled_sd if pooled_sd > 0 else np.nan

            row = dict(
                age=age, multiplier=m,
                kappa_mean=a_m.mean(), kappa_sd=a_m.std(),
                diff_vs_baseline=a_m.mean() - a_base.mean(),
                cohend_vs_baseline=cohend, p_ttest=p,
                g_pv=params_m.g_pv, g_sst=params_m.g_sst, g_sst_to_pv=params_m.g_sst_to_pv,
                n=len(a_m),
            )
            rows.append(row)
            print(f"  {age:5s} / x{m:.2f}  kappa: {a_m.mean():+.3f} (vs baseline diff={row['diff_vs_baseline']:+.3f}, "
                  f"d={cohend:+.3f}" + (f", p={p:.4f}" if not np.isnan(p) else ", p=n/a (self)") + ")")

    result = pd.DataFrame(rows)
    out_path = OUT_DIR / "phase1_total_inhibition_sweep.csv"
    result.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 4.5))
        for age, color in [("young", "tab:blue"), ("old", "tab:orange")]:
            sub = result[result.age == age].sort_values("multiplier")
            ax.plot(sub.multiplier, sub.kappa_mean, "o-", color=color, label=age)
            ax.fill_between(sub.multiplier, sub.kappa_mean - sub.kappa_sd / np.sqrt(N_ANIMALS),
                             sub.kappa_mean + sub.kappa_sd / np.sqrt(N_ANIMALS), color=color, alpha=0.15)
        ax.axvline(1.0, color="gray", lw=0.5, ls="--")
        ax.set_xlabel("total-inhibition multiplier (relative to own-age baseline)")
        ax.set_ylabel("fitted kappa (animal mean +/- SEM)")
        ax.set_title("Finer sweep: total inhibition vs. perseveration, by age")
        ax.legend()
        fig.tight_layout()
        fig.savefig(OUT_DIR / "phase1_total_inhibition_sweep.png", dpi=150)
        print(f"Saved plot: {OUT_DIR / 'phase1_total_inhibition_sweep.png'}")
    except Exception as e:
        print(f"Plotting failed (non-fatal): {e}")

    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
