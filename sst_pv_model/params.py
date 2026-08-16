"""Central parameter table for the SST:PV network model.

Every number below is tagged as either EMPIRICAL (traceable to a real
measurement you gave us) or ASSUMED (a placeholder or literature-typical
value that was NOT constrained by your data). Nothing here should be read
as a claim about the real circuit until the EMPIRICAL entries are replaced
with your actual numbers.

Run `print_assumption_report()` (also called by scripts/run_phase1.py) to
get a flat, human-readable list of every assumed parameter before trusting
any downstream result.
"""

from dataclasses import dataclass, field, replace


# ---------------------------------------------------------------------------
# EMPIRICAL (fold-change) anchors -- PLACEHOLDER VALUES, see note below.
# ---------------------------------------------------------------------------
# You asked to proceed with clearly-flagged placeholders rather than block
# Phase 1 on the real numbers. These two fold-changes are the ONLY inputs
# that set how much SST vs. PV inhibitory weight the "young" and "old"
# networks get. Replace SST_FOLD_CHANGE_OLD_OVER_YOUNG and
# PV_FOLD_CHANGE_OLD_OVER_YOUNG with your isolated SST-Cre;Ai32 and
# PV-Cre;Ai32 ChR2-evoked amplitude ratios (old/young) and every downstream
# number in Phase 1/2 will update automatically.
#
# Direction is taken from your stated background (SST amplitude declines
# with age, PV amplitude increases with age); MAGNITUDE below is an
# illustrative placeholder, not a measurement.
SST_FOLD_CHANGE_OLD_OVER_YOUNG = 0.5   # PLACEHOLDER: assumed 2x amplitude decrease
PV_FOLD_CHANGE_OLD_OVER_YOUNG = 2.0    # PLACEHOLDER: assumed 2x amplitude increase

# Age mapping, per your instruction: use the youngest/oldest bandit-cohort
# bins directly (2-5wk vs 16-30wk) rather than separate slice-ephys ages.
AGE_LABELS = {"young": "2-5wk", "old": "16-30wk"}


@dataclass(frozen=True)
class NetworkParams:
    # --- excitatory pools ---
    tau_E: float = 0.020        # s, ASSUMED: typical cortical pyramidal membrane/synaptic tau
    w_self: float = 2.0         # ASSUMED: recurrent self-excitation strength (free/robustness param)
    input_gain: float = 4.0     # ASSUMED: scales internal value V into a pool input drive
    noise_sigma: float = 0.30   # ASSUMED: per-step input noise SD (sets choice stochasticity)

    # --- inhibitory populations ---
    # Kinetics: PV faster than SST is an empirical constraint (isolated ChR2
    # kinetics + compound IPSC speeding with age); the ABSOLUTE tau values
    # below are literature-typical (fast perisomatic PV ~10-20 ms decay,
    # slower dendritic SST ~80-150 ms decay) rather than measured in this
    # dataset, and are held FIXED across age -- only the WEIGHTS (g_pv,
    # g_sst) change with age, per fold-change data. This is deliberate: it's
    # what makes the age-shift in emergent (compound) suppression kinetics
    # in Phase 2 an emergent prediction rather than something hardcoded in.
    tau_pv: float = 0.015        # s, ASSUMED (literature-typical fast/perisomatic)
    tau_sst: float = 0.100       # s, ASSUMED (literature-typical slow/dendritic)

    g_pv: float = 1.0            # divisive gain weight, set per age from PV fold-change
    g_sst: float = 1.0           # subtractive weight, set per age from SST fold-change

    # --- activation function F(x) = 1 / (1 + exp(-(x-theta)/k)) ---
    theta: float = 0.0           # ASSUMED: activation threshold/offset
    k_sig: float = 0.5           # ASSUMED: activation slope

    # --- internal (network-side) value tracking, NOT the external Q-learning fit ---
    alpha_net: float = 0.25      # ASSUMED: internal Rescorla-Wagner learning rate driving pool input


def scaled_params(age: str, base: NetworkParams = NetworkParams()) -> NetworkParams:
    """Return NetworkParams with g_sst/g_pv set for 'young' or 'old'.

    Young is the reference (fold-change = 1.0 by construction); old is
    scaled by the SST/PV fold-changes above. Absolute gain magnitude
    (the multiplier applied to the young reference) is itself an ASSUMED
    normalization -- only the young:old RATIO is anchored to your data.
    """
    if age == "young":
        return replace(base, g_sst=1.0, g_pv=1.0)
    elif age == "old":
        return replace(
            base,
            g_sst=1.0 * SST_FOLD_CHANGE_OLD_OVER_YOUNG,
            g_pv=1.0 * PV_FOLD_CHANGE_OLD_OVER_YOUNG,
        )
    else:
        raise ValueError(f"unknown age label: {age!r}")


@dataclass(frozen=True)
class TaskParams:
    """80-20 bandit task/session structure.

    Trial counts, session counts, block lengths, and cohort size are all
    ASSUMED defaults (you asked to proceed with reasonable placeholders
    here rather than the exact real numbers) -- flagged so any effect-size
    comparison against the real data is understood as directional/
    qualitative, not a magnitude match.
    """
    n_sessions: int = 10          # EMPIRICAL: matches the real 80-20 cohort (10 sessions/animal)
    n_trials_per_session: int = 150   # ASSUMED: typical mouse bandit session length
    n_animals_per_group: int = 16     # ASSUMED: typical cohort size
    p_high: float = 0.8            # EMPIRICAL: 80-20 contingency
    p_low: float = 0.2              # EMPIRICAL: 80-20 contingency
    block_len_min: int = 15         # ASSUMED: reversal block length range
    block_len_max: int = 25         # ASSUMED: reversal block length range

    # Trial epoch durations (s), ASSUMED (chosen to be a few tau_sst long so
    # the ITI is long enough to reveal differential SST vs. PV reset).
    t_stim: float = 0.15
    t_iti: float = 0.35
    dt: float = 0.002


ASSUMED_PARAMETERS = {
    "SST_FOLD_CHANGE_OLD_OVER_YOUNG": "PLACEHOLDER direction-only (SST declines w/ age); magnitude not from real data",
    "PV_FOLD_CHANGE_OLD_OVER_YOUNG": "PLACEHOLDER direction-only (PV increases w/ age); magnitude not from real data",
    "NetworkParams.tau_E": "literature-typical, not measured in this dataset",
    "NetworkParams.w_self": "free/robustness parameter, swept in sensitivity analysis",
    "NetworkParams.input_gain": "free/robustness parameter, swept in sensitivity analysis",
    "NetworkParams.noise_sigma": "sets choice stochasticity, not empirically constrained",
    "NetworkParams.tau_pv": "literature-typical fast/perisomatic IPSC decay, not measured here",
    "NetworkParams.tau_sst": "literature-typical slow/dendritic IPSC decay, not measured here",
    "NetworkParams.theta / k_sig": "activation function shape, arbitrary units",
    "NetworkParams.alpha_net": "network's internal value-learning rate (distinct from the externally fitted Q-learning alpha)",
    "TaskParams.n_trials_per_session": "ASSUMED session length, not the real cohort's exact count",
    "TaskParams.n_animals_per_group": "ASSUMED cohort size",
    "TaskParams.block_len_min/max": "ASSUMED reversal-block length range",
}


def print_assumption_report():
    print("=" * 78)
    print("UNCONSTRAINED / PLACEHOLDER PARAMETERS -- treat downstream results as")
    print("a qualitative/directional sufficiency test, not a magnitude match,")
    print("until these are replaced with real values.")
    print("=" * 78)
    for name, note in ASSUMED_PARAMETERS.items():
        print(f"  - {name}: {note}")
    print("=" * 78)


if __name__ == "__main__":
    print_assumption_report()
