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
# EMPIRICAL (fold-change) anchors -- from real SST-Cre;Ai32 / PV-Cre;Ai32
# ChR2 dose-response curves (mean +/- SEM evoked charge, fC/pF, vs. laser
# power), read off the saturating (~15 mW) plateau of each age-group curve.
# These are graph-read estimates, not exact table values -- ask for the
# underlying per-cell table if tighter precision is wanted.
#
#   PV:  young (6-9wk) approx 3650 fC/pF  ->  old (16-36wk) approx 5150 fC/pF
#        fold-change (old/young) approx 1.4
#   SST: young (6-9wk) approx 16100 fC/pF ->  old (16-36wk) approx 11700 fC/pF
#        fold-change (old/young) approx 0.73
#
# Note the two curves differ in SHAPE, not just magnitude: PV's age gap is
# present across the whole laser-power range, while SST's curves overlap at
# low power and only diverge near saturation. The model only uses the
# saturating-charge fold-change below, so this shape difference doesn't
# currently affect it -- flagged in case a intensity-resolved treatment
# matters later.
SST_FOLD_CHANGE_OLD_OVER_YOUNG = 0.73   # EMPIRICAL (graph-read), SST charge declines w/ age
PV_FOLD_CHANGE_OLD_OVER_YOUNG = 1.4     # EMPIRICAL (graph-read), PV charge increases w/ age

# Age mapping: per your confirmation, "young" = 6-9wk and "old" = 16-36wk,
# matching the ages actually recorded in the SST/PV ChR2 slice data (not the
# behavioral cohort's own 2-5wk/16-30wk bins, which weren't recorded here).
AGE_LABELS = {"young": "6-9wk", "old": "16-36wk"}


@dataclass(frozen=True)
class NetworkParams:
    # --- excitatory pools ---
    tau_E: float = 0.020        # s, ASSUMED: typical cortical pyramidal membrane/synaptic tau
    w_self: float = 2.0         # ASSUMED: recurrent self-excitation strength (free/robustness param)
    input_gain: float = 4.0     # ASSUMED: scales internal value V into a pool input drive
    noise_sigma: float = 0.20   # ASSUMED: per-trial input noise SD (sets choice stochasticity);
                                # calibrated so the fraction of sessions hitting the sticky-Q
                                # optimizer's parameter bounds (~20-30%) is in the same ballpark
                                # as the real cohort's own ~30% boundary-hit rate

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

    # NOTE on what is deliberately NOT modeled here: s_pv/s_sst are driven by
    # the local excitatory pool (state.E) with a FIXED, age-invariant
    # coupling in network.py -- only the OUTPUT side (g_pv, g_sst above)
    # scales with age. You've told us (electrical-stimulation recordings)
    # that with age: (a) feedforward EPSC onto PV cells declines, and (b)
    # PV cells' intrinsic excitability increases. These two changes act on
    # the INPUT side of the PV pathway and pull in opposite directions on
    # net PV recruitment (less synaptic drive, but easier to fire once
    # driven) -- plausibly partially offsetting, which is what motivates
    # leaving that coupling age-invariant rather than a claim that neither
    # effect exists. This is a considered simplification, not an oversight:
    # kept this way deliberately (per your explicit call) rather than
    # building a combined EPSC+excitability input-recruitment model, since
    # we don't have matched quantitative magnitudes for both to know
    # whether/how much they actually cancel, and no equivalent SST-cell
    # excitability data. Revisit if those numbers become available.

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
    "SST_FOLD_CHANGE_OLD_OVER_YOUNG": "EMPIRICAL but graph-read (not exact table values) from SST-ChR2 charge dose-response curves, saturating plateau, 6-9wk vs 16-36wk",
    "PV_FOLD_CHANGE_OLD_OVER_YOUNG": "EMPIRICAL but graph-read (not exact table values) from PV-ChR2 charge dose-response curves, saturating plateau, 6-9wk vs 16-36wk",
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
