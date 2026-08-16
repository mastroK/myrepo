"""Joint network + task simulation: produces trial-level choice/reward
sequences from the rate-model circuit, in the same long-format schema the
sticky Q-learning fitter (and the real pipeline) expects.

Mechanism, spelled out once here:
  - Each simulated animal tracks its own internal option values V0, V1
    with a plain Rescorla-Wagner update (no stickiness term anywhere).
  - Those values drive input to E0/E1 during a brief "stimulus" epoch.
  - The pool with the higher divisively-gated output at the end of that
    epoch is the trial's choice.
  - Reward is drawn from the task's 80-20 contingency for whichever port
    was chosen.
  - An inter-trial-interval (ITI) epoch follows with zero external input,
    during which E0/E1/S_pv/S_sst simply continue to relax under their own
    dynamics -- NOT forcibly reset. Whatever activity survives the ITI
    carries directly into the next trial's stimulus epoch.
  - Network state (but not learned values) is reset at the start of each
    new session, matching real sessions being separated by rest/off days.

Any resulting trial-to-trial choice-repetition bias is therefore an
emergent consequence of how completely PV (fast/divisive) vs. SST
(slow/subtractive) inhibition clears residual pool activity during the
ITI -- not a term fit or coded in directly.
"""

import numpy as np
import pandas as pd

from .network import NetworkState, run_epoch, output_rates
from .task import make_high_port_schedule, draw_reward


def simulate_group(params, task_params, n_animals, seed, age_label, animal_prefix=None):
    """Simulate `n_animals` independent animals under one NetworkParams
    setting (i.e. one age) across task_params.n_sessions sessions each.

    Returns a long-format DataFrame with columns:
    Mouse ID, Session ID, Trial, Decision, Reward, Age
    """
    rng = np.random.default_rng(seed)
    prefix = animal_prefix or age_label
    n_trials = task_params.n_trials_per_session
    n_steps_stim = int(round(task_params.t_stim / task_params.dt))
    n_steps_iti = int(round(task_params.t_iti / task_params.dt))

    records = []
    for session_idx in range(task_params.n_sessions):
        state = NetworkState(n_animals)
        V = np.full((n_animals, 2), 0.5)

        schedules = np.stack(
            [
                make_high_port_schedule(
                    n_trials, task_params.block_len_min, task_params.block_len_max, rng
                )
                for _ in range(n_animals)
            ],
            axis=1,
        )  # (n_trials, n_animals)

        for trial_idx in range(n_trials):
            base_input = params.input_gain * V  # (n_animals, 2)
            # One noise draw per trial (not resampled every dt step): this is
            # trial-level sensory/decision noise held constant across the
            # stimulus epoch, matching standard evidence-accumulation models.
            # Per-step-resampled white noise gets averaged down by the pool's
            # own leaky (tau_E) integration and barely perturbs the final
            # choice; a single per-trial draw is what actually lets decision
            # stochasticity compete with the value-driven (Q-diff-like) drive.
            trial_noise = rng.normal(0.0, params.noise_sigma, size=base_input.shape)
            stim_input_arr = base_input + trial_noise

            def stim_input(_step, arr=stim_input_arr):
                return arr

            run_epoch(state, params, stim_input, task_params.t_stim, task_params.dt, rng)

            out = output_rates(state, params)  # (n_animals, 2)
            choice = (out[:, 1] > out[:, 0]).astype(int)

            high_port = schedules[trial_idx]
            reward = draw_reward(choice, high_port, task_params.p_high, task_params.p_low, rng)

            idx = np.arange(n_animals)
            V[idx, choice] += params.alpha_net * (reward - V[idx, choice])

            zero_input = lambda _step, shape=base_input.shape: np.zeros(shape)
            run_epoch(state, params, zero_input, task_params.t_iti, task_params.dt, rng)

            for a in range(n_animals):
                records.append(
                    {
                        "Mouse ID": f"{prefix}_{a:03d}",
                        "Session ID": f"{prefix}_{a:03d}_s{session_idx:02d}",
                        "Trial": trial_idx + 1,
                        "Decision": int(choice[a]),
                        "Reward": int(reward[a]),
                        "Age": age_label,
                    }
                )

    return pd.DataFrame.from_records(records)
