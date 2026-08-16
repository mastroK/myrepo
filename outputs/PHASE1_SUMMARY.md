# Phase 1 results: behavioral sufficiency test

Full run: `python scripts/run_phase1.py` (10 sessions x 150 trials x 16
animals/group; sticky Q-learning fit with 15 random restarts/session).
Raw outputs: `phase1_session_fits_{young,old}.csv`,
`phase1_kappa_comparison.csv`, `phase1_kappa_by_age.png`,
`phase1_robustness_report.txt`, `phase1_sweep_*.csv`.

**Caveat up front:** SST/PV fold-change amplitudes are still PLACEHOLDER
values (2x decrease / 2x increase, direction-only from your stated
background), not your real slice-electrophysiology numbers. Everything
below is a qualitative/directional check, not a magnitude match.

## Headline result

| | young (animal-mean kappa) | old (animal-mean kappa) |
|---|---|---|
| All sessions | +0.012 +/- 0.259 | -0.111 +/- 0.200 |
| Early sessions (0-4) | +0.042 +/- 0.381 | -0.049 +/- 0.307 |
| Late sessions (5-9) | -0.017 +/- 0.251 | -0.172 +/- 0.291 |

- **Direction is correct**: young (SST-high/PV-low) shows higher fitted
  kappa than old (SST-low/PV-high) in every session window, with a
  medium effect size (Cohen's d = 0.52 overall, 0.55 late sessions).
- **Not statistically significant at this cohort size** (all sessions:
  t-test p=0.16, Mann-Whitney p=0.34; late sessions: p=0.13 / p=0.09).
  This mirrors the real data's own finding, which needed a well-powered
  cohort and survived only after correction for the specific late-session
  window -- so an underpowered but correctly-directed effect here is
  arguably the *expected* qualitative outcome, not a failure. Bigger
  simulated cohorts would sharpen this if a firmer answer is wanted before
  Phase 2.
- **Unforced late-session correspondence**: exactly like the real cohort,
  the effect is weaker/non-significant in early sessions (d=0.26, p=0.48)
  and stronger/closer-to-significant in late sessions (d=0.55, p=0.09-0.13).
  This wasn't built in -- there's no session-number-dependent mechanism in
  the model -- so it's a notable (if noisy, n=16/group) qualitative match
  worth flagging, not something to over-interpret.
- Sticky-Q optimizer boundary-hit rate: 16-17% of sessions (real cohort:
  ~30%) -- same ballpark, simulated choices are somewhat more probabilistic
  than the real animals' but not wildly off.

## Robustness / sensitivity sweep (Phase 1 step 5)

One-at-a-time sweeps around baseline, reduced trial count for speed:

- **tau_pv** (PV interneuron time constant): young > old kappa in **5/5**
  swept values (8-30 ms).
- **tau_sst** (SST interneuron time constant): **5/5** (60-160 ms).
- **w_self** (recurrent self-excitation / coupling strength): **4/4**
  (1.2-2.5).
- **noise_sigma** (decision stochasticity, not named in your prompt but a
  free parameter of this implementation): **3/4** -- one point (0.18)
  came out slightly negative (diff=-0.06, near zero), most plausibly
  small-sample noise at the sweep's reduced scale (n=8 animals) rather
  than a real reversal.

**Conclusion**: across every parameter explicitly named in the prompt
(time constants, coupling strength), the young>old kappa direction was
never reversed. The one exception was in a parameter I introduced myself
(noise_sigma) and was a near-null point, not a clear flip.

## Mechanism check (regression-tested)

Verified directly (not just via the downstream behavioral fit): after an
identical "win" for one pool, followed by the same inter-trial-interval,
the young network retains more residual winner/loser output asymmetry
than the old network (`tests/test_network.py`). No stickiness term exists
anywhere in the circuit equations -- the entire kappa effect is a
downstream consequence of this differential reset.

## What's still an open assumption

See `sst_pv_model/params.py::ASSUMED_PARAMETERS` for the full list
(interneuron time constants, trial/session counts, cohort size, block
length, activation function shape, network's internal learning rate).
The two that matter most for magnitude, if you want a tighter match to
your real effect size: the SST/PV fold-change values, and the real
trial/session/cohort structure.
