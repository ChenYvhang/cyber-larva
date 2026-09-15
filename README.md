# CyberLarva

An interactive, closed-loop embodied model of a *Drosophila melanogaster* larva. A sparse neural simulation constrained by the Winding et al. L1 connectome receives environmental sensory signals, modulates a segmental ventral-nerve-cord controller, and drives an 11-segment MuJoCo neuromechanical body in a 3D editable habitat.

## What is real—and what is modeled

- **Measured prior:** neuron identities, directed topology and synapse-count priors from Winding et al. (2023).
- **Model assumptions:** LIF membrane dynamics, inferred excitatory/inhibitory signs, sensory gain and DN readout.
- **Physics:** MuJoCo resolves axial and lateral muscle actuators, inertia, flexible joints, substrate friction, denticle anchoring and obstacle contacts at a 1 ms step.
- **Functional abstraction:** the segmental VNC oscillator, inferred muscle readout and mouth-hook traction controller.
- **Not claimed:** a biological emulation or a complete measured brain-to-muscle connectome.

The interface keeps these layers visible because scientific provenance matters more than a misleading “digital brain” label.

## 3D larva

The renderer uses a continuous 41-ring, 32-sided deforming cuticle rather than visible physics capsules. Its silhouette is reconstructed from the *D. melanogaster* panel of the supplied photographic reference: a narrow dark anterior, fuller middle, blunt posterior, shallow intersegmental folds, translucent tissue, internal cephalopharyngeal hooks and paired posterior spiracles. The surface is resampled every frame over the 11 MuJoCo bodies, so head casts and peristaltic contractions deform one unbroken animal.

An editable rest-pose asset is included at `assets/drosophila-melanogaster-larva.glb`. Rebuild it with `node tools/export-larva-glb.mjs`; provenance and the limits of the multi-species reference are documented in `assets/MODEL-SOURCE.md`.

## Run

On Windows, double-click `start.cmd`, or run:

```bash
python server.py
```

Then open <http://127.0.0.1:8775>. `start.cmd` automatically uses the project-local virtual environment when present. The first launch uses a deterministic 512-neuron fallback unless the public connectome pack has been prepared.

Install the physics dependencies into the local environment with:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Prepare the Winding L1 topology

Download `Supplementary-Data-S1.zip` from [brain-networks/larval-drosophila-connectome](https://github.com/brain-networks/larval-drosophila-connectome), extract it, then run:

```bash
python tools/prepare_connectome.py PATH/TO/Supplementary-Data-S1
```

This generates a compact sparse matrix and annotated sensory/DN index groups under `data/connectome/`. The source repository republishes manuscript supplementary data but does not currently declare a software/data license; therefore the raw files are not redistributed by this project.

## Empirical trajectory calibration

`tools/calibrate_tracks.py` reads the 12-point spine tracks published in the Schleyer dataset and derives body-length-normalized targets. The checked calibration used eight real larvae comprising 829.75 seconds of valid, collision-free tracking:

- body length: 4.19 mm median
- crawling frequency: 1.41 Hz
- median / 95th-percentile speed: 0.300 / 0.640 body-lengths per second
- turning curvature: 1.06 rad per body-length during turns
- head-cast rate and median amplitude: 0.111 Hz and 39.0 degrees

These values live in `config/trajectory_calibration.json`; per-animal results and provenance are retained. Raw tracks remain under their CC BY-NC-SA 4.0 license and are not redistributed.

Run `python tools/validate_calibration.py` after changing physics parameters. It writes `calibration-report.json` and fails when speed, curvature or substrate-contact errors exceed the documented tolerance.

## Current closed loop

1. Bilateral head sensors sample odor; head and body report contact and stretch.
2. Sensory populations receive modality-specific input in a sparse LIF network.
3. activity of the DN-VNC population modulates forward/backward drive, steering and head casting.
4. A calibrated segmental VNC oscillator produces a posterior-to-anterior axial contraction wave and phase-locked lateral bending.
5. Paired axial/hinge actuators deform the 11-segment MuJoCo body; ventral pads and mouth hooks exchange real forces with the substrate.
6. MuJoCo contact, body stretch and pose return to the sensory encoder.

## Scientific references

- Winding, M. et al. (2023). *The connectome of an insect brain*. Science 379, eadd9330. https://doi.org/10.1126/science.add9330
- Zarin, A. A. et al. (2019). *A multilayer circuit architecture for the generation of distinct locomotor behaviors in Drosophila*. eLife 8:e51781.
- Sakagiannis, P. et al. Larvaworld, an open behavioral simulation and analysis platform: https://github.com/nawrotlab/larvaworld
- Thoener, J. & Schleyer, M. (2021). *Locomotion of naive Drosophila larvae*. G-Node. https://doi.org/10.12751/g-node.5e1ifd

## License

Code is MIT licensed. Third-party data retain their original terms and citations.
