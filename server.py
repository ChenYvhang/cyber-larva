"""CyberLarva local server and fixed-step closed-loop simulation."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import argparse, json, mimetypes, threading, time, webbrowser
from cyberlarva.connectome import ConnectomeBrain
from cyberlarva.world import LarvaWorld
from cyberlarva.physics import MuJoCoLarva

ROOT=Path(__file__).resolve().parent; mimetypes.add_type('text/javascript','.js')

class Simulation:
    def __init__(self):
        self.world=LarvaWorld(); self.brain=ConnectomeBrain(ROOT/'data'/'connectome')
        self.physics=MuJoCoLarva(self.world,ROOT/'config'/'trajectory_calibration.json')
        pose=self.physics.pose();self.world.segments=pose['segments'];self.world.x,self.world.y,self.world.heading=pose['x'],pose['y'],pose['heading']
        self.physics_stats=pose;self.lock=threading.RLock(); self.paused=True; self.revision=0; self.stats={}; self.error=''
        self.map_path=ROOT/'maps'/'custom_map.json'; threading.Thread(target=self.run,daemon=True).start()
    def rebuild_physics(self):
        self.physics=MuJoCoLarva(self.world,ROOT/'config'/'trajectory_calibration.json');self.physics_stats=self.physics.pose();self.world.segments=self.physics_stats['segments']
    def run(self):
        try:
            while True:
                start=time.perf_counter()
                with self.lock:
                    if not self.paused:
                        n=self.brain.step(self.world.senses());physics_start=time.perf_counter();self.physics_stats=self.physics.step(n,.02);physics_ms=(time.perf_counter()-physics_start)*1000;self.world.sync_physics(self.physics_stats,n,.02);self.stats=n.__dict__|{'physics_ms':physics_ms,'speed_bl_s':self.physics_stats['speed_bl_s'],'curvature_rad_bl':self.physics_stats['curvature_rad_bl']}
                time.sleep(max(.001,.02-(time.perf_counter()-start)))
        except Exception as exc:self.error=str(exc)
    def state(self):
        with self.lock:
            w=self.world
            return {'time':w.time,'paused':self.paused,'error':self.error,'behavior':w.behavior,'segments':w.segments,'heading':w.heading,
                    'foods_found':w.foods_found,'distance':w.distance,'trail':w.trail,'stats':self.stats,'physics':self.physics_stats,'revision':self.revision,'items':[i.__dict__ for i in w.items]}
    def world_data(self):
        with self.lock:return {'grid':[''.join(r) for r in self.world.grid],'items':[i.__dict__ for i in self.world.items],'revision':self.revision}
    def command(self,d):
        with self.lock:
            a=d.get('action')
            if a=='pause':self.paused=bool(d.get('value',True))
            elif a=='paint':
                if not self.paused:raise ValueError('请先暂停再编辑')
                self.world.paint(int(d['x']),int(d['y']),d['tool']);self.rebuild_physics();self.revision+=1
            elif a=='save':self.world.save(self.map_path)
            elif a=='load':self.world.load(self.map_path);self.brain.reset();self.rebuild_physics();self.revision+=1
            elif a=='garden':self.world.garden();self.brain.reset();self.rebuild_physics();self.paused=True;self.revision+=1
            elif a=='reset':self.world.garden();self.brain.reset();self.rebuild_physics();self.paused=True;self.revision+=1
            else:raise ValueError('未知操作')
        return {'ok':True}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8775);ap.add_argument('--no-browser',action='store_true');args=ap.parse_args();sim=Simulation()
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
        def log_message(self,*a):pass
        def js(self,d,status=200):
            p=json.dumps(d).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(p)));self.end_headers();self.wfile.write(p)
        def do_GET(self):
            p=self.path.split('?')[0]
            if p=='/api/state':return self.js(sim.state())
            if p=='/api/world':return self.js(sim.world_data())
            if p=='/':self.path='/web/index.html'
            elif not p.startswith(('/web/','/node_modules/three/')) or '..' in p:return self.send_error(404)
            return super().do_GET()
        def do_POST(self):
            if self.path!='/api/command':return self.send_error(404)
            try:n=int(self.headers.get('Content-Length','0'));return self.js(sim.command(json.loads(self.rfile.read(n))))
            except Exception as exc:return self.js({'error':str(exc)},400)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);url=f'http://127.0.0.1:{args.port}';print('CyberLarva:',url,flush=True)
    if not args.no_browser:webbrowser.open(url)
    server.serve_forever()
if __name__=='__main__':main()
