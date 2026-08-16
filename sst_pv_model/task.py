"""80-20 probabilistic bandit task structure (block schedule + reward draws).

Independent of the network -- just generates, per simulated session, which
port is the "high" (80%) port on each trial, with block-based reversals.
Block lengths and trial/session counts are ASSUMED (ballpark, not the real
cohort's exact numbers) -- see sst_pv_model.params.TaskParams docstring.
"""

import numpy as np


def make_high_port_schedule(n_trials, block_len_min, block_len_max, rng):
    """Return an (n_trials,) array of 0/1 indicating the high-reward port,
    switching at randomized block boundaries."""
    schedule = np.empty(n_trials, dtype=int)
    pos = 0
    high_port = rng.integers(0, 2)
    while pos < n_trials:
        block_len = rng.integers(block_len_min, block_len_max + 1)
        end = min(pos + block_len, n_trials)
        schedule[pos:end] = high_port
        high_port = 1 - high_port
        pos = end
    return schedule


def draw_reward(choice, high_port, p_high, p_low, rng):
    """Bernoulli reward draw given which port was chosen this trial.

    choice, high_port: (batch,) int arrays. Vectorized.
    """
    p = np.where(choice == high_port, p_high, p_low)
    return (rng.random(choice.shape) < p).astype(int)
