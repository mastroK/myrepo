import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.network import NetworkState, run_epoch, output_rates, _pv_cross_net
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


def test_sst_to_pv_discount_unaffects_early_window_but_diverges_later():
    """Mechanism check for the SST->PV coupling added 2026-11-06: the
    SEPARATE, slower s_sst_pv pathway (tau_sst_pv, not the existing
    tau_sst=100ms subtractive pathway) should leave PV's cross-pool reach
    effectively age-INVARIANT shortly after an isolated activation (s_sst_pv
    hasn't built up enough yet for the age-different gain to matter), then
    diverge once s_sst_pv has risen further -- never flipping
    net-disinhibitory (floored at 0).

    Deliberately isolated from the full task protocol (a brief pulse, not
    the 150ms stimulus epoch): the claim is about the synapse's own IPSC
    shape following SST activation, not about the full behavioral trial."""
    young = scaled_params("young")
    old = scaled_params("old")
    assert young.g_sst_to_pv < old.g_sst_to_pv  # the reported finding's direction

    def pv_cross_net_after_pulse(params, t_after_pulse):
        state = NetworkState(1)
        pulse = lambda i: np.array([[0.0, 3.0]])
        run_epoch(state, params, pulse, 0.02, params.tau_pv / 10, None)  # brief activation
        zero = lambda i: np.zeros((1, 2))
        run_epoch(state, params, zero, t_after_pulse, params.tau_pv / 10, None)
        return _pv_cross_net(state, params)[0, 0]  # pool 0's view of pool 1's net PV reach

    early_young = pv_cross_net_after_pulse(young, 0.05)
    early_old = pv_cross_net_after_pulse(old, 0.05)
    late_young = pv_cross_net_after_pulse(young, 0.30)
    late_old = pv_cross_net_after_pulse(old, 0.30)

    assert early_young == pytest.approx(early_old, rel=0.1)
    assert late_old < late_young  # old's larger g_sst_to_pv discounts more once s_sst_pv has risen
    assert late_old >= 0.0 and late_young >= 0.0  # floored, never net-disinhibitory
