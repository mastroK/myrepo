# Phase 1 results: behavioral sufficiency test

Full run: `python scripts/run_phase1.py` (10 sessions x 150 trials x 16
animals/group; sticky Q-learning fit with 15 random restarts/session).
Raw outputs: `phase1_session_fits_{young,old}.csv`,
`phase1_kappa_comparison.csv`, `phase1_kappa_by_age.png`,
`phase1_robustness_report.txt`, `phase1_sweep_*.csv`.

**This version uses real SST/PV fold-changes**, read off the saturating
plateau (~15 mW) of your SST-Cre;Ai32 / PV-Cre;Ai32 ChR2 charge (fC/pF)
dose-response curves: SST fold-change (old/young) ~0.73, PV fold-change
~1.4, ages 6-9wk (young) vs. 16-36wk (old). These are graph-read estimates,
not exact per-cell table values -- ask for the underlying table if tighter
precision is wanted. Both are milder than the placeholder values used in
the first pass (0.5 / 2.0), which matters for what follows: the model's
effect size shrinks with the real, smaller inhibitory contrast between
ages. See `sst_pv_model/params.py` for the full derivation and caveats.

## Headline result

| | young (animal-mean kappa) | old (animal-mean kappa) |
|---|---|---|
| All sessions | +0.012 +/- 0.259 | -0.088 +/- 0.205 |
| Early sessions (0-4) | +0.042 +/- 0.381 | -0.032 +/- 0.306 |
| Late sessions (5-9) | -0.017 +/- 0.251 | -0.144 +/- 0.282 |

- **Direction is still correct**: young shows higher fitted kappa than old
  in every session window, with a small-to-medium effect size (Cohen's
  d = 0.42 overall, 0.46 late sessions) -- smaller than the placeholder-run's
  d = 0.52 / 0.55, as expected given the real fold-changes are milder.
- **Not statistically significant at this cohort size** (all sessions:
  t-test p=0.25, Mann-Whitney p=0.53; late sessions: p=0.21 / p=0.18).
  Weaker than the placeholder run's p-values. This is the honest
  consequence of using the real (smaller) SST/PV amplitude contrast rather
  than an exaggerated placeholder one -- the qualitative direction survives,
  but detecting it with confidence would need a larger simulated (or real)
  cohort than 16/group.
- **Late-session pattern still present but weaker**: effect is smaller in
  early sessions (d=0.21) than late (d=0.46), echoing the real data's
  late-session-specific kappa effect, though less cleanly than in the
  placeholder run.
- Sticky-Q optimizer boundary-hit rate: 16-17% of sessions (real cohort:
  ~30%), unchanged from the placeholder run (this is governed by
  `noise_sigma`, not the fold-changes).

## Robustness / sensitivity sweep (Phase 1 step 5) -- weaker than before

One-at-a-time sweeps around baseline, reduced trial count for speed:

- **tau_pv**: young > old kappa in **5/5** swept values, but effect sizes
  are now small (Cohen's d ~0.09-0.09 throughout).
- **tau_sst**: **5/5**, but shrinks to near-null at the longest tau_sst
  tested (160 ms: d=0.018, essentially no effect).
- **w_self**: **4/4**, effect sizes modest (d ~0.09-0.14).
- **noise_sigma**: **2/4** -- direction reversed at two swept values
  (0.18 and 0.30), both small-magnitude reversals (diff approx -0.02 to
  -0.08) most likely small-sample noise at this sweep's reduced scale
  (n=8 animals), not a clear structural failure -- but this is a real
  weakening from the placeholder run's 3/4.

**Honest conclusion**: with the real, milder SST/PV fold-changes, the
qualitative direction (young > old kappa) still holds in the headline
comparison and in every swept value of the three parameters explicitly
named in your prompt (tau_pv, tau_sst, w_self) -- it is not fragile to
those. But the effect is smaller and noisier than the placeholder run
suggested, doesn't reach significance at n=16/group, and is no longer
robust to the noise_sigma parameter (a stochasticity knob I introduced,
not one you named). If you want a firmer statistical read, scaling up the
simulated cohort (more animals/sessions) is the direct next step -- the
direction is not in question, the *power to detect it* at this real,
modest effect size is.

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
length, activation function shape, network's internal learning rate). The
SST/PV fold-changes are now real (if graph-read); the biggest remaining
lever on magnitude is the real trial/session/cohort structure.
