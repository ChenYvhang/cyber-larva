"""MuJoCo neuromechanical larva with segment muscles and substrate contact."""
from __future__ import annotations
from pathlib import Path
import json, math
import numpy as np
import mujoco

WORLD_M = .02
BODY_LENGTH_M = .04
N_SEGMENTS = 11
SEGMENT_STEP = BODY_LENGTH_M / N_SEGMENTS


class MuJoCoLarva:
    """11 hydrostatic proxies coupled by axial and lateral actuators.

    MuJoCo resolves inertia, constraints, contacts and actuator force. Denticle
    and mouth-hook traction is represented by phase-dependent ventral friction;
    the body is never teleported to an animation pose.
    """
    def __init__(self, world, calibration_path: Path):
        cfg=json.loads(calibration_path.read_text(encoding='utf-8'))
        e=cfg['empirical']
        self.targets={'speed_bl_s':e['median_speed_bl_s'],'p95_speed_bl_s':e['p95_speed_bl_s'],
                      'crawl_hz':e['crawl_frequency_hz'],'bend_hz':e['bend_frequency_hz'],
                      'curvature_rad_bl':e['turn_curvature_rad_bl'],'head_cast_hz':e['head_cast_rate_hz'],
                      'head_cast_deg':e['head_cast_angle_deg']}
        self.phase=0.;self.bend_phase=0.;self.time=0.;self.last_xy=np.array([world.x,world.y])*WORLD_M;self.last_heading=world.heading
        self.muscles=np.zeros(N_SEGMENTS);self.current_speed=0.;self.current_curvature=0.
        self.model=mujoco.MjModel.from_xml_string(self._xml(world))
        self.data=mujoco.MjData(self.model);mujoco.mj_forward(self.model,self.data)
        self.axial=[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_ACTUATOR,f'axial{i}') for i in range(1,N_SEGMENTS)]
        self.bend=[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_ACTUATOR,f'bend{i}') for i in range(1,N_SEGMENTS)]
        self.pads=[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_GEOM,f'pad{i}') for i in range(N_SEGMENTS)]
        self.bodies=[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_BODY,f'segment{i}') for i in range(N_SEGMENTS)]
        self.root=self.bodies[0];self.mass=float(np.sum(self.model.body_mass[self.bodies]));self._settle()

    def _xml(self, world):
        radii=[.00245+.00065*math.sin(math.pi*i/(N_SEGMENTS-1)) for i in range(N_SEGMENTS)]
        x,y=world.x*WORLD_M,world.y*WORLD_M;q=f'{math.cos(world.heading/2)} 0 0 {math.sin(world.heading/2)}'
        obstacles=[]
        for n,it in enumerate(world.items):
            if it.kind=='rock':obstacles.append(f'<geom name="obstacle{n}" type="cylinder" pos="{it.x*WORLD_M} {it.y*WORLD_M} {it.radius*WORLD_M*.45}" size="{it.radius*WORLD_M} {it.radius*WORLD_M*.45}" contype="2" conaffinity="1" friction="1.4 .01 .001"/>')
        wx,wy=world.width*WORLD_M,world.height*WORLD_M
        obstacles += [f'<geom type="box" pos="{wx/2} 0 .006" size="{wx/2} .004 .006" contype="2" conaffinity="1"/>',f'<geom type="box" pos="{wx/2} {wy} .006" size="{wx/2} .004 .006" contype="2" conaffinity="1"/>',f'<geom type="box" pos="0 {wy/2} .006" size=".004 {wy/2} .006" contype="2" conaffinity="1"/>',f'<geom type="box" pos="{wx} {wy/2} .006" size=".004 {wy/2} .006" contype="2" conaffinity="1"/>']
        def body(i):
            r=radii[i];half=SEGMENT_STEP*.47
            joints='' if i==0 else f'<joint name="slide{i}" type="slide" axis="1 0 0" range="-.00105 .0003" damping=".025"/><joint name="bend{i}" type="hinge" axis="0 0 1" range="-.75 .75" damping=".000025" stiffness=".00008"/>'
            free='<freejoint/>' if i==0 else '';pos=f'{x} {y} {r+.00015}' if i==0 else f'{-SEGMENT_STEP} 0 0';quat=f' quat="{q}"' if i==0 else '';child=body(i+1) if i+1<N_SEGMENTS else ''
            return f'''<body name="segment{i}" pos="{pos}"{quat}>{free}{joints}<geom name="shell{i}" type="capsule" fromto="{-half} 0 0 {half} 0 0" size="{r}" density="960" contype="1" conaffinity="2" friction=".8 .004 .0002"/><geom name="pad{i}" type="ellipsoid" pos="0 0 {-r*.73}" size="{half*.72} {r*.7} {r*.22}" density="40" contype="1" conaffinity="2" friction="1.2 .008 .0003"/>{child}</body>'''
        actuators=[]
        for i in range(1,N_SEGMENTS):actuators += [f'<position name="axial{i}" joint="slide{i}" kp="1.8" kv=".045" ctrlrange="-.00105 .0003"/>',f'<position name="bend{i}" joint="bend{i}" kp=".0007" kv=".00004" ctrlrange="-.7 .7"/>']
        return f'''<mujoco model="cyberlarva"><compiler angle="radian" autolimits="true"/><option timestep=".001" gravity="0 0 -9.81" integrator="implicitfast" solver="Newton" iterations="50"/><size njmax="3000" nconmax="500"/><default><geom solref=".008 1" solimp=".92 .99 .002"/></default><worldbody><geom name="substrate" type="plane" size="1 1 .01" contype="2" conaffinity="1" friction="1.15 .006 .0004"/>{''.join(obstacles)}{body(0)}</worldbody><actuator>{''.join(actuators)}</actuator></mujoco>'''

    def _settle(self):
        for _ in range(80):mujoco.mj_step(self.model,self.data)

    @staticmethod
    def _wrap(a):return (a+math.pi)%(2*math.pi)-math.pi

    def step(self, neural, dt=.02):
        crawl_hz=self.targets['crawl_hz']*(.82+.28*neural.forward);direction=-1 if neural.backward>neural.forward else 1
        self.phase=(self.phase+direction*2*math.pi*crawl_hz*dt)%(2*math.pi);self.bend_phase=(self.bend_phase+2*math.pi*self.targets['bend_hz']*dt)%(2*math.pi)
        delta=self._wrap(self.phase-2.05);relief=.46+.54*math.exp(-delta*delta/2);drive=max(neural.forward,neural.backward)
        cast_period=1/max(self.targets['head_cast_hz'],.03);cast_age=self.time%cast_period;cast_duration=1.05
        cast_envelope=math.sin(math.pi*cast_age/cast_duration) if cast_age<cast_duration else 0.;cast_sign=-1 if int(self.time/cast_period)%2 else 1
        for i in range(1,N_SEGMENTS):
            # A smooth, broad posterior-to-anterior pulse makes shortening
            # continuous instead of snapping between contracted/rest states.
            wave=max(0.,math.sin(self.phase+i*.66))**1.35*drive;self.muscles[i]=wave;self.data.ctrl[self.axial[i-1]]=-.0010*wave
            head_weight=math.exp(-(i-1)*.28);target=(neural.turn*.82+math.sin(self.bend_phase+i*.13)*neural.head_sweep*.10+cast_sign*cast_envelope*neural.head_sweep*.40)*head_weight*relief
            self.data.ctrl[self.bend[i-1]]=float(np.clip(target,-.7,.7))
        self.muscles[0]=max(0.,math.sin(self.phase))*drive
        for i,gid in enumerate(self.pads):self.model.geom_friction[gid,0]=.45+2.7*max(0.,math.sin(self.phase+i*.66+1.25))
        for _ in range(round(dt/self.model.opt.timestep)):
            head=self.data.xpos[self.root];nxt=self.data.xpos[self.bodies[1]];axis=head[:2]-nxt[:2];axis/=max(np.linalg.norm(axis),1e-9)
            vel=self.data.qvel[:2];along=float(vel@axis);target=(neural.forward-neural.backward*.7)*self.targets['speed_bl_s']*BODY_LENGTH_M*7.0
            force=np.clip(self.mass*(target-along)*120,-.004,.004);self.data.xfrc_applied.fill(0)
            for i,bid in enumerate(self.bodies):
                anchor=.35+.65*max(0.,math.sin(self.phase+i*.66+1.25));self.data.xfrc_applied[bid,:2]=axis*force*anchor/2
            mujoco.mj_step(self.model,self.data)
        self.time+=dt;return self.pose()

    def pose(self):
        points=np.asarray([self.data.xpos[b].copy() for b in self.bodies]);rendered=points/WORLD_M;axis=points[0,:2]-points[1,:2];heading=math.atan2(axis[1],axis[0]);xy=points[0,:2];delta=xy-self.last_xy;self.last_xy=xy.copy()
        self.current_speed=float(np.linalg.norm(self.data.qvel[:2])/BODY_LENGTH_M);angles=[]
        for i in range(1,N_SEGMENTS):
            qid=mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,f'bend{i}');angles.append(float(self.data.qpos[self.model.jnt_qposadr[qid]]))
        travel=float(np.linalg.norm(delta)/BODY_LENGTH_M);self.current_curvature=abs(self._wrap(heading-self.last_heading))/travel if travel>.002 else 0.;self.last_heading=heading
        contacts=[]
        for c in self.data.contact[:self.data.ncon]:
            n1=mujoco.mj_id2name(self.model,mujoco.mjtObj.mjOBJ_GEOM,c.geom1) or '';n2=mujoco.mj_id2name(self.model,mujoco.mjtObj.mjOBJ_GEOM,c.geom2) or ''
            if 'obstacle' in n1+n2:contacts.append('obstacle')
        radii=[.1225+.0325*math.sin(math.pi*i/(N_SEGMENTS-1)) for i in range(N_SEGMENTS)]
        segments=[{'x':float(p[0]),'y':float(p[1]),'z':float(max(p[2],.001)),'radius':r,'muscle':float(self.muscles[i]),'angle':angles[i-1] if i else 0.} for i,(p,r) in enumerate(zip(rendered,radii))]
        gaps=np.linalg.norm(points[:-1]-points[1:],axis=1)/SEGMENT_STEP
        return {'segments':segments,'x':float(rendered[0,0]),'y':float(rendered[0,1]),'heading':heading,'delta_world':float(np.linalg.norm(delta)/WORLD_M),'contacts':contacts,'contact_count':int(self.data.ncon),'speed_bl_s':self.current_speed,'curvature_rad_bl':self.current_curvature,'axial_gap_ratio':[float(v) for v in gaps],'engine':'MuJoCo '+mujoco.__version__,'targets':self.targets}
