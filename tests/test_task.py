import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.task import make_high_port_schedule, draw_reward


def test_schedule_length_and_values():
    rng = np.random.default_rng(0)
    sched = make_high_port_schedule(200, 10, 20, rng)
    assert len(sched) == 200
    assert set(np.unique(sched)) <= {0, 1}


def test_schedule_has_reversals():
    rng = np.random.default_rng(0)
    sched = make_high_port_schedule(500, 10, 20, rng)
    n_switches = np.sum(np.diff(sched) != 0)
    assert n_switches > 5  # should reverse repeatedly over 500 trials


def test_reward_probabilities_roughly_match():
    rng = np.random.default_rng(1)
    n = 50000
    choice = np.zeros(n, dtype=int)
    high_port = np.zeros(n, dtype=int)  # always choosing the high port
    r = draw_reward(choice, high_port, p_high=0.8, p_low=0.2, rng=rng)
    assert abs(r.mean() - 0.8) < 0.01

    choice_low = np.ones(n, dtype=int)
    r_low = draw_reward(choice_low, high_port, p_high=0.8, p_low=0.2, rng=rng)
    assert abs(r_low.mean() - 0.2) < 0.01
