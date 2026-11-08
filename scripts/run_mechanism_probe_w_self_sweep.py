#!/usr/bin/env python3
"""Phase 1 extension: rerun the isolated single-trial mechanism-asymmetry
probe across the same (w_self, age, multiplier) grid used by
scripts/run_w_self_threshold_crosssweep.py, to see whether the probe
tracks the behavioral high-total-inhibition threshold found there, or
continues to disagree with it the way it already disagreed once before
(see PHASE1_SUMMARY.md's "Mechanism check" section -- the probe's
isolated-trial asymmetry did not predict the real, noisy, learning-coupled
behavioral result once the confirmed SST->PV coupling values were added).

The probe (forced extreme win -> one stim epoch -> one ITI, no noise, no
learning, no cross-trial dynamics) is deterministic and essentially free
to compute, so this reruns it at every (w_self, age, multiplier) point
already behaviorally swept, and joins the result against that existing
behavioral CSV for direct comparison.

Usage: python scripts/run_mechanism_probe_w_self_sweep.py
  (requires outputs/phase1_w_self_threshold_crosssweep.csv to already
  exist, from scripts/run_w_self_threshold_crosssweep.py)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.params import NetworkParams, TaskParams, scaled_params
from sst_pv_model.manipulations import scale_total_inhibition
from sst_pv_model.network import NetworkState, run_epoch, output_rates

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"

W_SELF_VALUES = [1.2, 1.5, 2.0, 2.5]
MULTIPLIERS = [0.5, 1.0, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3]

TASK = TaskParams()


def mechanism_asymmetry(params, task):
    """Isolated single-trial probe (forced extreme win -> one ITI) --
    deterministic, no noise, no learning. Flagged unreliable as a
    standalone predictor of the real behavioral result -- see
    PHASE1_SUMMARY.md's 'Mechanism check' section."""
    state = NetworkState(1)
    stim = lambda i: np.array([[0.0, 3.0]])
    run_epoch(state, params, stim, task.t_stim, task.dt, None)
    zero = lambda i: np.zeros((1, 2))
    run_epoch(state, params, zero, task.t_iti, task.dt, None)
    out = output_rates(state, params)
    return out[0, 1] - out[0, 0]


def main():
    rows = []
    for w_self in W_SELF_VALUES:
        base_net = NetworkParams(w_self=w_self)
        for age in ["young", "old"]:
            base = scaled_params(age, base_net)
            for m in MULTIPLIERS:
                params_m = scale_total_inhibition(base, m)
                mech = mechanism_asymmetry(params_m, TASK)
                rows.append(dict(
                    w_self=w_self, age=age, multiplier=m, mech_asymmetry=mech,
                    g_pv=params_m.g_pv, g_sst=params_m.g_sst, g_sst_to_pv=params_m.g_sst_to_pv,
                ))
                print(f"  w_self={w_self} {age:5s} / x{m:.2f}  mech_asymmetry={mech:+.4f}")

    mech_df = pd.DataFrame(rows)
    out_path = OUT_DIR / "phase1_mechanism_probe_w_self_sweep.csv"
    mech_df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")

    behavior_path = OUT_DIR / "phase1_w_self_threshold_crosssweep.csv"
    if behavior_path.exists():
        behavior_df = pd.read_csv(behavior_path)
        merged = mech_df.merge(
            behavior_df[["w_self", "age", "multiplier", "kappa_mean", "cohend_vs_baseline", "p_ttest"]],
            on=["w_self", "age", "multiplier"], how="left",
        )
        merged_path = OUT_DIR / "phase1_mechanism_vs_behavior_w_self_sweep.csv"
        merged.to_csv(merged_path, index=False)
        print(f"Saved merged comparison: {merged_path}")

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True)
            colors = {1.2: "tab:green", 1.5: "tab:blue", 2.0: "tab:orange", 2.5: "tab:red"}
            for col, age in enumerate(["young", "old"]):
                ax_mech, ax_behav = axes[0, col], axes[1, col]
                for w_self in W_SELF_VALUES:
                    sub = merged[(merged.age == age) & (merged.w_self == w_self)].sort_values("multiplier")
                    ax_mech.plot(sub.multiplier, sub.mech_asymmetry, "o-", color=colors[w_self], label=f"w_self={w_self}")
                    ax_behav.plot(sub.multiplier, sub.kappa_mean, "o-", color=colors[w_self])
                ax_mech.axhline(0, color="gray", lw=0.5, ls="--")
                ax_mech.axvline(1.0, color="gray", lw=0.5, ls="--")
                ax_behav.axvline(1.0, color="gray", lw=0.5, ls="--")
                ax_mech.set_title(age)
                ax_behav.set_xlabel("total-inhibition multiplier")
            axes[0, 0].set_ylabel("mechanism probe\n(single-trial asymmetry)")
            axes[1, 0].set_ylabel("behavioral kappa\n(animal mean)")
            axes[0, 0].legend(fontsize=8)
            fig.suptitle("Mechanism probe vs. behavioral result, across the w_self x multiplier grid")
            fig.tight_layout()
            fig.savefig(OUT_DIR / "phase1_mechanism_vs_behavior_w_self_sweep.png", dpi=150)
            print(f"Saved plot: {OUT_DIR / 'phase1_mechanism_vs_behavior_w_self_sweep.png'}")
        except Exception as e:
            print(f"Plotting failed (non-fatal): {e}")

        print(merged.to_string(index=False))
    else:
        print(f"NOTE: {behavior_path} not found -- skipping merge/plot against behavioral results.")
        print(mech_df.to_string(index=False))


if __name__ == "__main__":
    main()
