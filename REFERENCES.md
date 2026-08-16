# References for the SST:PV network model construction

This documents which pieces of `sst_pv_model/` are grounded in published
literature, which are literature-typical-but-not-measured-here numbers, and
which are this project's own constructed hypothesis (i.e., the thing Phase
1/2 is actually testing, not something already shown elsewhere).

## Literature-validated design choices

**PV = fast/divisive (gain) inhibition, SST = slower/subtractive (shift)
inhibition** (`network.py`: `g_pv` divides the activation drive, `g_sst`
subtracts from it)
- Wilson NR, Runyan CA, Wang FL, Sur M (2012). "Division and subtraction by
  distinct cortical inhibitory networks in vivo." *Nature* 488:343-348.
  Direct in vivo demonstration in mouse visual cortex: soma-targeting PV
  interneurons divide (scale) excitatory responses and preserve selectivity;
  dendrite-targeting SST interneurons subtract from responses and sharpen
  selectivity. This is the core functional assumption behind `g_pv`/`g_sst`
  in the model.
  https://www.nature.com/articles/nature11347

**PV interneurons have faster synaptic/decay kinetics than SST; PV targets
perisomatic domains, SST targets dendrites** (`params.py`: `tau_pv` <
`tau_sst`)
- Kinetics and Connectivity Properties of Parvalbumin- and
  Somatostatin-Positive Inhibition in Layer 2/3 Medial Entorhinal Cortex.
  *eNeuro* 9(1), 2022. PV-PV synapses show smaller decay time constants and
  shorter delays than SST-related synapses.
  https://www.eneuro.org/content/9/1/ENEURO.0441-21.2022
- Dendrite-targeting interneurons control synaptic NMDA-receptor activation
  via nonlinear alpha5-GABA-A receptors. *Nat Commun* 9, 3576 (2018).
  Dendrite-targeting SST interneurons generate slow, alpha5-GABA-A-mediated
  IPSCs; perisomatic PV-mediated IPSCs show negligible alpha5 contribution
  (i.e., faster, different receptor composition).
  https://www.nature.com/articles/s41467-018-06004-8

**SST interneurons inhibit PV interneurons; the reverse (PV->SST) is
comparatively weak/sparse** (relevant to what the model does NOT include --
see caveat below)
- Pfeffer CK, Xue M, He M, Huang ZJ, Scanziani M (2013). "Inhibition of
  inhibition in visual cortex: the logic of connections between molecularly
  distinct interneurons." *Nat Neurosci* 16:1068-1076. Established that
  Martinotti (SST) cells make systematic synapses onto PV basket cells
  (and VIP cells), while PV cells' output is comparatively restricted to
  pyramidal cells and other PV cells -- an asymmetric interneuron-interneuron
  connectivity motif.
  https://www.nature.com/articles/nn.3446

**Competing-pools / winner-take-all decision circuit architecture**
(two excitatory pools + shared feedback inhibition -> attractor-like choice
dynamics; `network.py`'s overall structure)
- Wang XJ (2002). "Probabilistic Decision Making by Slow Reverberation in
  Cortical Circuits." *Neuron* 36:955-968. The canonical reference for this
  class of model: two mutually-competing excitatory pools with strong
  recurrent excitation, competing via shared inhibition, producing
  attractor-like binary decisions.
  https://www.cns.nyu.edu/wanglab/publications/pdf/wang2002_decision.pdf

**Rate-model (firing-rate) formalism itself**
- Wilson HR, Cowan JD (1972). "Excitatory and inhibitory interactions in
  localized populations of model neurons." *Biophysical Journal* 12:1-24.
  Foundational reference for the Wilson-Cowan-style dynamics used throughout
  `network.py`.

## Important caveat: what is NOT in the model (yet)

The model has **no direct PV<->SST synaptic connection in either
direction** -- each interneuron population is driven only by its own local
excitatory pool and projects only onto the *competing* excitatory pool.
This sidesteps the Pfeffer et al. asymmetry question entirely for Phase
1/2. If interneuron-interneuron coupling is ever added (e.g., for a more
biophysically complete model beyond this sufficiency test), it should be
asymmetric (SST->PV only) per Pfeffer et al. 2013, not bidirectional. Your
original Phase 3 spec already anticipated this by explicitly requiring "no
interneuron-interneuron coupling" for the VGAT summation check.

## Additional experimental findings you shared, and how they were handled

Beyond the ChR2-isolated output-synapse data used to set `g_pv`/`g_sst`,
you described three more findings from electrical-stimulation slice
recordings, none of which are yet built into the model, along with the
reasoning for that choice:

- **Feedforward EPSC onto pyramidal cells declines with age**, and
  **feedforward IPSC onto pyramidal cells (compound, disynaptic) also
  declines with age.** The compound IPSC result is exactly the kind of
  composite/ambiguous signal your original framing (Phase 3's motivation)
  was already wary of: taken alone it would suggest "inhibition weakens
  with age," which is not what the isolated PV/SST ChR2 data show (PV
  output strengthens, SST output weakens). It's plausibly explained by
  reduced excitatory drive reaching the interneurons in the first place,
  which is a different quantity than output synapse strength and does not
  contaminate the ChR2 measurements (ChR2 depolarizes the interneuron
  directly, bypassing its synaptic input entirely).
- **Feedforward EPSC onto PV cells specifically declines with age**
  (recorded directly from PV cells, so cell-type-specific, not a
  composite signal). This says PV cells receive less excitatory synaptic
  drive with age.
- **PV cells' intrinsic excitability increases with age.** This pulls in
  the opposite direction from the EPSC finding above: less synaptic drive,
  but each unit of drive is more likely to make the cell fire. Net effect
  on PV recruitment is therefore ambiguous without matched quantitative
  magnitudes for both -- they could partially or fully offset.

**Decision (explicit, by request)**: keep the model simple for now.
`network.py`'s `s_pv`/`s_sst` are driven by the local excitatory pool with
a fixed, age-invariant coupling; only the ChR2-derived output-side
`g_pv`/`g_sst` scale with age. This is treated as a considered
simplification motivated by the plausible EPSC-vs-excitability offset
above, not as evidence those two effects don't matter -- revisit if
matched quantitative magnitudes for both become available (and/or an
SST-cell excitability equivalent, which hasn't been reported).

## What is NOT literature-validated -- this project's own hypothesis

The specific causal chain this sufficiency test is built around --
**SST/PV kinetic and gain-type asymmetry -> incomplete inter-trial reset of
residual pool activity -> behavioral perseveration** -- is this project's
own mechanistic construction, not a finding reported in any of the papers
above or elsewhere as far as I know. Each individual piece (PV
divisive/fast, SST subtractive/slow, competing-pools decision circuits,
slow-timescale memory/history effects in attractor networks generally) is
independently grounded; the specific combination and its behavioral
consequence is the hypothesis Phase 1 is testing, not a premise borrowed
from prior work. Treat Phase 1's result accordingly: a demonstration that
this construction is *sufficient* to produce the right qualitative
behavior, not a claim that this is how the real circuit is known to work.
