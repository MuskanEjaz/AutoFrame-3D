// Offline conversion: OBJ -> welded, baked local metre-space buffers, grouped by finish.
import fs from 'node:fs';
import path from 'node:path';
import * as T from '../frontend/node_modules/three/build/three.module.js';
import { OBJLoader } from '../frontend/node_modules/three/examples/jsm/loaders/OBJLoader.js';
import { mergeGeometries, mergeVertices, toCreasedNormals } from '../frontend/node_modules/three/examples/jsm/utils/BufferGeometryUtils.js';
const source = '.tools/robot-source', out = 'frontend/public/assets/industrial';
const manifest = JSON.parse(fs.readFileSync(path.join(source,'manifest.json')));
const groups = new Map();
for (const part of manifest.parts) {
  const obj = new OBJLoader().parse(fs.readFileSync(path.join(source,part.file),'utf8'));
  obj.traverse(o => {
    if (!o.isMesh) return;
    const g = o.geometry;
    g.deleteAttribute('uv');
    g.scale(manifest.scale,manifest.scale,manifest.scale);
    g.applyMatrix4(new T.Matrix4().fromArray(part.matrix));
    const material = ['white','off_white'].includes(part.material) ? 'paint' : part.material === 'black' ? 'dark' : 'steel';
    if (!groups.has(material)) groups.set(material,[]);
    // Three's crease helper hashes at .01 units. Work in millimetres so distinct
    // metre-scale surface vertices are not incorrectly averaged across 1 cm cells.
    g.scale(1000,1000,1000);
    const smooth = toCreasedNormals(g,Math.PI/4);
    smooth.scale(.001,.001,.001);
    groups.get(material).push(mergeVertices(smooth,1e-6));
  });
}
const chunks = [], meshes = [];
let offset = 0, triangles = 0;
for (const [material,geometries] of groups) {
  const geometry = mergeGeometries(geometries);
  const entry = {material};
  for (const name of ['position','normal','index']) {
    const array = name === 'index' ? new Uint32Array(geometry.index.array) : new Float32Array(geometry.getAttribute(name).array);
    const buffer = Buffer.from(array.buffer,array.byteOffset,array.byteLength);
    entry[name] = {offset, count:array.length}; chunks.push(buffer); offset += buffer.length;
  }
  triangles += entry.index.count/3;
  meshes.push(entry);
}
fs.writeFileSync(path.join(out,'robot.bin'),Buffer.concat(chunks));
fs.writeFileSync(path.join(out,'robot.json'),JSON.stringify({meshes,triangles,bytes:offset,sourceDownloadBytes:manifest.downloadBytes,revision:manifest.revision,scale:manifest.scale,jointAngles:manifest.jointAngles},null,2));
console.log({triangles,bytes:offset});
