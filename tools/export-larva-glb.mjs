import * as THREE from 'three';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { writeFile, mkdir } from 'node:fs/promises';

globalThis.FileReader = class {
  readAsArrayBuffer(blob) { blob.arrayBuffer().then(v => { this.result=v; this.onloadend?.(); }); }
  readAsDataURL(blob) { blob.arrayBuffer().then(v => { this.result=`data:${blob.type};base64,${Buffer.from(v).toString('base64')}`; this.onloadend?.(); }); }
};

const profile=[.045,.085,.125,.142,.147,.150,.151,.151,.150,.149,.148,.147,.146,.145,.143,.140,.136,.131,.123,.110,.090];
const radius=t=>{const x=t*(profile.length-1),i=Math.min(profile.length-2,Math.floor(x)),f=x-i;return THREE.MathUtils.lerp(profile[i],profile[i+1],f)};
const rings=81,sides=40,verts=[],colors=[],indices=[];
const head=new THREE.Color('#ddd9d3'),mid=new THREE.Color('#faf8f4'),tail=new THREE.Color('#ebe8e2');
for(let i=0;i<rings;i++){
  const t=i/(rings-1),r=radius(t)*(1-.025*Math.exp(-Math.pow((t*10-Math.round(t*10))/.16,2))),x=(.5-t)*1.55;
  const c=t<.42?new THREE.Color().lerpColors(head,mid,t/.42):new THREE.Color().lerpColors(mid,tail,(t-.42)/.58);
  for(let j=0;j<sides;j++){const a=j/sides*Math.PI*2,v=Math.sin(a),z=Math.cos(a)*r,y=v*r*(v>0?.82:.64);verts.push(x,y,z);colors.push(c.r,c.g,c.b);}
}
for(let i=0;i<rings-1;i++)for(let j=0;j<sides;j++){const a=i*sides+j,b=i*sides+(j+1)%sides,c=(i+1)*sides+j,d=(i+1)*sides+(j+1)%sides;indices.push(a,c,b,b,c,d)}
const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(verts,3));geometry.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));geometry.setIndex(indices);geometry.computeVertexNormals();
const root=new THREE.Group();root.name='Drosophila_melanogaster_larva';
const skin=new THREE.Mesh(geometry,new THREE.MeshPhysicalMaterial({name:'translucent_cuticle',color:'#ffffff',roughness:.38,transmission:.20,transparent:true,opacity:.60,thickness:.38,vertexColors:true,side:THREE.DoubleSide,depthWrite:false}));skin.name='continuous_segmented_cuticle';root.add(skin);
const dark=new THREE.MeshStandardMaterial({name:'cephalopharyngeal_skeleton',color:'#261812',roughness:.5});
for(const side of [-1,1]){const curve=new THREE.CatmullRomCurve3([new THREE.Vector3(.745,-.006,side*.006),new THREE.Vector3(.71,-.004,side*.015),new THREE.Vector3(.67,.005,side*.017),new THREE.Vector3(.62,.012,side*.01)]);const hook=new THREE.Mesh(new THREE.TubeGeometry(curve,20,.006,7,false),dark);hook.name=`mouth_hook_${side<0?'left':'right'}`;root.add(hook)}
const spiracleMat=new THREE.MeshStandardMaterial({name:'posterior_spiracle',color:'#a45c3e',roughness:.6});
for(const side of [-1,1]){const s=new THREE.Mesh(new THREE.CylinderGeometry(.007,.01,.022,10),spiracleMat);s.name=`posterior_spiracle_${side<0?'left':'right'}`;s.position.set(-.77,0,side*.027);s.rotation.z=Math.PI/2;root.add(s)}
root.rotation.z=.04;
const exporter=new GLTFExporter();const data=await new Promise((resolve,reject)=>exporter.parse(root,resolve,reject,{binary:true,onlyVisible:true}));
await mkdir(new URL('../assets/',import.meta.url),{recursive:true});
await writeFile(new URL('../assets/drosophila-melanogaster-larva.glb',import.meta.url),Buffer.from(data));
console.log(`exported ${data.byteLength} bytes`);
