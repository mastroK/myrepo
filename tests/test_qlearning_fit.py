import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.qlearning_fit import fit_session_level, qlearn_sticky_nll, multistart_fit


def _generate_sticky_q_data(alpha, beta, kappa, n_trials, seed):
    """Generate choices/rewards directly from the sticky-Q generative model
    (independent of the network) to sanity-check the fitter recovers known
    parameters."""
    rng = np.random.default_rng(seed)
    Q = np.array([0.5, 0.5])
    prev_choice = None
    choices, rewards = [], []
    for _ in range(n_trials):
        stick = 0.0 if prev_choice is None else (1.0 if prev_choice == 1 else -1.0)
        z = beta * (Q[1] - Q[0]) + kappa * stick
        p1 = 1.0 / (1.0 + np.exp(-z))
        c = int(rng.random() < p1)
        r = int(rng.random() < (0.8 if c == 1 else 0.2))
        Q[c] += alpha * (r - Q[c])
        choices.append(c)
        rewards.append(r)
        prev_choice = c
    return np.array(choices), np.array(rewards)


def test_fitter_recovers_known_kappa_sign():
    choices, rewards = _generate_sticky_q_data(alpha=0.3, beta=3.0, kappa=1.5, n_trials=400, seed=0)
    best = multistart_fit(choices, rewards, n_starts=10)
    assert best.x[2] > 0.3  # recovered kappa should be clearly positive, near-ish 1.5

    choices2, rewards2 = _generate_sticky_q_data(alpha=0.3, beta=3.0, kappa=-1.5, n_trials=400, seed=1)
    best2 = multistart_fit(choices2, rewards2, n_starts=10)
    assert best2.x[2] < -0.3


def test_fit_session_level_shape():
    choices, rewards = _generate_sticky_q_data(alpha=0.3, beta=3.0, kappa=0.5, n_trials=100, seed=2)
    df = pd.DataFrame({
        "Mouse ID": ["m1"] * 100,
        "Session ID": ["s1"] * 100,
        "Trial": np.arange(1, 101),
        "Decision": choices,
        "Reward": rewards,
    })
    fit = fit_session_level(df, n_starts=5)
    assert len(fit) == 1
    assert {"alpha", "beta", "kappa", "group"} <= set(fit.columns)
