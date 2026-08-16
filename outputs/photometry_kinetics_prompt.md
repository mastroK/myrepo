# Prompt for Claude Code (run inside the `Photometry_Analysis` repo)

Add onset-latency and decay-time-constant extraction to the existing
reward-evoked photometry kinetics pipeline, alongside the peak-amplitude
and AUC metrics that already exist.

## Context

`alignment/windowing.py::compute_per_trial_event_metrics` already computes,
for every trial, a baseline-corrected z-scored PETH (via
`compute_event_aligned_zscore`) and extracts **peak z-score** and **AUC**
in a fixed post-event window (`metric_window_s`, e.g.
`config.params.DECISION_WINDOW_S`). I need two more metrics computed the
same way, from the same z-scored traces: **onset latency** and **decay
time constant**. These three (peak/AUC already done, onset latency, decay
tau) together need to be directly comparable to an external computational
model's simulated kinetics, so the definitions need to be explicit and
documented, not just implicit in code.

## Why per-trial won't work for onset/decay, but does for peak/AUC

Peak and AUC are computed per single trial because they're just a max and
a numeric integral -- robust to noise. Onset latency and decay tau involve
fitting a rise/fall shape, which single noisy dF/F trials generally don't
have enough SNR for. Compute onset latency and decay tau from
**trial-averaged PETHs** (per mouse x condition, e.g. per mouse x
reward/omission, or whatever grouping `run_age_comparison.py`'s FP1/FP2
per-mouse tables already use), not from individual trials. Keep peak/AUC
as they are (per-trial), and add onset/decay as a new per-mouse (or
per-mouse x condition) summary table.

## Definitions to implement (numbers are sensible defaults -- flag them
clearly as configurable constants, don't hardcode invisibly)

**Onset latency**: time from the aligned event (t=0) to when the
trial-averaged z-scored trace first reaches a fixed fraction of its own
peak amplitude within `metric_window_s` -- default **50% of peak**
(time-to-half-max), as a named constant (e.g. `ONSET_FRACTION = 0.5`) so
it's easy to change. Handle sign explicitly: since this is a *signed*
RPE-like deflection (rewards and omissions can go in opposite directions),
compute onset latency on the trace oriented so the response is positive
-- e.g. flip sign based on the mean direction of deflection for that
condition, or compute separately for reward and omission trials rather
than combining them. Do not take an absolute value of the whole trace
before finding the peak, since that would conflate a positive-going and
negative-going response.

**Decay time constant**: fit a single-exponential decay,
`z(t) = A * exp(-(t - t_peak) / tau) + offset`, to the trace from its peak
time to the end of `metric_window_s` (or until it returns to within some
tolerance of baseline, whichever is shorter), using
`scipy.optimize.curve_fit`. Report `tau` in seconds. Skip/NaN the fit
(don't force a bad fit) when: the post-peak segment is too short (fewer
than ~5-6 samples), the fit doesn't converge, or the fitted tau is
negative or implausibly large (e.g. > the window length) -- and report
what fraction of mouse x condition groups get skipped, don't silently drop
them.

## Where to put this

Add a new function in `alignment/windowing.py` (or a new
`alignment/kinetics.py` if that reads cleaner) --
`compute_onset_and_decay(mean_trace, peth_time, metric_window_s, onset_fraction=0.5)`
returning `(onset_latency_s, decay_tau_s, fit_r_squared)`. Then a
higher-level function that groups trials by mouse (and condition, if
applicable), averages their per-trial z-scored PETHs (reuse
`compute_event_aligned_zscore`'s output before the peak/AUC reduction --
you may need to expose the per-trial z-scored windows, not just the
reduced peak/AUC, as an intermediate return value), and calls
`compute_onset_and_decay` on each group's mean trace.

## Output

A per-mouse (x condition) table with columns for peak, AUC (existing),
onset_latency_s, decay_tau_s, and fit_r_squared (new) -- structured so it
slots into the same kind of per-mouse CSV that `run_age_comparison.py`
already reads (`outputs_fixed/rpe_analysis_pooled/results/...csv` style),
so an FP1-vs-FP2 (young vs old) comparison of onset latency and decay tau
can be added to `run_age_comparison.py` the same way the existing RPE
metrics are compared there (Mann-Whitney U, Cliff's delta, bootstrap CI
-- reuse `compare_metric`).

## Validation

Add a unit test with a synthetic exponential-decay trace of known tau and
known onset latency (construct it directly, don't reuse production code to
generate it) and assert the fitted values recover the true ones within a
reasonable tolerance. Also sanity-check on one or two real sessions that
onset_latency_s and decay_tau_s land in a plausible range (milliseconds to
low seconds, not negative or absurdly large) before trusting the full run.

## One thing to flag back to me, not decide silently

If the "average across trials, then fit" approach doesn't give clean
enough decay fits in practice (too few trials per mouse x condition, or
fits failing on a large fraction of groups), don't just relax the
definition quietly -- report the failure rate and what you tried, and
we'll decide together whether to pool across sessions, relax the
convergence criteria, or use a different fitting approach (e.g. fitting
the population-mean trace instead of per-mouse).
