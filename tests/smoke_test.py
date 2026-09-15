from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cyberlarva.connectome import ConnectomeBrain
from cyberlarva.world import LarvaWorld
from cyberlarva.physics import MuJoCoLarva

world=LarvaWorld();brain=ConnectomeBrain(ROOT/'data'/'connectome');physics=MuJoCoLarva(world,ROOT/'config'/'trajectory_calibration.json')
start=(world.x,world.y)
speeds=[];contacts=[]
for _ in range(100):
    neural=brain.step(world.senses())
    pose=physics.step(neural);world.sync_physics(pose,neural);speeds.append(pose['speed_bl_s']);contacts.append(pose['contact_count'])
assert brain.n==2952,brain.n
assert neural.source=='Winding L1 topology'
assert len(world.segments)==11
assert world.distance>0
assert pose['engine'].startswith('MuJoCo') and max(contacts)>0
assert 0<=neural.forward<=1 and -1<=neural.turn<=1
print({'neurons':brain.n,'connections':brain.W.nnz,'active':neural.active,'distance':round(world.distance,3),'speed_bl_s':round(sum(speeds)/len(speeds),3),'contacts':round(sum(contacts)/len(contacts),1),'engine':pose['engine'],'source':neural.source})
