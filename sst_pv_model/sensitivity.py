"""Phase 1 step 5: robustness/sensitivity sweep.

Sweeps the model's free (ASSUMED, not empirically-anchored) parameters --
tau_pv, tau_sst, w_self (coupling/recurrent-excitation strength), and
noise_sigma -- one at a time around the baseline used for the headline
result, and checks whether young still shows higher fitted kappa than old
at every swept value. This is deliberately a coarse, fast (reduced
trial-count) sweep: the question is direction-robustness, not a precise
effect-size map.
"""

from dataclasses import replace

import numpy as np
import pandas as pd
from scipy import stats

from .params import NetworkParams, TaskParams, SST_FOLD_CHANGE_OLD_OVER_YOUNG, PV_FOLD_CHANGE_OLD_OVER_YOUNG
from .simulate import simulate_group
from .qlearning_fit import fit_session_level


def _run_one(base_params, task_params, n_animals, seed):
    young = replace(base_params, g_sst=1.0, g_pv=1.0)
    old = replace(
        base_params,
        g_sst=1.0 * SST_FOLD_CHANGE_OLD_OVER_YOUNG,
        g_pv=1.0 * PV_FOLD_CHANGE_OLD_OVER_YOUNG,
    )
    df_y = simulate_group(young, task_params, n_animals=n_animals, seed=seed, age_label="young")
    df_o = simulate_group(old, task_params, n_animals=n_animals, seed=seed + 1, age_label="old")
    fit_y = fit_session_level(df_y, n_starts=8)
    fit_o = fit_session_level(df_o, n_starts=8)
    ky, ko = fit_y["kappa"].values, fit_o["kappa"].values
    if len(ky) < 2 or len(ko) < 2:
        return dict(kappa_young=np.nan, kappa_old=np.nan, diff=np.nan, p=np.nan, cohend=np.nan)
    t, p = stats.ttest_ind(ky, ko)
    pooled_sd = np.sqrt((ky.var(ddof=1) + ko.var(ddof=1)) / 2)
    d = (ky.mean() - ko.mean()) / pooled_sd if pooled_sd > 0 else np.nan
    return dict(kappa_young=ky.mean(), kappa_old=ko.mean(), diff=ky.mean() - ko.mean(), p=p, cohend=d)


def sweep_parameter(param_name, values, base_params=None, task_params=None, n_animals=8, seed=0):
    base_params = base_params or NetworkParams()
    task_params = task_params or TaskParams(n_sessions=3, n_trials_per_session=100)
    rows = []
    for v in values:
        params_v = replace(base_params, **{param_name: v})
        result = _run_one(params_v, task_params, n_animals, seed)
        rows.append({param_name: v, **result})
    return pd.DataFrame(rows)


def run_robustness_suite(n_animals=8, seed=0):
    """Sweep each free parameter one-at-a-time around the baseline and
    report whether the qualitative direction (young kappa > old kappa)
    holds at every swept value."""
    base = NetworkParams()
    task = TaskParams(n_sessions=3, n_trials_per_session=100)

    sweeps = {
        "tau_pv": sweep_parameter("tau_pv", [0.008, 0.010, 0.015, 0.020, 0.030], base, task, n_animals, seed),
        "tau_sst": sweep_parameter("tau_sst", [0.06, 0.08, 0.10, 0.13, 0.16], base, task, n_animals, seed),
        "w_self": sweep_parameter("w_self", [1.2, 1.5, 2.0, 2.5], base, task, n_animals, seed),
        "noise_sigma": sweep_parameter("noise_sigma", [0.18, 0.22, 0.25, 0.30], base, task, n_animals, seed),
    }
    return sweeps


def summarize_robustness(sweeps):
    lines = []
    for name, df in sweeps.items():
        n_ok = (df["diff"] > 0).sum()
        n_total = df["diff"].notna().sum()
        lines.append(f"{name}: young>old kappa in {n_ok}/{n_total} swept values")
        lines.append(df.to_string(index=False))
        lines.append("")
    return "\n".join(lines)
