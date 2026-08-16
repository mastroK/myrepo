"""Rate-based (Wilson-Cowan-style) competing decision circuit.

Two excitatory pools (E0, E1) represent accumulated value/evidence for the
two bandit options. Each pool recruits its own local PV and SST
interneuron drive, which inhibits the COMPETING pool (cross/lateral
inhibition) -- the standard motif for winner-take-all decision circuits:
pool i's own activity is what suppresses pool j, and vice versa.

  s_pv[:, i]  : fast time constant, driven by E[:, i], projects a DIVISIVE
                (perisomatic-like) gain suppression onto pool j's output.
  s_sst[:, i] : slow time constant, driven by E[:, i], projects a
                SUBTRACTIVE (dendritic-like) input offset onto pool j.

Neither the excitatory pools nor the interneuron pools are reset between
trials -- all state variables simply carry over from the end of one trial
into the start of the next. There is no stickiness/history term anywhere
in these equations. Whatever choice-repetition bias emerges is entirely a
side effect of how completely (or incompletely) each pool's cross-
inhibitory tone decays during the inter-trial interval: because it is the
PREVIOUS winner's own (slow, if SST-dominated) interneuron drive that keeps
suppressing the loser, an incompletely-decayed SST tone leaves the loser
pool still below baseline when the next trial's stimulus arrives, biasing
the network to repeat its previous choice.

Everything is vectorized over a `batch` axis so many independent simulated
sessions/animals can be integrated in lockstep with plain numpy loops.
"""

import numpy as np

N_POOLS = 2
_OTHER = np.array([1, 0])  # index of the competing pool for pool i


class NetworkState:
    """State for `batch` independent parallel simulations.

    E     : (batch, 2) excitatory pool rates
    s_pv  : (batch, 2) local fast/divisive inhibitory drive, one per pool
    s_sst : (batch, 2) local slow/subtractive inhibitory drive, one per pool
    """

    __slots__ = ("E", "s_pv", "s_sst")

    def __init__(self, batch):
        self.E = np.zeros((batch, N_POOLS))
        self.s_pv = np.zeros((batch, N_POOLS))
        self.s_sst = np.zeros((batch, N_POOLS))


def _activation(x, theta, k_sig):
    """Bounded sigmoidal firing-rate nonlinearity F(x) in [0, 1]."""
    z = np.clip((x - theta) / k_sig, -50, 50)
    return 1.0 / (1.0 + np.exp(-z))


def step(state, params, I_input, dt):
    """Advance `state` in place by one Euler step of size `dt`.

    I_input: (batch, 2) external drive to each excitatory pool this step
             (zero during the inter-trial interval).
    """
    s_pv_cross = state.s_pv[:, _OTHER]    # (batch, 2): pool i is inhibited by pool j's PV
    s_sst_cross = state.s_sst[:, _OTHER]  # (batch, 2): pool i is inhibited by pool j's SST

    gain = 1.0 + params.g_pv * s_pv_cross
    drive = (params.w_self * state.E + I_input - params.g_sst * s_sst_cross) / gain

    F = _activation(drive, params.theta, params.k_sig)
    dE = (-state.E + F) / params.tau_E

    d_pv = (-state.s_pv + state.E) / params.tau_pv
    d_sst = (-state.s_sst + state.E) / params.tau_sst

    state.E = state.E + dt * dE
    state.s_pv = state.s_pv + dt * d_pv
    state.s_sst = state.s_sst + dt * d_sst
    return state


def output_rates(state, params):
    """Divisively-gated readout rate of each pool (what downstream/choice
    and, in Phase 2, the pyramidal photometry readout are driven by)."""
    s_pv_cross = state.s_pv[:, _OTHER]
    gain = 1.0 + params.g_pv * s_pv_cross
    return state.E / gain


def run_epoch(state, params, I_input_fn, duration, dt, rng, record=False):
    """Integrate `state` forward for `duration` seconds.

    I_input_fn(t_index) -> (batch, 2) array of external input at that step
    (already includes any trial-varying noise the caller wants).
    Returns the (possibly) recorded trajectory of output_rates if
    record=True, else None.
    """
    n_steps = int(round(duration / dt))
    traj = np.empty((n_steps, state.E.shape[0], N_POOLS)) if record else None
    for i in range(n_steps):
        I_input = I_input_fn(i)
        step(state, params, I_input, dt)
        if record:
            traj[i] = output_rates(state, params)
    return traj
