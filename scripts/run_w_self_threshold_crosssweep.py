#!/usr/bin/env python3
"""Phase 1 extension: is the sharp high-total-inhibition threshold found by
scripts/run_total_inhibition_sweep.py (kappa explodes upward above roughly
x1.4-1.5 of baseline gain, in BOTH ages) a genuine prediction about this
circuit's inhibitory tone, or an artifact of w_self -- the recurrent
self-excitation strength, which is an ASSUMED (not empirically-anchored)
free parameter already flagged for robustness sweeping in
sst_pv_model/sensitivity.py?

Logic: re-run the total-inhibition multiplier sweep (focused on the
transition zone, x0.5-x2.3) at SEVERAL w_self values -- the same four
points sensitivity.py already sweeps (1.2, 1.5, 2.0, 2.5) -- for both ages.
If the threshold's location/sharpness tracks w_self (lower w_self pushes
it out or removes it; higher w_self brings it in sooner/sharper), that is
strong evidence the explosive regime is a runaway winner-take-all artifact
of this free parameter, not a feature specifically tied to the SST/PV
inhibition fold-changes themselves. If the threshold stays put regardless
of w_self, that argues it's a more robust feature of the inhibition axis.

Baseline for Cohen's d at each (w_self, age) combo is multiplier=1.0 AT
THAT w_self (not the global default), so this isolates "does raising total
inhibition from this w_self's own baseline eventually blow up" separately
for each w_self.

Reduced/sensitivity scale throughout (n_animals=8, 3 sessions x 100
trials, 8 fit restarts), matching run_total_inhibition_sweep.py and
sst_pv_model/sensitivity.py's existing convention -- this is a shape/
threshold-location mapping exercise across many points, not a single
confirmatory comparison.

Usage: python scripts/run_w_self_threshold_crosssweep.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.params import NetworkParams, TaskParams, scaled_params
from sst_pv_model.manipulations import scale_total_inhibition
from sst_pv_model.simulate import simulate_group
from sst_pv_model.qlearning_fit import fit_session_level

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"

N_ANIMALS = 8
N_STARTS = 8
TASK = TaskParams(n_sessions=3, n_trials_per_session=100, n_animals_per_group=N_ANIMALS)

# Same four w_self values already swept in sst_pv_model/sensitivity.py, for
# direct comparability with that existing robustness result.
W_SELF_VALUES = [1.2, 1.5, 2.0, 2.5]

# Focused on the transition zone identified by run_total_inhibition_sweep.py
# (flat below ~x1.4, explosive above ~x1.5) rather than the full x0.2-x2.2
# range -- x0.5 kept as a single below-baseline reference point.
MULTIPLIERS = [0.5, 1.0, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3]


def animal_level(fit_df):
    return fit_df.groupby("Mouse ID")["kappa"].mean()


def run_one(params, seed, label):
    df = simulate_group(params, TASK, n_animals=N_ANIMALS, seed=seed, age_label=label)
    return fit_session_level(df, n_starts=N_STARTS)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    print(f"Task structure (reduced/sensitivity scale): {TASK.n_sessions} sessions x "
          f"{TASK.n_trials_per_session} trials, {N_ANIMALS} animals/group, {N_STARTS} restarts/fit")
    print(f"w_self values: {W_SELF_VALUES}")
    print(f"Multipliers: {MULTIPLIERS}")

    rows = []
    seed = 2000
    for w_self in W_SELF_VALUES:
        base_net = NetworkParams(w_self=w_self)
        for age in ["young", "old"]:
            base = scaled_params(age, base_net)
            baseline_fit = run_one(base, seed, f"w{w_self}_{age}_m1.00")
            seed += 1
            a_base = animal_level(baseline_fit).values
            print(f"\n=== w_self={w_self} {age} baseline (g_pv={base.g_pv:.2f}, g_sst={base.g_sst:.2f}, "
                  f"g_sst_to_pv={base.g_sst_to_pv:.2f}) : kappa={a_base.mean():+.3f} ===")

            for m in MULTIPLIERS:
                params_m = scale_total_inhibition(base, m)
                if m == 1.0:
                    a_m = a_base
                else:
                    fit_m = run_one(params_m, seed, f"w{w_self}_{age}_m{m:.2f}")
                    seed += 1
                    a_m = animal_level(fit_m).values

                if m == 1.0:
                    p, cohend = np.nan, 0.0
                else:
                    t, p = stats.ttest_ind(a_base, a_m)
                    pooled_sd = np.sqrt((a_base.var(ddof=1) + a_m.var(ddof=1)) / 2)
                    cohend = (a_m.mean() - a_base.mean()) / pooled_sd if pooled_sd > 0 else np.nan

                row = dict(
                    w_self=w_self, age=age, multiplier=m,
                    kappa_mean=a_m.mean(), kappa_sd=a_m.std(),
                    diff_vs_baseline=a_m.mean() - a_base.mean(),
                    cohend_vs_baseline=cohend, p_ttest=p,
                    g_pv=params_m.g_pv, g_sst=params_m.g_sst, g_sst_to_pv=params_m.g_sst_to_pv,
                    n=len(a_m),
                )
                rows.append(row)
                print(f"  w_self={w_self} {age:5s} / x{m:.2f}  kappa: {a_m.mean():+.3f} "
                      f"(diff={row['diff_vs_baseline']:+.3f}, d={cohend:+.3f}"
                      + (f", p={p:.4f}" if not np.isnan(p) else ", p=n/a (self)") + ")")

    result = pd.DataFrame(rows)
    out_path = OUT_DIR / "phase1_w_self_threshold_crosssweep.csv"
    result.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
        colors = {1.2: "tab:green", 1.5: "tab:blue", 2.0: "tab:orange", 2.5: "tab:red"}
        for ax, age in zip(axes, ["young", "old"]):
            for w_self in W_SELF_VALUES:
                sub = result[(result.age == age) & (result.w_self == w_self)].sort_values("multiplier")
                ax.plot(sub.multiplier, sub.kappa_mean, "o-", color=colors[w_self], label=f"w_self={w_self}")
            ax.axvline(1.0, color="gray", lw=0.5, ls="--")
            ax.set_xlabel("total-inhibition multiplier (relative to own baseline)")
            ax.set_title(age)
        axes[0].set_ylabel("fitted kappa (animal mean)")
        axes[0].legend()
        fig.suptitle("Does the high-inhibition threshold shift with w_self?")
        fig.tight_layout()
        fig.savefig(OUT_DIR / "phase1_w_self_threshold_crosssweep.png", dpi=150)
        print(f"Saved plot: {OUT_DIR / 'phase1_w_self_threshold_crosssweep.png'}")
    except Exception as e:
        print(f"Plotting failed (non-fatal): {e}")

    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
