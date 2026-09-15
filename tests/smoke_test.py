from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cyberlarva.connectome import ConnectomeBrain
from cyberlarva.world import LarvaWorld
from cyberlarva.physics import MuJoCoLarva

world=LarvaWorld();brain=ConnectomeBrain(ROOT/'data'/'connectome');physics=MuJoCoLarva(world,ROOT/'config'/'trajectory_calibration.json')
target=int(brain.forward_dn[0]);brain.set_knockout([target])
start=(world.x,world.y)
speeds=[];contacts=[];gap_ratios=[]
for _ in range(100):
    neural=brain.step(world.senses())
    pose=physics.step(neural);world.sync_physics(pose,neural);speeds.append(pose['speed_bl_s']);contacts.append(pose['contact_count']);gap_ratios.extend(pose['axial_gap_ratio'])
assert brain.n==2952,brain.n
assert neural.source=='Winding L1 topology'
assert len(world.segments)==11
assert world.distance>0
assert pose['engine'].startswith('MuJoCo') and max(contacts)>0
assert min(gap_ratios)<.82,(min(gap_ratios),max(gap_ratios))
assert 0<=neural.forward<=1 and -1<=neural.turn<=1
assert neural.knockout_count==1 and brain.disabled[target]
assert brain.v[target]==0 and brain.rate[target]==0 and brain.last_spikes[target]==0
assert brain.neuron_catalog(str(brain.neurons[target]['id']),10)
assert len(brain.neuron_catalog('MDNa',10))==2
brain.set_knockout([], 'set');assert not brain.disabled.any()
# Eating is a world mutation, so the server can invalidate the rendered item layer.
food=next(i for i in world.items if i.kind=='food');feeding_pose=pose|{'x':food.x,'y':food.y}
assert world.sync_physics(feeding_pose,neural) is True and food not in world.items
print({'neurons':brain.n,'connections':brain.W.nnz,'active':neural.active,'distance':round(world.distance,3),'speed_bl_s':round(sum(speeds)/len(speeds),3),'contacts':round(sum(contacts)/len(contacts),1),'engine':pose['engine'],'source':neural.source})
