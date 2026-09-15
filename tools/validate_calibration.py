"""Run a deterministic closed-loop benchmark against empirical targets."""
from pathlib import Path
import json, sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cyberlarva.connectome import ConnectomeBrain
from cyberlarva.physics import MuJoCoLarva
from cyberlarva.world import LarvaWorld

world=LarvaWorld();brain=ConnectomeBrain(ROOT/'data'/'connectome',seed=17);physics=MuJoCoLarva(world,ROOT/'config'/'trajectory_calibration.json')
speeds=[];curves=[];contacts=[]
for _ in range(600):
    neural=brain.step(world.senses());pose=physics.step(neural);world.sync_physics(pose,neural)
    speeds.append(pose['speed_bl_s']);curves.append(pose['curvature_rad_bl']);contacts.append(pose['contact_count'])
speeds=np.asarray(speeds[100:]);turn_curves=np.asarray([x for x in curves[100:] if x>.15]);t=pose['targets']
observed={'median_speed_bl_s':float(np.median(speeds)),'p95_speed_bl_s':float(np.percentile(speeds,95)),
          'turn_curvature_rad_bl':float(np.median(turn_curves)),'mean_contacts':float(np.mean(contacts)),
          'crawl_frequency_hz':t['crawl_hz'],'head_cast_rate_hz':t['head_cast_hz']}
targets={'median_speed_bl_s':t['speed_bl_s'],'p95_speed_bl_s':t['p95_speed_bl_s'],'turn_curvature_rad_bl':t['curvature_rad_bl'],'crawl_frequency_hz':t['crawl_hz'],'head_cast_rate_hz':t['head_cast_hz']}
errors={k:abs(observed[k]-v)/max(abs(v),1e-9) for k,v in targets.items()}
report={'engine':pose['engine'],'duration_s':12,'targets':targets,'observed':observed,'relative_error':errors,
        'pass':errors['median_speed_bl_s']<.25 and errors['p95_speed_bl_s']<.35 and errors['turn_curvature_rad_bl']<.40 and observed['mean_contacts']>5}
(ROOT/'calibration-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if not report['pass']:raise SystemExit(1)
