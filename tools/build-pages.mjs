import {cp, mkdir, readFile, writeFile} from 'node:fs/promises';
import {rm} from 'node:fs/promises';
const out=new URL('../dist/',import.meta.url),web=new URL('../web/',import.meta.url);
await rm(out,{recursive:true,force:true});await mkdir(out,{recursive:true});
for(const name of ['main.js','style.css','demo-api.js'])await cp(new URL(name,web),new URL(name,out));
await mkdir(new URL('vendor/three/build/',out),{recursive:true});await mkdir(new URL('vendor/three/examples/jsm/controls/',out),{recursive:true});await mkdir(new URL('vendor/three/examples/jsm/environments/',out),{recursive:true});
for(const name of ['three.module.min.js','three.core.min.js'])await cp(new URL('../node_modules/three/build/'+name,import.meta.url),new URL('vendor/three/build/'+name,out));
await cp(new URL('../node_modules/three/examples/jsm/controls/OrbitControls.js',import.meta.url),new URL('vendor/three/examples/jsm/controls/OrbitControls.js',out));
await cp(new URL('../node_modules/three/examples/jsm/environments/RoomEnvironment.js',import.meta.url),new URL('vendor/three/examples/jsm/environments/RoomEnvironment.js',out));
let html=await readFile(new URL('index.html',web),'utf8');
html=html.replace('href="/web/style.css"','href="./style.css"')
  .replace('"three":"/node_modules/three/build/three.module.js","three/addons/":"/node_modules/three/examples/jsm/"','"three":"./vendor/three/build/three.module.min.js","three/addons/":"./vendor/three/examples/jsm/"')
  .replace('<script type="module" src="/web/main.js"></script>','<script src="./demo-api.js"></script><script type="module" src="./main.js"></script>');
await writeFile(new URL('index.html',out),html);
await writeFile(new URL('.nojekyll',out),'');
console.log('Built GitHub Pages demo in dist/');
