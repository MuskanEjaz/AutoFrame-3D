import * as T from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

// Finite, original workshop geometry. Rendering with the inspection cameras
// preserves near-field parallax; the reflection panorama is never a backplate.
export function createWorkcellBackdrop(renderer: T.WebGLRenderer) {
  const scene = new T.Scene();
  scene.background = new T.Color("#202930");
  scene.fog = new T.Fog("#202930", 3.5, 8);
  const panel = new T.MeshStandardMaterial({color:"#29343d",metalness:.25,roughness:.78});
  const alternate = new T.MeshStandardMaterial({color:"#323d45",metalness:.3,roughness:.76});
  const framing = new T.MeshStandardMaterial({color:"#4c5962",metalness:.7,roughness:.52});
  const equipment = new T.MeshStandardMaterial({color:"#354149",metalness:.5,roughness:.63});
  const recess = new T.MeshStandardMaterial({color:"#1b252d",metalness:.1,roughness:.85});
  const floor = new T.MeshStandardMaterial({color:"#242e35",roughness:.9});
  const lightPanel = new T.MeshStandardMaterial({color:"#6f808a",emissive:"#89969f",emissiveIntensity:.18,roughness:.8});
  const warm = new T.MeshStandardMaterial({color:"#8a8171",emissive:"#b6aa91",emissiveIntensity:.12,roughness:.7});
  const buckets=new Map<T.Material,T.BufferGeometry[]>();
  const box=(size:[number,number,number],position:number[],material:T.Material,bevel=.003)=>{
    const g=new RoundedBoxGeometry(...size,1,Math.min(bevel,Math.min(...size)*.2));
    g.translate(...position as [number,number,number]);
    if(!buckets.has(material))buckets.set(material,[]);
    buckets.get(material)!.push(g);
  };
  box([6,5,.04],[0,1.7,-.11],floor);
  for(let i=0;i<8;i++) {
    const x=-1.8+i*.5;
    box([.47,.05,1.65],[x,1.9,.73],i%2?alternate:panel);
    box([.018,.065,1.7],[x-.25,1.86,.73],framing);
    for(const z of [.22,.85])box([.41,.015,.014],[x,1.86,z],equipment);
  }
  // Workcell frame in front of the rear panelling, not painted onto it.
  for(const x of [-1.4,-.7,0,.7,1.4]) {
    box([.038,.065,1.55],[x,1.15,.67],framing);
    box([.05,.085,.035],[x,1.15,.02],equipment);
  }
  for(const z of [.12,1.42])box([3.1,.075,.045],[0,1.15,z],framing);
  for(const x of [-1.05,.85]) {
    box([.54,.34,.49],[x,1.57,.19],equipment,.012);
    box([.57,.38,.035],[x,1.57,.45],framing);
    for(const z of [.04,.17,.30]) {
      box([.47,.012,.006],[x,1.391,z],recess);
      box([.09,.016,.012],[x+.13,1.38,z+.052],framing);
    }
    box([.12,.14,.24],[x,1.59,.59],equipment);
    box([.17,.17,.027],[x,1.57,.72],framing);
    for(let z=.5;z<.71;z+=.033)box([.075,.012,.006],[x-.19,1.4,z],recess);
    box([.07,.022,.1],[x+.18,1.4,.6],recess);
  }
  // Restrained illumination sits beside the robot, away from the amber mismatch.
  box([.25,.016,.66],[-1.53,1.82,1.02],lightPanel);
  box([.32,.016,.02],[-.93,1.8,1.26],warm);
  for(const z of [.13,.48,.83])box([.34,.24,.023],[1.67,1.37,z],framing);
  for(const x of [1.51,1.83])box([.018,.25,.86],[x,1.37,.43],equipment);
  for(const [material,geometries] of buckets) {
    scene.add(new T.Mesh(mergeGeometries(geometries),material));
    geometries.forEach(g=>g.dispose());
  }
  scene.add(new T.HemisphereLight("#e1e7eb","#222930",.45));
  const key=new T.RectAreaLight("#eee6da",1.8,2,1);
  key.position.set(-.8,.3,1.7);key.lookAt(0,1.5,.65);scene.add(key);

  const passScene=new T.Scene(), passCamera=new T.OrthographicCamera(-1,1,1,-1,0,1);
  const shader=new T.ShaderMaterial({
    depthTest:false,depthWrite:false,toneMapped:false,
    uniforms:{source:{value:null},texel:{value:new T.Vector2()},gain:{value:.86}},
    vertexShader:"varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}",
    fragmentShader:`uniform sampler2D source;uniform vec2 texel;uniform float gain;varying vec2 vUv;
      void main(){vec3 c=texture2D(source,vUv).rgb*.36;
        c+=texture2D(source,vUv+texel).rgb*.16;
        c+=texture2D(source,vUv-texel).rgb*.16;
        c+=texture2D(source,vUv+vec2(texel.x,-texel.y)).rgb*.16;
        c+=texture2D(source,vUv+vec2(-texel.x,texel.y)).rgb*.16;
        gl_FragColor=vec4(c*gain,1.);
        #include <colorspace_fragment>
      }`,
  });
  const quad=new T.Mesh(new T.PlaneGeometry(2,2),shader);passScene.add(quad);
  const targets: T.WebGLRenderTarget[]=[];
  const createView=()=>{
    const raw=new T.WebGLRenderTarget(160,88),soft=new T.WebGLRenderTarget(160,88,{depthBuffer:false});
    raw.texture.colorSpace=soft.texture.colorSpace=T.SRGBColorSpace;targets.push(raw,soft);
    return {texture:soft.texture,render(camera:T.Camera,width:number,height:number){
      const w=Math.max(1,Math.round(width/2)),h=Math.max(1,Math.round(height/2));
      if(raw.width!==w||raw.height!==h){raw.setSize(w,h);soft.setSize(w,h);}
      renderer.setRenderTarget(raw);renderer.render(scene,camera);
      shader.uniforms.source.value=raw.texture;shader.uniforms.texel.value.set(1.3/w,1.3/h);
      renderer.setRenderTarget(soft);renderer.render(passScene,passCamera);
      renderer.setRenderTarget(null);
    }};
  };
  return {createView,setEnvironment(texture:T.Texture,rotation:T.Euler){
    scene.environment=texture;scene.environmentIntensity=.42;scene.environmentRotation.copy(rotation);
  },dispose(){
    scene.traverse(o=>{if(o instanceof T.Mesh){o.geometry.dispose();(o.material as T.Material).dispose();}});
    targets.forEach(t=>t.dispose());quad.geometry.dispose();shader.dispose();
  }};
}
