/* Browser-only API used by the GitHub Pages demo. The local application does
   not load this file and continues to use the Python/MuJoCo server. */
(() => {
  const nativeFetch = window.fetch.bind(window), width = 24, height = 20, dt = .02;
  const baseItems = () => [
    {kind:'food',x:15.8,y:9.2,radius:.8,strength:1},{kind:'food',x:6.2,y:6,radius:.65,strength:.85},
    {kind:'food',x:18.3,y:15.1,radius:.75,strength:.9},{kind:'leaf',x:8,y:11.5,radius:1.1,strength:1},
    {kind:'leaf',x:14.5,y:5.4,radius:1.15,strength:1},{kind:'rock',x:11.3,y:13.1,radius:.7,strength:1},
    {kind:'rock',x:17,y:8,radius:.55,strength:1},{kind:'fungus',x:5,y:14,radius:.7,strength:1},
    {kind:'puddle',x:10.4,y:5.3,radius:1.25,strength:1}
  ];
  const neurons = [
    ['MDNa-left','MDNa','left','descending neuron','reported backward locomotion command'],
    ['MDNa-right','MDNa','right','descending neuron','reported backward locomotion command'],
    ['DN-VNC-01','DN-VNC','left','descending neuron','browser-demo forward drive'],
    ['DN-VNC-02','DN-VNC','right','descending neuron','browser-demo forward drive'],
    ['olfactory-left','olfactory projection','left','sensory projection','odor steering input'],
    ['olfactory-right','olfactory projection','right','sensory projection','odor steering input'],
    ['Basin-1','Basin','left','mechanosensory interneuron','touch pathway'],
    ['Basin-2','Basin','right','mechanosensory interneuron','touch pathway'],
    ['A27h-left','A27h','left','premotor interneuron','forward wave drive'],
    ['A27h-right','A27h','right','premotor interneuron','forward wave drive'],
    ['Goro-left','Goro','left','nociceptive interneuron','escape pathway'],
    ['Goro-right','Goro','right','nociceptive interneuron','escape pathway']
  ].map((n,index)=>({index,id:n[0],name:n[1],side:n[2],celltype:n[3],annotations:n[4],reported_function:n[4],cluster:index+1}));
  let grid, items, x, y, heading, phase, time, distance, foodsFound, trail, segments, revision, paused, knockout;
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)), wrap=a=>(a+Math.PI)%(Math.PI*2)-Math.PI;
  function reset(){
    grid=Array.from({length:height},(_,yy)=>Array.from({length:width},(_,xx)=>xx===0||yy===0||xx===width-1||yy===height-1?'#':'.'));
    items=baseItems();x=11.5;y=9.5;heading=.15;phase=time=distance=foodsFound=0;trail=[];revision=(revision||0)+1;paused=true;knockout=new Set();pose(0,.5);
  }
  function blocked(nx,ny){return nx<1||ny<1||nx>width-1||ny>height-1||grid[Math.floor(ny)]?.[Math.floor(nx)]==='#'||items.some(i=>i.kind==='rock'&&Math.hypot(nx-i.x,ny-i.y)<i.radius+.2)}
  function pose(turn,drive){
    segments=[];let along=0;
    for(let i=0;i<11;i++){
      let muscle=Math.pow(Math.max(0,Math.sin(phase+i*.66)),1.35)*drive;if(i)along+=.185*(1-.22*muscle);
      let lateral=Math.sin(phase+i*.66)*.025*(.3+muscle)+turn*Math.exp(-i*.35)*.12;
      let radius=.1225+.0325*Math.sin(Math.PI*i/10);
      segments.push({x:x-Math.cos(heading)*along-Math.sin(heading)*lateral,y:y-Math.sin(heading)*along+Math.cos(heading)*lateral,z:radius*.68,radius,muscle,angle:lateral});
    }
  }
  function tick(){
    if(paused)return;let food=items.filter(i=>i.kind==='food').sort((a,b)=>Math.hypot(x-a.x,y-a.y)-Math.hypot(x-b.x,y-b.y))[0];
    let desired=food?Math.atan2(food.y-y,food.x-x):heading,turn=clamp(wrap(desired-heading)*.8,-1,1),drive=clamp(.62-knockout.size*.035,.18,.62),speed=.62*drive/.62;
    phase=(phase+Math.PI*2*1.41*dt)%(Math.PI*2);heading+=turn*dt*.62+Math.sin(phase*.45)*dt*.025;
    let nx=x+Math.cos(heading)*speed*dt,ny=y+Math.sin(heading)*speed*dt;if(blocked(nx,ny)){heading+=.9;turn=1}else{x=nx;y=ny;distance+=speed*dt}
    time+=dt;pose(turn,drive);
    let before=items.length;items=items.filter(i=>i.kind!=='food'||Math.hypot(x-i.x,y-i.y)>=i.radius+.35);if(items.length<before){foodsFound+=before-items.length;revision++}
    if(!trail.length||Math.hypot(x-trail.at(-1)[0],y-trail.at(-1)[1])>.04)trail.push([x,y]);trail=trail.slice(-600);
  }
  reset();setInterval(tick,dt*1000);
  function world(){return {grid:grid.map(r=>r.join('')),items,revision}}
  function state(){let drive=clamp(.62-knockout.size*.035,.18,.62);return {time,paused,error:'',behavior:paused?'resting':'forward crawling',segments,heading,foods_found:foodsFound,distance,trail,revision,items,knockout:{count:knockout.size,indices:[...knockout]},interventions:[],stats:{forward:drive,backward:0,turn:0,source:'Browser demo · reduced controller',active:Math.round(180*drive),step_ms:.2,physics_ms:.1},physics:{segments,speed_bl_s:drive*.48,curvature_rad_bl:.35,contact_count:8,engine:'Browser segmented demo',targets:{speed_bl_s:.300,crawl_hz:1.410,curvature_rad_bl:1.061,head_cast_hz:.111}}}}
  function command(d){
    if(d.action==='pause')paused=!!d.value;
    else if(d.action==='reset'||d.action==='garden')reset();
    else if(d.action==='paint'){
      let px=+d.x,py=+d.y;if(px>=1&&py>=1&&px<width-1&&py<height-1){if(d.tool==='wall'||d.tool==='floor')grid[py][px]=d.tool==='wall'?'#':'.';else if(d.tool==='spawn'){x=px+.5;y=py+.5;pose(0,.5)}else{items=items.filter(i=>Math.hypot(i.x-(px+.5),i.y-(py+.5))>.55);if(d.tool!=='erase')items.push({kind:d.tool,x:px+.5,y:py+.5,radius:['leaf','puddle'].includes(d.tool)?1.1:.6,strength:1})}revision++}
    }else if(d.action==='save')localStorage.setItem('cyberlarva-map',JSON.stringify({grid,items,x,y,heading}));
    else if(d.action==='load'){let saved=JSON.parse(localStorage.getItem('cyberlarva-map')||'null');if(saved){({grid,items,x,y,heading}=saved);pose(0,.5);revision++}}
    else if(d.action==='knockout'){for(let i of d.indices||[]){if(d.mode==='remove')knockout.delete(i);else knockout.add(i)}}
    else if(d.action==='clear_knockout')knockout.clear();
    return {ok:true,knockout:{count:knockout.size,indices:[...knockout]}};
  }
  const reply=(data,status=200)=>Promise.resolve(new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}}));
  window.fetch=(input,init={})=>{let url=new URL(typeof input==='string'?input:input.url,location.href);if(!url.pathname.includes('/api/'))return nativeFetch(input,init);
    if(url.pathname.endsWith('/api/state'))return reply(state());if(url.pathname.endsWith('/api/world'))return reply(world());
    if(url.pathname.endsWith('/api/neurons')){let q=(url.searchParams.get('q')||'').toLowerCase(),found=neurons.filter(n=>JSON.stringify(n).toLowerCase().includes(q)).map(n=>({...n,disabled:knockout.has(n.index)}));return reply({neurons:found,total:2952,knockout:{count:knockout.size,indices:[...knockout]}})}
    if(url.pathname.endsWith('/api/command'))return reply(command(JSON.parse(init.body||'{}')));return reply({error:'unknown demo endpoint'},404);
  };
  addEventListener('DOMContentLoaded',()=>{let caption=document.querySelector('aside .caption');if(caption)caption.textContent='在线轻量演示 · 浏览器分节动力学 · 完整 MuJoCo 版请本地运行';});
})();
