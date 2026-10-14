import * as T from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

export type Finishes = { paint: T.MeshStandardMaterial; metal: T.MeshStandardMaterial;
  dark: T.MeshStandardMaterial; black: T.MeshStandardMaterial; steel: T.MeshStandardMaterial };

// Original metre-scale geometry. +X is tool approach; mating face stays x=-0.055.
export function industrialTools(materials: Finishes) {
  const fastener=new T.MeshStandardMaterial({color:"#35414a",metalness:.75,roughness:.52});
  const cache = new Map<string, T.BufferGeometry>();
  const cached = (key: string, create: () => T.BufferGeometry) => {
    if (!cache.has(key)) cache.set(key, create());
    return cache.get(key)!;
  };
  const mesh = (parent: T.Object3D, geometry: T.BufferGeometry, material: T.Material,
    position: number[], feature = true) => {
    const o = new T.Mesh(geometry, material);
    o.position.fromArray(position); o.castShadow = o.receiveShadow = true;
    o.userData.featureEdge = feature; parent.add(o); return o;
  };
  const box = (parent: T.Object3D, size: [number,number,number], position: number[],
    material: T.Material, radius = .0015, feature = true) => mesh(parent,
      cached(`b${size}:${radius}`, () => new RoundedBoxGeometry(...size, 1, radius)),
      material, position, feature);
  const cylinder = (parent: T.Object3D, r: number, length: number, position: number[],
    material: T.Material, axis = "x", feature = true) => {
    const o = mesh(parent, cached(`c${r}:${length}`, () => new T.CylinderGeometry(r,r,length,32)), material,position,feature);
    if (axis === "x") o.rotation.z = Math.PI/2;
    if (axis === "z") o.rotation.x = Math.PI/2;
    return o;
  };
  const socket = (parent: T.Object3D, position: number[], axis = "y", radius = .0038) => {
    const shape = new T.Shape(); shape.absarc(0,0,radius,0,Math.PI*2,false);
    const hole = new T.Path();
    for (let i=0;i<6;i++) {
      const a = -i*Math.PI/3;
      if (!i) hole.moveTo(Math.cos(a)*radius*.48,Math.sin(a)*radius*.48);
      else hole.lineTo(Math.cos(a)*radius*.48,Math.sin(a)*radius*.48);
    }
    hole.closePath(); shape.holes.push(hole);
    const g = cached(`s${radius}`,()=> new T.ExtrudeGeometry(shape,{depth:.0015,bevelEnabled:true,
      bevelSize:.0002,bevelThickness:.0002,bevelSegments:1,curveSegments:16}));
    const o = mesh(parent,g,fastener,position,false);
    if (axis === "y") o.rotation.x = Math.PI/2;
    if (axis === "x") o.rotation.y = Math.PI/2;
    // Dark bottom is behind the open hex socket, rather than painted on its face.
    cylinder(parent,radius*.95,.0006,position,materials.black,axis,false);
    return o;
  };
  const cable = (parent: T.Object3D, points: number[][], radius = .004) => mesh(parent,
    new T.TubeGeometry(new T.CatmullRomCurve3(points.map(p=>new T.Vector3().fromArray(p))),32,radius,8,false),
    materials.black,[0,0,0],false);
  const profile = (parent: T.Object3D, points: number[][], depth: number, position: number[],
    material: T.Material, holes: number[][] = []) => {
    const shape = new T.Shape(points.map(p=>new T.Vector2(p[0],p[1])));
    for(const [x,z,r] of holes) {
      const hole=new T.Path();hole.absarc(x,z,r,0,Math.PI*2,true);shape.holes.push(hole);
    }
    const geometry = new T.ExtrudeGeometry(shape,{depth,bevelEnabled:true,bevelSize:.002,
      bevelThickness:.002,bevelSegments:3,curveSegments:16});
    // Shape x/y -> tool x/z, extrusion goes toward the far side (+Y).
    geometry.rotateX(Math.PI/2); geometry.translate(0,depth/2,0);
    return mesh(parent,geometry,material,position);
  };
  const gripper = (parent: T.Group) => {
    cylinder(parent,.067,.026,[-.018,0,0],materials.dark);
    cylinder(parent,.062,.004,[-.002,0,0],materials.metal);
    profile(parent,[[0,-.038],[.014,-.048],[.085,-.048],[.099,-.034],
      [.099,.034],[.085,.048],[.014,.048],[0,.038]],.102,[0,0,0],materials.dark);
    // Separate machined side plates, seam and an inset actuator cover.
    for (const side of [-1,1]) {
      profile(parent,[[.007,-.034],[.019,-.043],[.08,-.043],[.093,-.03],
        [.093,.03],[.08,.043],[.019,.043],[.007,.034]],.004,[0,side*.054,0],materials.metal,
        [[.02,-.029,.006],[.02,.029,.006],[.079,-.029,.006],[.079,.029,.006]]);
      for (const x of [.02,.079]) for (const z of [-.029,.029])
        socket(parent,[x,side*.057,z],"y");
      box(parent,[.041,.001,.019],[.051,side*.057,0],materials.dark,.0004);
    }
    box(parent,[.096,.084,.008],[.049,0,.049],materials.steel);
    for(const x of [.032,.044,.056,.068])
      box(parent,[.002,.038,.001],[x,0,.0535],materials.black,.0003,false);
    for (const x of [.016,.083]) for (const y of [-.029,.029]) socket(parent,[x,y,.054],"z",.003);
    // Twin linear guide rods, end retainers and independently visible jaw carriages.
    for (const z of [-.028,.028]) {
      cylinder(parent,.005,.108,[.106,0,z],materials.metal,"y");
      for (const y of [-.056,.056]) cylinder(parent,.008,.007,[.106,y,z],materials.steel,"y");
    }
    for (const side of [-1,1]) {
      const y=side*.037;
      box(parent,[.035,.032,.081],[.121,y,0],materials.steel,.002);
      profile(parent,[[.132,-.031],[.158,-.031],[.18,-.025],[.198,-.02],[.25,-.02],
        [.256,-.014],[.256,.014],[.25,.02],[.198,.02],[.18,.025],[.158,.031],[.132,.031]],
        .022,[0,y,0],materials.metal,[[.151,0,.005],[.176,0,.005]]);
      for(const x of [.151,.176]) {
        cylinder(parent,.0045,.002,[x,y-side*.0115,0],materials.dark,"y",false);
        socket(parent,[x,y-side*.014,0],"y",.0027);
      }
      box(parent,[.058,.008,.031],[.224,y-side*.014,0],materials.black,.001);
      for (const x of [.15,.18]) socket(parent,[x,y-side*.013,-.013],"y",.003);
      // Grip grooves are only surface detail and excluded from the CAD feature edges.
      for (let x=.204;x<.25;x+=.006)
        box(parent,[.001,.0008,.029],[x,y-side*.0183,0],materials.steel,.0002,false);
      for (const z of [-.028,.028]) socket(parent,[.122,y,z+.001],"z",.003);
    }
    cylinder(parent,.008,.016,[.02,.062,.021],materials.steel,"y",false);
    cylinder(parent,.006,.02,[.02,.077,.021],materials.black,"y",false);
    cable(parent,[[.02,.087,.021],[-.005,.1,.035],[-.041,.09,.05],[-.075,.065,.055]],.0035);
  };
  const scanner = (parent: T.Group) => {
    profile(parent,[[-.053,-.026],[.039,-.026],[.048,-.015],[.048,.02],
      [.03,.031],[-.045,.031],[-.053,.021]],.068,[0,0,0],materials.dark);
    for (const y of [-.036,.036]) {
      box(parent,[.079,.003,.035],[-.005,y,.001],materials.steel);
      for (const x of [-.035,.025]) socket(parent,[x,y-.002,.012],"y",.0025);
    }
    // Recessed objective: dark glass behind a metal aperture and rubber bezel.
    cylinder(parent,.02,.008,[.049,0,0],materials.black);
    cylinder(parent,.016,.003,[.054,0,0],materials.metal);
    const glass = new T.MeshPhysicalMaterial({color:"#06232d",metalness:.35,roughness:.12,clearcoat:1});
    cylinder(parent,.013,.001,[.0558,0,0],glass);
    box(parent,[.012,.009,.006],[.02,-.034,.026],new T.MeshStandardMaterial({color:"#008fa8",emissive:"#008fa8",emissiveIntensity:.4}));
    cylinder(parent,.009,.017,[-.061,0,.002],materials.steel);
    cylinder(parent,.007,.022,[-.08,0,.002],materials.black);
    cable(parent,[[-.092,0,.002],[-.13,0,.003],[-.16,.015,-.025],[-.14,.02,-.12]],.004);
    for (const y of [-.028,.028]) box(parent,[.058,.006,.049],[-.02,y,-.043],materials.steel);
    box(parent,[.075,.07,.008],[-.02,0,-.07],materials.dark);
  };
  return {gripper,scanner,box,cylinder,socket,cable};
}

// Linear-data textures: deterministic micron-scale grain, no colour image or external URL.
export function surfaceTexture(kind: "paint" | "metal" | "bench") {
  const size=256, data = new Uint8Array(size*size*4);
  let seed=72819;
  for (let y=0;y<size;y++) for (let x=0;x<size;x++) {
    seed=(Math.imul(seed,1664525)+1013904223)>>>0;
    const noise=(seed>>>24)/255;
    const value=Math.round(kind==="paint" ? 185+noise*14+Math.sin(x*.025)*Math.cos(y*.03)*9
      : 175+noise*18+Math.sin(y*2.7)*12+Math.sin(x*.02)*5);
    const i=(y*size+x)*4; data[i]=data[i+1]=data[i+2]=value;data[i+3]=255;
  }
  const texture=new T.DataTexture(data,size,size);texture.wrapS=texture.wrapT=T.RepeatWrapping;
  texture.magFilter=T.LinearFilter;texture.minFilter=T.LinearMipmapLinearFilter;
  texture.generateMipmaps=true;texture.needsUpdate=true;
  texture.repeat.set(kind==="bench"?25:8,kind==="bench"?25:8);
  return texture;
}

export async function loadRobot(materials: Finishes, signal: AbortSignal) {
  const base = "assets/industrial/";
  const [description,buffer]=await Promise.all([
    fetch(base+"robot.json",{signal}).then(r=>{if(!r.ok)throw new Error("Robot manifest unavailable");return r.json();}),
    fetch(base+"robot.bin",{signal}).then(r=>{if(!r.ok)throw new Error("Robot buffers unavailable");return r.arrayBuffer();})]);
  const group=new T.Group();
  for (const m of description.meshes) {
    const geometry=new T.BufferGeometry();
    for (const name of ["position","normal"])
      geometry.setAttribute(name,new T.BufferAttribute(new Float32Array(buffer,m[name].offset,m[name].count),3));
    geometry.setIndex(new T.BufferAttribute(new Uint32Array(buffer,m.index.offset,m.index.count),1));
    const pos=geometry.getAttribute("position"),uv=new Float32Array(pos.count*2);
    for(let i=0;i<pos.count;i++){uv[i*2]=pos.getX(i)*10;uv[i*2+1]=pos.getZ(i)*10;}
    geometry.setAttribute("uv",new T.BufferAttribute(uv,2));
    const o=new T.Mesh(geometry,materials[m.material as keyof Finishes]);
    o.castShadow=o.receiveShadow=true;group.add(o);
  }
  group.userData.asset=description; return group;
}
