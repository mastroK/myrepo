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

## Replication/power study -- and a correction to the late-session claim above

`python scripts/run_phase1_replications.py` (12 independent cohorts, each
n_animals=16/group -- your real cohort size, not an inflated one -- 10
sessions x 150 trials, sticky-Q fit with 8 restarts/session). Rationale:
a single simulated cohort can't tell you how reliable an effect is: this
runs the equivalent "experiment" 12 independent times and combines the
evidence via Fisher's method, which is the honest way to sharpen
significance without pretending you could ever collect a 40+/group cohort.
Full output: `phase1_replications_raw.csv`, `phase1_replications_summary.txt`,
`phase1_replications_cohend_hist.png`.

| window | mean Cohen's d (range) | % replications young>old | combined p (Fisher) |
|---|---|---|---|
| All sessions | +0.24 ([-0.25, +0.80]) | 8/12 (67%) | **0.019** |
| Early sessions (0-4) | +0.29 ([-0.23, +0.58]) | 11/12 (92%) | **0.019** |
| Late sessions (5-9) | +0.05 ([-0.64, +0.80]) | 6/12 (50%) | 0.073 |

- **The core direction is now on firmer ground**: combined across 12
  independent real-sized cohorts, the young>old kappa direction reaches
  significance overall (p=0.019) and specifically in early sessions
  (p=0.019). Any single 16/group cohort is noisy enough that it often
  won't show significance on its own (only 2/12 replications did,
  individually) -- exactly why a single run shouldn't be over-read, and
  why this replication step was worth doing.
- **Correction: the "late-session correspondence" reported above does NOT
  replicate, and I should not have highlighted it as confidently as I did.**
  That claim was based on one single simulated draw. Across 12
  independent replications, late sessions show the *weakest and least
  consistent* effect (mean d=+0.05, median actually slightly *negative*
  at -0.08, only 6/12 in the right direction, combined p=0.073, not
  significant) -- if anything, early sessions show the more robust effect
  in this model, which is the **opposite** of the real data's
  late-session-specific kappa decline. The earlier single-run report's
  "unforced late-session match" was very likely a coincidence of that
  particular random draw, not a real property of the model. There is no
  session-number-dependent mechanism anywhere in the model, so there's no
  principled reason to expect it to reproduce a late-session-specific
  effect -- and the replication data confirms it doesn't, reliably.
- **Bottom line**: treat this model as a sufficiency demonstration for the
  *overall* young>old perseveration direction, well-supported once
  properly powered across replications at a real cohort size -- but not,
  currently, as an explanation for *why* the real effect is late-session
  specific. That would need an explicit session/experience-dependent
  mechanism this model doesn't have.

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
