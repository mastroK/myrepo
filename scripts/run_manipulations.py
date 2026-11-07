#!/usr/bin/env python3
"""Phase 1 extension: what does the model predict under named circuit-wide
inhibition manipulations, applied on top of either age baseline?

Full scale by default (10 sessions x 150 trials x 16 animals/group, 15
restarts/session fit -- same as scripts/run_phase1.py's headline run), one
seed per scenario. This is exploratory, single-cohort, NOT replicated the
way the headline young-vs-old result is (see scripts/run_phase1_replications.py) --
treat directionality here as a first-pass prediction, not a statistically
confirmed one, unless/until it's worth the compute to replicate a specific
manipulation the same way.

For each baseline age (young, old) and each manipulation in
sst_pv_model/manipulations.py, simulates+fits the manipulated circuit and
compares against that SAME age's own unmanipulated baseline (independent
samples, same stats convention as run_phase1.py: t-test + Mann-Whitney +
Cohen's d). Also reports the isolated single-trial mechanism-asymmetry
probe for each scenario, explicitly flagged as unreliable on its own (see
PHASE1_SUMMARY.md's "Mechanism check" section -- it disagreed with the
real behavioral result once before, during the SST->PV reopening).

Usage: python scripts/run_manipulations.py [--quick]
  --quick uses a much smaller cohort/trial count for a fast smoke-test run.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.params import TaskParams, scaled_params
from sst_pv_model.manipulations import MANIPULATIONS, apply_manipulation
from sst_pv_model.simulate import simulate_group
from sst_pv_model.qlearning_fit import fit_session_level
from sst_pv_model.network import NetworkState, run_epoch, output_rates

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def animal_level(fit_df):
    return fit_df.groupby("Mouse ID")["kappa"].mean()


def mechanism_asymmetry(params, task):
    """Isolated single-trial probe (forced extreme win -> one ITI). Flagged
    unreliable as a predictor of the real behavioral result on its own --
    see PHASE1_SUMMARY.md's 'Mechanism check' section."""
    state = NetworkState(1)
    stim = lambda i: np.array([[0.0, 3.0]])
    run_epoch(state, params, stim, task.t_stim, task.dt, None)
    zero = lambda i: np.zeros((1, 2))
    run_epoch(state, params, zero, task.t_iti, task.dt, None)
    out = output_rates(state, params)
    return out[0, 1] - out[0, 0]


def run_one(params, task, n_animals, seed, n_starts, label):
    df = simulate_group(params, task, n_animals=n_animals, seed=seed, age_label=label)
    fit = fit_session_level(df, n_starts=n_starts)
    return fit


def compare_to_baseline(fit_baseline, fit_manip, age, manipulation_name):
    a_base = animal_level(fit_baseline).values
    a_manip = animal_level(fit_manip).values
    t, p_t = stats.ttest_ind(a_base, a_manip)
    u, p_u = stats.mannwhitneyu(a_base, a_manip)
    pooled_sd = np.sqrt((a_base.var(ddof=1) + a_manip.var(ddof=1)) / 2)
    cohend = (a_manip.mean() - a_base.mean()) / pooled_sd if pooled_sd > 0 else np.nan
    row = dict(
        age=age, manipulation=manipulation_name,
        kappa_baseline=a_base.mean(), kappa_baseline_sd=a_base.std(),
        kappa_manip=a_manip.mean(), kappa_manip_sd=a_manip.std(),
        diff=a_manip.mean() - a_base.mean(), cohend=cohend,
        p_ttest=p_t, p_mwu=p_u, n_baseline=len(a_base), n_manip=len(a_manip),
    )
    print(f"  {age:5s} / {manipulation_name:28s} kappa: {a_base.mean():+.3f} -> {a_manip.mean():+.3f} "
          f"(diff={row['diff']:+.3f}, d={cohend:+.3f}, p_t={p_t:.4f}, p_mwu={p_u:.4f})")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fast smoke-test scale")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    if args.quick:
        task = TaskParams(n_sessions=3, n_trials_per_session=80, n_animals_per_group=6)
        n_starts = 8
    else:
        task = TaskParams()
        n_starts = 15

    print(f"Task structure: {task.n_sessions} sessions x {task.n_trials_per_session} trials, "
          f"{task.n_animals_per_group} animals/group{' (QUICK)' if args.quick else ''}")
    print(f"Manipulations: {list(MANIPULATIONS)}")

    rows = []
    seed = 100
    for age in ["young", "old"]:
        baseline_params = scaled_params(age)
        print(f"\n=== {age} baseline (g_pv={baseline_params.g_pv:.2f}, g_sst={baseline_params.g_sst:.2f}, "
              f"g_sst_to_pv={baseline_params.g_sst_to_pv:.2f}) ===")
        fit_baseline = run_one(baseline_params, task, task.n_animals_per_group, seed, n_starts, f"{age}_baseline")
        seed += 1
        mech_baseline = mechanism_asymmetry(baseline_params, task)

        for name in MANIPULATIONS:
            manip_params = apply_manipulation(baseline_params, name)
            fit_manip = run_one(manip_params, task, task.n_animals_per_group, seed, n_starts, f"{age}_{name}")
            seed += 1
            row = compare_to_baseline(fit_baseline, fit_manip, age, name)
            row["mech_asym_baseline"] = mech_baseline
            row["mech_asym_manip"] = mechanism_asymmetry(manip_params, task)
            row["g_pv"] = manip_params.g_pv
            row["g_sst"] = manip_params.g_sst
            row["g_sst_to_pv"] = manip_params.g_sst_to_pv
            rows.append(row)

    result = pd.DataFrame(rows)
    out_path = OUT_DIR / "phase1_manipulations.csv"
    result.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
