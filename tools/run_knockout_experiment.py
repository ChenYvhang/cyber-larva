"""Paired control/knockout assay for the bilateral larval MDNa neurons."""
from __future__ import annotations

from pathlib import Path
import json
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cyberlarva.connectome import ConnectomeBrain
from cyberlarva.physics import MuJoCoLarva
from cyberlarva.world import LarvaWorld

MDNA_INDICES = [557, 845]
MDNA_IDS = ["18464581", "10728333"]
DT = 0.02
STEPS = 250
TOUCH_START = 50
TOUCH_END = 200


def trial(seed: int, knockout: bool) -> dict:
    world = LarvaWorld()
    brain = ConnectomeBrain(ROOT / "data" / "connectome", seed=seed)
    physics = MuJoCoLarva(world, ROOT / "config" / "trajectory_calibration.json")
    if knockout:
        brain.set_knockout(MDNA_INDICES)
    backward, forward, turn, speed, mdn_rate = [], [], [], [], []
    behavior_counts: dict[str, int] = {}
    for step in range(STEPS):
        senses = world.senses()
        stimulated = TOUCH_START <= step < TOUCH_END
        senses.update(touch=1.0 if stimulated else 0.0,
                      touch_lr=0.0, noci=0.2 if stimulated else 0.0)
        neural = brain.step(senses, DT)
        pose = physics.step(neural, DT)
        world.sync_physics(pose, neural, DT)
        if stimulated:
            backward.append(neural.backward); forward.append(neural.forward)
            turn.append(neural.turn); speed.append(pose["speed_bl_s"])
            mdn_rate.append(float(brain.rate[MDNA_INDICES].mean()))
            behavior_counts[world.behavior] = behavior_counts.get(world.behavior, 0) + 1
    return {
        "seed": seed,
        "knockout": knockout,
        "mean_backward_command": statistics.fmean(backward),
        "mean_forward_command": statistics.fmean(forward),
        "mean_abs_turn": statistics.fmean(abs(x) for x in turn),
        "mean_speed_bl_s": statistics.fmean(speed),
        "mean_mdna_rate": statistics.fmean(mdn_rate),
        "backward_behavior_fraction": behavior_counts.get("backward escape", 0) / len(backward),
        "distance_bl": world.distance,
    }


def summarize(rows: list[dict]) -> dict:
    metrics = [k for k in rows[0] if k not in {"seed", "knockout"}]
    result = {}
    for metric in metrics:
        control = [r[metric] for r in rows if not r["knockout"]]
        knockout = [r[metric] for r in rows if r["knockout"]]
        paired = [k - c for c, k in zip(control, knockout)]
        cmean, kmean = statistics.fmean(control), statistics.fmean(knockout)
        result[metric] = {
            "control_mean": cmean,
            "knockout_mean": kmean,
            "paired_difference": statistics.fmean(paired),
            "relative_change": None if abs(cmean) < 1e-12 else (kmean - cmean) / abs(cmean),
        }
    return result


def main():
    rows = []
    for seed in range(17, 37):
        rows.append(trial(seed, False))
        rows.append(trial(seed, True))
    report = {
        "experiment": "bilateral MDNa acute functional silencing",
        "neuron_ids": MDNA_IDS,
        "connectome_indices": MDNA_INDICES,
        "replicates": 20,
        "protocol": {"duration_s": STEPS * DT, "touch_start_s": TOUCH_START * DT,
                     "touch_end_s": TOUCH_END * DT, "paired_seeds": [17, 36]},
        "summary": summarize(rows),
        "trials": rows,
    }
    out = ROOT / "experiments" / "mdna_knockout_report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
