import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sst_pv_model.params import scaled_params
from sst_pv_model.manipulations import MANIPULATIONS, apply_manipulation


def test_lower_total_inhibition_halves_all_three_gains():
    base = scaled_params("old")
    manip = apply_manipulation(base, "lower_total_inhibition")
    assert manip.g_pv == base.g_pv * 0.5
    assert manip.g_sst == base.g_sst * 0.5
    assert manip.g_sst_to_pv == base.g_sst_to_pv * 0.5


def test_higher_total_inhibition_scales_all_three_gains_up():
    base = scaled_params("young")
    manip = apply_manipulation(base, "higher_total_inhibition")
    assert manip.g_pv == base.g_pv * 1.5
    assert manip.g_sst == base.g_sst * 1.5
    assert manip.g_sst_to_pv == base.g_sst_to_pv * 1.5


def test_lower_pv_only_touches_only_g_pv():
    base = scaled_params("old")
    manip = apply_manipulation(base, "lower_pv_only")
    assert manip.g_pv == base.g_pv * 0.5
    assert manip.g_sst == base.g_sst
    assert manip.g_sst_to_pv == base.g_sst_to_pv


def test_lower_sst_only_touches_both_sst_pathways_not_pv():
    """Silencing SST should reduce BOTH of its output pathways (onto the
    competing pool, and onto PV) since both come from the same presynaptic
    population -- not just one of the two."""
    base = scaled_params("young")
    manip = apply_manipulation(base, "lower_sst_only")
    assert manip.g_sst == base.g_sst * 0.5
    assert manip.g_sst_to_pv == base.g_sst_to_pv * 0.5
    assert manip.g_pv == base.g_pv


def test_unknown_manipulation_raises():
    base = scaled_params("young")
    try:
        apply_manipulation(base, "not_a_real_manipulation")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_all_manipulations_are_registered_and_applicable():
    base = scaled_params("old")
    for name in MANIPULATIONS:
        manip = apply_manipulation(base, name)
        assert manip.g_pv > 0 and manip.g_sst > 0 and manip.g_sst_to_pv >= 0
