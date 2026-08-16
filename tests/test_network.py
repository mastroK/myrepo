import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.network import NetworkState, run_epoch, output_rates
from sst_pv_model.params import NetworkParams, TaskParams, scaled_params


def test_dynamics_stay_bounded():
    p = NetworkParams()
    state = NetworkState(4)
    stim = lambda i: np.array([[0.0, 3.0], [3.0, 0.0], [1.0, 1.0], [0.0, 0.0]])
    run_epoch(state, p, stim, 0.15, 0.002, None)
    assert np.all(np.isfinite(state.E))
    assert np.all(state.E >= -1e-6)
    out = output_rates(state, p)
    assert np.all(np.isfinite(out))


def test_young_retains_more_residual_asymmetry_than_old():
    """Core mechanism check: after an identical 'win' for pool 1 followed by
    the same ITI duration, the young (SST-high/PV-low) network should carry
    more residual winner-vs-loser asymmetry into the next trial than old
    (SST-low/PV-high), since PV's fast/divisive inhibition should clear the
    imbalance more completely."""
    task = TaskParams()
    young = scaled_params("young")
    old = scaled_params("old")

    def residual_asymmetry(params):
        state = NetworkState(1)
        stim = lambda i: np.array([[0.0, 3.0]])
        run_epoch(state, params, stim, task.t_stim, task.dt, None)
        zero = lambda i: np.zeros((1, 2))
        run_epoch(state, params, zero, task.t_iti, task.dt, None)
        out = output_rates(state, params)
        return out[0, 1] - out[0, 0]

    asym_young = residual_asymmetry(young)
    asym_old = residual_asymmetry(old)
    assert asym_young > asym_old > 0
