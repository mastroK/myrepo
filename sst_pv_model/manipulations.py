"""Phase 1 extension: named circuit-wide inhibition manipulations, applied
on top of either age baseline.

Each manipulation is defined as a multiplicative scaling of the relevant
gain parameter(s) relative to whichever baseline NetworkParams it's applied
to -- these are NOT new empirical findings, they are exploratory "what
would the model predict if you did X" interventions, requested directly
(e.g. to plan pharmacology/optogenetics experiments around).

Manipulations:
  lower_total_inhibition  : halve g_pv, g_sst, AND g_sst_to_pv together
                            (a global GABAergic-tone-down intervention,
                            e.g. a GABA-A antagonist / broad disinhibition)
  higher_total_inhibition : the same three gains x1.5 (e.g. a
                            benzodiazepine-like broad potentiation)
  lower_pv_only           : halve g_pv alone (e.g. PV-specific
                            chemogenetic/optogenetic silencing)
  lower_sst_only          : halve g_sst AND g_sst_to_pv together (e.g. SST-
                            specific silencing -- this reduces BOTH of
                            SST's output pathways, since silencing the
                            presynaptic population reduces everything it
                            does, not just one of its two targets)

"Total inhibition" is interpreted as the circuit's inhibitory GAIN
parameters (g_pv, g_sst, g_sst_to_pv) -- not the interneuron time constants
(tau_pv, tau_sst, tau_sst_pv), which represent kinetics, not strength, and
are already covered by the existing robustness sweep
(sst_pv_model/sensitivity.py).
"""

from dataclasses import replace


def scale_total_inhibition(p, multiplier):
    """Scale all three inhibitory gains (g_pv, g_sst, g_sst_to_pv) together
    by an arbitrary multiplier relative to whichever baseline `p` already
    is. Generalizes _lower_total/_higher_total (multiplier=0.5/1.5) to any
    value, for sweeping the "total inhibition" axis continuously rather
    than at only two fixed points -- see scripts/run_total_inhibition_sweep.py.
    """
    return replace(p, g_pv=p.g_pv * multiplier, g_sst=p.g_sst * multiplier,
                    g_sst_to_pv=p.g_sst_to_pv * multiplier)


def _lower_total(p):
    return scale_total_inhibition(p, 0.5)


def _higher_total(p):
    return scale_total_inhibition(p, 1.5)


def _lower_pv_only(p):
    return replace(p, g_pv=p.g_pv * 0.5)


def _lower_sst_only(p):
    return replace(p, g_sst=p.g_sst * 0.5, g_sst_to_pv=p.g_sst_to_pv * 0.5)


MANIPULATIONS = {
    "lower_total_inhibition": _lower_total,
    "higher_total_inhibition": _higher_total,
    "lower_pv_only": _lower_pv_only,
    "lower_sst_only": _lower_sst_only,
}


def apply_manipulation(base_params, name):
    if name not in MANIPULATIONS:
        raise ValueError(f"unknown manipulation: {name!r}, choices: {list(MANIPULATIONS)}")
    return MANIPULATIONS[name](base_params)
