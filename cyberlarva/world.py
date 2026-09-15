from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json, math


@dataclass
class Item:
    kind: str
    x: float
    y: float
    radius: float = .55
    strength: float = 1.


class LarvaWorld:
    width, height = 24, 20
    segment_count = 11

    def __init__(self):
        self.grid = []
        self.items: list[Item] = []
        self.x, self.y, self.heading = 11.5, 9.5, .15
        self.time = self.phase = self.distance = 0.
        self.foods_found = 0
        self.behavior = "resting"
        self.trail = []
        self.muscles = [0.] * self.segment_count
        self.segments = []
        self.physics_touch = 0.
        self.garden()

    def garden(self):
        self.grid = [['#' if x in (0,self.width-1) or y in (0,self.height-1) else '.' for x in range(self.width)] for y in range(self.height)]
        self.items = [Item('food', 15.8, 9.2, .8, 1), Item('food', 6.2, 6.0, .65, .85),
                      Item('food', 18.3, 15.1, .75, .9), Item('leaf', 8.0, 11.5, 1.1),
                      Item('leaf', 14.5, 5.4, 1.15), Item('rock', 11.3, 13.1, .7),
                      Item('rock', 17.0, 8.0, .55), Item('fungus', 5.0, 14.0, .7),
                      Item('puddle', 10.4, 5.3, 1.25)]
        self.x, self.y, self.heading = 11.5, 9.5, .15
        self.time = self.phase = self.distance = 0.; self.foods_found = 0; self.trail = []
        self._pose(0, 0)

    def _blocked(self, x, y):
        gx, gy = int(x), int(y)
        if gx < 0 or gy < 0 or gx >= self.width or gy >= self.height or self.grid[gy][gx] == '#': return True
        return any(i.kind == 'rock' and math.hypot(x-i.x, y-i.y) < i.radius+.18 for i in self.items)

    def senses(self):
        hx = self.x + math.cos(self.heading) * .55; hy = self.y + math.sin(self.heading) * .55
        def odor_at(x, y):
            return sum(i.strength / (1 + math.hypot(x-i.x, y-i.y)**2 * .7) for i in self.items if i.kind == 'food')
        left = odor_at(hx-math.sin(self.heading)*.18, hy+math.cos(self.heading)*.18)
        right = odor_at(hx+math.sin(self.heading)*.18, hy-math.cos(self.heading)*.18)
        ahead = self._blocked(hx+math.cos(self.heading)*.28, hy+math.sin(self.heading)*.28)
        al = self._blocked(hx+math.cos(self.heading)*.2-math.sin(self.heading)*.2, hy+math.sin(self.heading)*.2+math.cos(self.heading)*.2)
        ar = self._blocked(hx+math.cos(self.heading)*.2+math.sin(self.heading)*.2, hy+math.sin(self.heading)*.2-math.cos(self.heading)*.2)
        stretch = sum(abs(self.muscles[i]-self.muscles[i-1]) for i in range(1,len(self.muscles))) / 10
        return {'olfactory': min(1., (left+right)*.55), 'odor_lr': max(-1,min(1,(right-left)*2.8)),
                'visual': .18, 'warm': .08, 'cold': .02, 'touch': max(float(ahead),self.physics_touch),
                'touch_lr': float(al)-float(ar), 'proprio': min(1,stretch*2), 'noci': float(ahead)*.18}

    def sync_physics(self, pose, neural, dt=.02):
        previous=(self.x,self.y);self.x,self.y,self.heading=pose['x'],pose['y'],pose['heading']
        self.segments=pose['segments'];self.muscles=[s['muscle'] for s in self.segments]
        self.physics_touch=float(bool(pose['contacts']));self.distance+=math.hypot(self.x-previous[0],self.y-previous[1]);self.time+=dt
        self.behavior='backward escape' if neural.backward>.45 else 'head casting' if neural.head_sweep>.58 else 'forward crawling' if neural.forward>.3 else 'resting'
        for item in list(self.items):
            if item.kind=='food' and math.hypot(self.x-item.x,self.y-item.y)<item.radius+.35:
                self.items.remove(item);self.foods_found+=1;self.behavior='feeding'
        if not self.trail or math.hypot(self.x-self.trail[-1][0],self.y-self.trail[-1][1])>.035:self.trail.append([self.x,self.y])
        self.trail=self.trail[-600:]

    def step(self, neural, dt=.02):
        direction = neural.forward - neural.backward
        speed = direction * .58
        self.phase += dt * (5.2 + abs(speed)*3.4)
        self.heading += neural.turn * dt * 1.85 + math.sin(self.phase*.42) * neural.head_sweep * dt * .1
        nx = self.x + math.cos(self.heading)*speed*dt; ny = self.y + math.sin(self.heading)*speed*dt
        if self._blocked(nx,ny): self.heading += 1.3*dt; speed = min(0,speed)
        else: self.x,self.y=nx,ny; self.distance += abs(speed)*dt
        self.time += dt
        # Posterior segments (high index) lead the forward contraction wave.
        self.muscles = [max(0, math.sin(self.phase+i*.72))*abs(direction) for i in range(self.segment_count)]
        self._pose(neural.turn, neural.head_sweep)
        self.behavior = 'backward escape' if neural.backward>.45 else 'head casting' if neural.head_sweep>.58 else 'forward crawling' if neural.forward>.3 else 'resting'
        for item in list(self.items):
            if item.kind=='food' and math.hypot(self.x-item.x,self.y-item.y)<item.radius+.35:
                self.items.remove(item); self.foods_found += 1; self.behavior='feeding'
        if not self.trail or math.hypot(self.x-self.trail[-1][0],self.y-self.trail[-1][1])>.04:self.trail.append([self.x,self.y])
        self.trail=self.trail[-600:]

    def _pose(self, turn, sweep):
        self.segments=[]
        for i in range(self.segment_count):
            back=i*.185; wave=math.sin(self.phase+i*.72)
            lateral=wave*.035*(.25+abs(self.muscles[i]))
            if i<3:lateral += math.sin(self.phase*.42+i*.35)*sweep*.035
            px=self.x-math.cos(self.heading)*back-math.sin(self.heading)*lateral
            py=self.y-math.sin(self.heading)*back+math.cos(self.heading)*lateral
            radius=(.135+.055*math.sin(math.pi*i/(self.segment_count-1)))*(1-self.muscles[i]*.12)
            self.segments.append({'x':px,'y':py,'z':radius*.62,'radius':radius,'muscle':self.muscles[i]})

    def paint(self,x,y,tool):
        if not (1<=x<self.width-1 and 1<=y<self.height-1): return
        if tool in ('wall','floor'): self.grid[y][x]='#' if tool=='wall' else '.'
        elif tool=='spawn': self.x,self.y=x+.5,y+.5
        else:
            self.items=[i for i in self.items if math.hypot(i.x-(x+.5),i.y-(y+.5))>.55]
            if tool!='erase': self.items.append(Item(tool,x+.5,y+.5,1.1 if tool in ('leaf','puddle') else .6))

    def save(self,path:Path): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps({'grid':[''.join(r) for r in self.grid],'items':[asdict(i) for i in self.items],'spawn':[self.x,self.y,self.heading]},indent=2),encoding='utf-8')
    def load(self,path:Path):
        d=json.loads(path.read_text(encoding='utf-8')); self.grid=[list(r) for r in d['grid']]; self.items=[Item(**i) for i in d['items']]; self.x,self.y,self.heading=d['spawn']; self.trail=[]; self._pose(0,0)
