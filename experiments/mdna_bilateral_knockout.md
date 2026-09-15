# Bilateral MDNa virtual silencing experiment

## Biological expectation

Larval mooncrawler descending neurons (MDNs) promote backward locomotion while suppressing forward locomotion. Virtual Fly Brain identifies the L1 MDNa pair as skeleton `10728333` (left) and `18464581` (right), ontology class `FBbt_00048558`. Experimental silencing has been reported to suppress backward crawling in response to mild mechanical stimulation.

Sources: [Carreira-Rosario et al., 2018](https://elifesciences.org/articles/38554); [Virtual Fly Brain MDNa](https://www.virtualflybrain.org/blog/2022/01/01/larval-mooncrawler-descending-neuron-a-fbbt_00048558/).

## Protocol

- Targets: bilateral MDNa, connectome indices `845` and `557`.
- Intervention: acute functional silencing; membrane potential, spikes, and filtered rate clamped to zero.
- Design: 20 paired seeds, control and knockout initialized identically.
- Duration: 5 seconds per trial.
- Stimulus: symmetric anterior mechanical stimulus from 1–4 seconds.
- Runtime: Winding L1 topology, sparse LIF network, calibrated MuJoCo body.

## Result

| Metric during stimulus | Control | MDNa knockout | Change |
|---|---:|---:|---:|
| Backward command | 0.8100 | 0.8100 | 0.0% |
| Forward command | 0.1011 | 0.1011 | 0.0% |
| Absolute turn | 0.0192 | 0.0192 | 0.0% |
| Speed (BL/s) | 0.3589 | 0.3589 | 0.0% |
| Backward-behavior fraction | 1.0000 | 1.0000 | 0.0% |
| Distance (BL) | 3.5814 | 3.5814 | 0.0% |
| MDNa activity rate | 0.0000 | 0.0000 | — |

## Interpretation

The current model does **not** reproduce the reported MDNa loss-of-function phenotype. MDNa was already silent in every control trial, while backward drive was produced by the controller's direct touch-to-backward term. Silencing an already inactive node therefore could not change behavior.

This is a model-validation failure, not evidence against the biological result. Before repeating the assay, the model needs a documented mechanosensory-to-MDN pathway, transmitter signs, and an MDN-dependent backward readout. Those changes must be declared as literature-informed assumptions and validated independently rather than tuned solely to force this experiment positive.

Machine-readable results are in `mdna_knockout_report.json`; reproduce with:

```bash
python tools/run_knockout_experiment.py
```
