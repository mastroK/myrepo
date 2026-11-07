# Phase 1 results: behavioral sufficiency test

Full run: `python scripts/run_phase1.py` (10 sessions x 150 trials x 16
animals/group; sticky Q-learning fit with 15 random restarts/session).
Raw outputs: `phase1_session_fits_{young,old}.csv`,
`phase1_kappa_comparison.csv`, `phase1_kappa_by_age.png`,
`phase1_robustness_report.txt`, `phase1_sweep_*.csv`.

## REOPENED (2026-11-06/07): SST->PV coupling added -- result substantially strengthened, not overturned

New finding reported for this reopening: the SST->PV IPSC's own kinetics
change with age -- the first ~50ms is age-invariant, but the longer/
sustained component of the evoked charge grows with age (confirmed point
estimates, average at midpoint stimulation: 0.25 in young -> 0.75 in old,
a ~3x change; max evoked charge unchanged, this is a kinetic/shape change).
This adds a previously-unmodeled pathway -- the model explicitly had NO
direct PV<->SST coupling in either direction before this. See
`sst_pv_model/params.py::SST_TO_PV_GAIN_YOUNG/OLD` and
`sst_pv_model/network.py` (new `s_sst_pv` state, `_pv_cross_net`) for the
full implementation, including two false starts documented in commit
history: an absolute-subtraction version that destabilized the circuit
(the recurrent self-excitation, w_self=2.0, overran the losing pool once
PV's divisive gain was eroded too far), and reusing the existing s_sst
state directly (rejected because s_sst is already ~78% built up by the
end of a 150ms stimulus epoch, which would have made the age-difference
appear immediately rather than after the reported ~50ms). The shipped
version uses a dedicated, slower state variable and a FRACTIONAL (not
absolute) discount on PV's cross-pool divisive reach.

**Before committing to the full-scale rerun, an isolated single-trial
mechanism probe (forced extreme win -> one ITI, no noise, no learning)
suggested the core mechanism might REVERSE at these confirmed values --
old's residual asymmetry went negative. That turned out to be a
misleading signal from an artificial probe, not a preview of the real
result** -- flagged here explicitly since it was reported to the user
as an open concern before the full pipeline was rerun.

### Headline result, before vs. after (single real-scale cohort, n=16/group)

| window | Cohen's d (before) | Cohen's d (after) | p after (t-test / MWU) |
|---|---|---|---|
| All sessions | +0.42 (n.s.) | **+0.87** | **0.020 / 0.048** |
| Early (0-4) | +0.21 (n.s.) | +0.54 | 0.136 / 0.207 (n.s.) |
| Late (5-9) | +0.46 (n.s.) | **+0.84** | **0.025 / 0.028** |

The direction did not reverse -- it roughly doubled in magnitude, and the
all-sessions and late-sessions windows are now individually significant
at a single cohort, which the pre-reopening model never achieved without
pooling 12 replications.

### Robustness sweep, before vs. after

Direction (young>old kappa) survival rate is unchanged or improved:
tau_PV 5/5 -> 5/5, tau_SST 5/5 -> 5/5, w_self 4/4 -> 4/4, noise_sigma
2/4 -> **3/4**. The new coupling does not make the result more fragile to
these four parameters.

### Replication/power study, before vs. after (now 15 independent cohorts, not 12)

| window | mean d (before, n=12) | mean d (after, n=15) | % correct direction (before -> after) | individually sig. (after) | Fisher's p (before -> after) |
|---|---|---|---|---|---|
| All sessions | +0.24 | **+0.95** | 67% -> **100%** | 14/15 (93%) | 0.019 -> **3.99e-19** |
| Early (0-4) | +0.29 | **+0.79** | 92% -> **100%** | 13/15 (87%) | 0.019 -> **6.58e-14** |
| Late (5-9) | +0.05 | **+0.57** | 50% -> **100%** | 5/15 (33%) | 0.073 (n.s.) -> **1.44e-08** |

**The late-session pattern from the original retraction (see below)
qualitatively persists even after this reopening**: late sessions still
have the lowest mean effect size and by far the lowest individual-
replication hit rate (33% vs. 93%/87%) of the three windows -- it is
still the least consistent window on a per-replication basis. What
changed is magnitude: the underlying effect is now large enough that even
the "weakest" window's *pooled* evidence is overwhelming. This does not
revive the originally-retracted late-session-specific claim (see
"Replication/power study" section below) -- early sessions are still
comparatively the more consistent window, just by less of a margin than
before.

### What this means

Treat the original "Headline result," "Robustness," and "Replication"
sections below as the **pre-reopening historical record** -- accurate for
the model as it stood before this new SST->PV finding, superseded (not
reversed) by the numbers above. The qualitative conclusion is the same
sufficiency claim as before, now on much firmer statistical ground; the
retraction of the late-session-specific claim (below) still stands on its
own terms and is not reopened by this update.

An open question raised during this reopening and not yet resolved: why
the isolated single-trial mechanism probe disagrees with the full
noisy/learning-coupled simulation at these parameter values. Worth
understanding before leaning on the isolated probe for future exploratory
predictions (see the per-manipulation exploration run this session,
scratch-only, not yet committed to the repo).

---

**This version uses real SST/PV fold-changes**, read off the saturating
plateau (~15 mW) of your SST-Cre;Ai32 / PV-Cre;Ai32 ChR2 charge (fC/pF)
dose-response curves: SST fold-change (old/young) ~0.73, PV fold-change
~1.4, ages 6-9wk (young) vs. 16-36wk (old). These are graph-read estimates,
not exact per-cell table values -- ask for the underlying table if tighter
precision is wanted. Both are milder than the placeholder values used in
the first pass (0.5 / 2.0), which matters for what follows: the model's
effect size shrinks with the real, smaller inhibitory contrast between
ages. See `sst_pv_model/params.py` for the full derivation and caveats.

## Headline result (PRE-REOPENING HISTORICAL RECORD -- see REOPENED section above for current numbers)

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

## Robustness / sensitivity sweep (Phase 1 step 5) -- weaker than before (PRE-REOPENING HISTORICAL RECORD)

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

## Replication/power study -- and a correction to the late-session claim above (PRE-REOPENING HISTORICAL RECORD; the retraction itself still stands)

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

## Mechanism check (regression-tested) -- REVISED 2026-11-07

Pre-reopening: after an identical "win" for one pool, followed by the same
inter-trial-interval, the young network retained more residual winner/
loser output asymmetry than the old network, with old's own asymmetry
staying positive (just smaller) -- a weaker version of the same effect.

**That no longer holds at the confirmed SST->PV coupling values.** Old's
residual asymmetry in this isolated probe is now NEGATIVE (the pool that
just lost ends up with higher output than the pool that just won) --
see `tests/test_network.py::test_young_retains_more_residual_asymmetry_than_old`,
updated to assert this directly. Young's result is unchanged.

**This isolated probe's reversal does NOT reflect what happens in the
full task** -- see the REOPENED section at the top: the actual behavioral
kappa effect got stronger, not weaker or reversed, once simulated with
realistic noise and trial-to-trial value learning. The isolated probe
(a single forced extreme win, no noise, no learning, full ITI relaxation)
is evidently not a reliable stand-in for the full multi-trial dynamics at
these parameter values -- why, specifically, is not yet understood and is
flagged as an open question, not resolved by picking a reassuring
explanation. Treat the isolated mechanism probe as a diagnostic for
circuit behavior under extreme conditions, not as a predictor of the
behavioral readout, until this discrepancy is understood.

## Inhibition-manipulation predictions (full scale, formalized 2026-11-07)

`python scripts/run_manipulations.py` (`sst_pv_model/manipulations.py`,
`tests/test_manipulations.py`) -- four named circuit-wide manipulations
(lower/higher total inhibition = g_pv, g_sst, g_sst_to_pv all scaled
together; PV-only; SST-only = both of SST's output pathways scaled
together), applied on top of each age's own baseline, at full scale (10
sessions x 150 trials x 16/group, 15 fit restarts, matching the headline
convention). Single cohort per scenario -- not replicated the way the
headline young-vs-old result is. Full output: `outputs/phase1_manipulations.csv`.

| Age | Manipulation | kappa (baseline -> manip) | diff | Cohen's d | p (t / MWU) |
|---|---|---|---|---|---|
| Young | Lower total inhibition | -0.208 -> -0.194 | +0.014 | +0.06 | 0.859 / 0.807 (n.s.) |
| Young | **Higher total inhibition** | -0.208 -> **+0.350** | **+0.558** | **+2.07** | **<0.0001 / <0.0001** |
| Young | Lower PV only | -0.208 -> -0.128 | +0.080 | +0.35 | 0.337 / 0.356 (n.s.) |
| Young | Lower SST only | -0.208 -> -0.133 | +0.075 | +0.33 | 0.359 / 0.440 (n.s.) |
| Old | **Lower total inhibition** | -0.352 -> **-0.101** | **+0.252** | **+1.20** | **0.002 / 0.001** |
| Old | Higher total inhibition | -0.352 -> -0.381 | -0.028 | -0.23 | 0.527 / 0.955 (n.s.) |
| Old | Lower PV only | -0.352 -> -0.328 | +0.025 | +0.11 | 0.752 / 0.806 (n.s.) |
| Old | Lower SST only | -0.352 -> -0.212 | +0.140 | +0.67 | 0.066 / 0.080 (trend) |

**Only 2 of 8 scenarios survive at full scale** -- and they are not the
same two a quick, reduced-scale (n=10, single seed) exploration had
suggested earlier the same day. **Corrections to that earlier exploration,
stated plainly:**

- "Higher total inhibition flips sign between ages" -- **partially wrong**.
  Young's increase is real and enormous (d=+2.07, about as bulletproof as
  an effect gets at this cohort size). Old's earlier-reported large
  *decrease* shrinks to a small, non-significant effect at full scale
  (d=-0.23) -- not a true sign flip, just "huge in young, negligible in
  old."
- "Lower total inhibition behaves similarly in both ages" -- **wrong**.
  This is actually the most age-asymmetric manipulation at full scale:
  null in young (d=+0.06, n.s.) but large and significant in old
  (d=+1.20, p=0.002).
- "SST alone is the single largest effect in young" -- **does not
  replicate**. Full-scale d=+0.33 (n.s.), much smaller than the reduced-
  scale exploration suggested; that earlier result was single-seed noise.
- "Lower PV matters in old" -- **does not replicate** (full-scale d=+0.11,
  n.s.).
- "PV alone barely matters in young" -- holds up directionally (small,
  non-significant either way), the one claim that survived.

**Honest takeaway**: at proper statistical power, this model makes two
clear, specific predictions -- raising total inhibition in a young-like
circuit sharply increases perseveration, and lowering total inhibition in
an old-like circuit sharply increases perseveration -- and is silent
(no significant prediction either way) on the other six scenarios tested,
including both PV-only and most SST-only manipulations. Single-seed
exploratory runs at reduced scale are not a reliable guide to this
model's predictions; several directional claims drawn from one this
session did not survive being run properly.

## Finer sweep around each age's baseline (reduced scale, 2026-11-07)

`python scripts/run_total_inhibition_sweep.py` (`sst_pv_model/manipulations.py::scale_total_inhibition`)
-- the two significant full-scale results above were each measured at a
single multiplier point (x0.5 or x1.5 of baseline gain). This asks the
natural follow-up: is each age's own baseline sitting at a true local
minimum of perseveration, with kappa rising smoothly and symmetrically in
both directions (a U-shape), or is there something sharper going on?
Swept 17 multiplier values (x0.2-x2.2) of total inhibition (g_pv, g_sst,
g_sst_to_pv scaled together) around each age's own baseline, at the
project's established reduced/sensitivity scale (n=8/group, 3 sessions x
100 trials, 8 fit restarts -- shape-mapping, not a confirmatory rerun).
Full output: `outputs/phase1_total_inhibition_sweep.csv`,
`outputs/phase1_total_inhibition_sweep.png`.

**Answer: neither a smooth symmetric U-shape nor a single clean threshold
-- the two directions look qualitatively different, and in both ages:**

- **x0.2-x1.4 (lower-to-moderately-higher inhibition):** kappa is flat and
  noisy around the baseline level, bouncing within roughly +/-0.4 kappa
  with no significant difference from baseline at ANY single point in this
  reduced-n sweep (best: old x0.3, d=+0.89, p=0.098, n.s.). This is
  consistent with the full-scale finding for old (lower total inhibition,
  d=+1.20, p=0.002) being a real but modest effect that needs the full
  n=16/group cohort to resolve point-by-point -- it is not dramatic enough
  to show up cleanly at n=8 at any single multiplier.
- There is a shallow, non-significant DIP (lowest kappa of the whole
  sweep) around **x1.2-1.3** in BOTH ages, i.e. slightly past each
  baseline toward more inhibition, not exactly at x1.0 -- but this is
  well within noise (d=-0.41 to -0.76, p=0.15-0.44) and should not be
  over-interpreted as a precise "true minimum" location without more
  animals.
- **Above roughly x1.4-1.5, kappa rises sharply and increasingly
  significantly in BOTH ages** -- not a gentle slope: d climbs from
  ~0.1-0.4 (n.s.) at x1.4-1.5 to d=+1.48 (p=0.01) at x1.7, d=+2.46
  (p=0.0002) at x2.0, and d=+2.90 (p<0.0001) at x2.2 in young; old shows
  the same pattern (d=+1.74 at x1.7, p=0.0037; d=+4.16 at x2.0,
  p<0.0001). Absolute kappa jumps from the -0.2 to -0.4 range at baseline
  to +1.1 to +2.7 by x2.0-2.2 -- a qualitative change in behavior
  (near-total perseveration), not a small shift.

**Interpretation**: the full-scale young result (higher total inhibition,
x1.5, d=+2.07) sits right at the edge of this steep high-inhibition
regime, which is consistent with how large and clean that effect was even
at a single cohort. The shape above x1.4 looks less like ordinary
parameter sensitivity and more like a shared (age-independent) dynamical
threshold -- plausibly the same runaway winner-take-all regime flagged
during model construction (`w_self=2.0` recurrent self-excitation
overrunning the losing pool once cross-inhibition is strong enough; see
`network.py` module docstring on the rejected absolute-subtraction
SST->PV implementation). The low-inhibition side, by contrast, shows no
such sharp feature in either age within the range swept -- whatever is
driving old's real lower-total-inhibition effect, it is a gentler, noisier
effect than the explosive high-inhibition transition, not its mirror
image. **Open question, not resolved here**: whether this high-inhibition
threshold is a genuine model prediction about circuit dynamics or an
artifact of `w_self` being an ASSUMED (not empirically-anchored) free
parameter -- worth a `w_self` cross-sweep before treating the x1.7-2.2
regime as biologically meaningful.

## w_self cross-sweep: is the high-inhibition threshold an artifact? (reduced scale, 2026-11-07)

`python scripts/run_w_self_threshold_crosssweep.py` -- re-ran the
total-inhibition multiplier sweep (focused on the x0.5-x2.3 transition
zone) at the same four `w_self` (recurrent self-excitation strength, an
ASSUMED free parameter) values `sensitivity.py` already sweeps (1.2, 1.5,
2.0, 2.5), for both ages, at reduced/sensitivity scale. Full output:
`outputs/phase1_w_self_threshold_crosssweep.csv`,
`outputs/phase1_w_self_threshold_crosssweep.png`.

**Answer: both things are true at once.**

- **The threshold itself is not an artifact of the specific `w_self=2.0`
  default** -- the same qualitative shape (flat/noisy below roughly
  x1.3-1.5, then a sharp rise to near-total perseveration) appears at
  EVERY `w_self` value tested, from 1.2 up to 2.5, in both ages. This is a
  robust feature of this winner-take-all architecture across a >2x range
  of the recurrent-excitation parameter, not a coincidence of one chosen
  setting.
- **But its exact onset location and steepness are NOT w_self-independent
  -- old shows this clearly and (mostly) monotonically**: the point where
  the effect first becomes large/significant (d>1, p<0.01) shifts
  progressively earlier as w_self increases -- around x1.9 for w_self=1.2
  (only reaches d=+1.70, p=0.004, at x1.7; weaker/later overall), x1.7 for
  w_self=1.5 (d=+5.07) and w_self=2.0 (d=+2.11), and as early as x1.5 for
  w_self=2.5 (d=+1.57, p=0.007). Young shows the same qualitative shape at
  every w_self but a noisier, less monotonic onset location (full-scale
  CI would be needed to pin this down more precisely at n=8/group).
- At the lowest tested w_self (1.2), the effect is both delayed and
  visibly blunted in BOTH ages compared to higher w_self -- the kappa
  curve stays closer to flat for longer and the final rise is smaller in
  magnitude (young never reaches significance anywhere in the x0.5-2.3
  range swept; old's largest d, +4.04 at x1.9, is still smaller than the
  d=+5-7 seen at w_self=1.5/2.5 at their own steepest points).

**Honest takeaway**: the explosive high-total-inhibition regime is a real,
qualitative prediction of this circuit's winner-take-all structure --
it's not something that only shows up because of one specific, arbitrary
choice of `w_self`. But the PRECISE multiplier at which it kicks in (e.g.
"around x1.5 in young") is NOT a `w_self`-independent number -- it moves
with this still-ASSUMED, not-empirically-anchored parameter, and a larger
real `w_self` would make the circuit tip into runaway perseveration at a
smaller inhibition increase than a smaller one would. Any claim about the
exact location of this threshold should be treated as contingent on
`w_self`, while the existence/direction of the effect (more total
inhibition eventually causes severe perseveration in both ages) looks
model-robust.

## What's still an open assumption

See `sst_pv_model/params.py::ASSUMED_PARAMETERS` for the full list
(interneuron time constants, trial/session counts, cohort size, block
length, activation function shape, network's internal learning rate). The
SST/PV fold-changes are now real (if graph-read); the biggest remaining
lever on magnitude is the real trial/session/cohort structure.
