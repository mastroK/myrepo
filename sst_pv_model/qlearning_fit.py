"""Sticky Q-learning fit -- vendored from mastroK/mastro_mouse_bandit_analysis
`qlearning.py` (Module 2 of the real analysis pipeline) so simulated choice
sequences are fit with the IDENTICAL model/NLL/optimizer used on real data.

Vendored rather than imported because this package lives in a separate repo
from the real pipeline. `qlearn_sticky_nll`, `multistart_fit`, and
`boundary_flags` below are copied verbatim (same bounds, same optimizer
settings); only `fit_session_level`'s column defaults were left as-is since
`simulate.py` already produces matching column names.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ALPHA_BOUNDS = (1e-4, 1 - 1e-4)
BETA_BOUNDS = (1e-3, 50.0)
KAPPA_BOUNDS = (-10.0, 10.0)
BOUNDS = [ALPHA_BOUNDS, BETA_BOUNDS, KAPPA_BOUNDS]

BETA_BOUND_THRESH = 49.9
KAPPA_BOUND_THRESH = 9.9
ALPHA_BOUND_LO = 0.001
ALPHA_BOUND_HI = 0.999

NLL_CHANCE_THRESH = 0.70


def qlearn_sticky_nll(params, choices, rewards):
    """Negative log-likelihood for the sticky Q-learning model.

    stick = +1 (repeat right) | -1 (repeat left) | 0 (trial 1)
    z = beta*(Q_right - Q_left) + kappa*stick
    P(right) = sigmoid(z)
    Q(c) <- Q(c) + alpha*(r - Q(c))
    """
    alpha, beta, kappa = params
    if not (0 < alpha < 1) or beta <= 0:
        return np.inf

    Q = np.array([0.5, 0.5], dtype=float)
    nll = 0.0
    prev_choice = None

    for c, r in zip(choices, rewards):
        stick = 0.0 if prev_choice is None else (1.0 if prev_choice == 1 else -1.0)
        z = beta * (Q[1] - Q[0]) + kappa * stick
        p1 = 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))
        p = p1 if c == 1 else (1.0 - p1)
        nll -= np.log(p + 1e-12)
        Q[c] += alpha * (r - Q[c])
        prev_choice = c

    return nll


def multistart_fit(choices, rewards, n_starts, seed_offset=0):
    """Run L-BFGS-B from n_starts random initializations, return the best OptimizeResult."""
    best = None
    for seed in range(seed_offset, seed_offset + n_starts):
        rng = np.random.default_rng(seed)
        x0 = np.array(
            [rng.uniform(0.1, 0.9), rng.uniform(0.5, 5.0), rng.uniform(-2.0, 2.0)]
        )
        res = minimize(
            qlearn_sticky_nll, x0=x0, args=(choices, rewards), method="L-BFGS-B", bounds=BOUNDS
        )
        if best is None or res.fun < best.fun:
            best = res
    return best


def boundary_flags(x):
    alpha, beta, kappa = x
    return {
        "beta_at_bound": beta >= BETA_BOUND_THRESH,
        "kappa_at_bound": abs(kappa) >= KAPPA_BOUND_THRESH,
        "alpha_at_bound": alpha <= ALPHA_BOUND_LO or alpha >= ALPHA_BOUND_HI,
    }


def label_fit_groups(params_df):
    any_bound = params_df[["beta_at_bound", "kappa_at_bound", "alpha_at_bound"]].any(axis=1)
    nll_per_trial = params_df["nll"] / params_df["n_trials"]

    params_df = params_df.copy()
    params_df["group"] = "non_boundary"
    params_df.loc[any_bound & (nll_per_trial < NLL_CHANCE_THRESH), "group"] = "fast_learner"
    params_df.loc[any_bound & (nll_per_trial >= NLL_CHANCE_THRESH), "group"] = "non_learner"
    return params_df


def fit_session_level(
    df,
    col_animal="Mouse ID",
    col_session="Session ID",
    col_trial="Trial",
    col_choice="Decision",
    col_outcome="Reward",
    min_trials=30,
    n_starts=20,
):
    """Fit the sticky Q-learning model independently to each session."""
    records = []
    for session, sdf in df.groupby(col_session):
        sdf = sdf.sort_values(col_trial)
        choices = sdf[col_choice].dropna().values.astype(int)
        rewards = sdf[col_outcome].dropna().values.astype(int)
        if len(choices) < min_trials:
            continue

        best = multistart_fit(choices, rewards, n_starts)
        records.append(
            {
                col_session: session,
                col_animal: sdf[col_animal].iloc[0],
                "alpha": best.x[0],
                "beta": best.x[1],
                "kappa": best.x[2],
                "nll": best.fun,
                "n_trials": len(choices),
                **boundary_flags(best.x),
            }
        )

    return label_fit_groups(pd.DataFrame(records))
