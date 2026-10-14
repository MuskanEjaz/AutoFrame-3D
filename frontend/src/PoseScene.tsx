import { useEffect, useRef, useState } from "react";
import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { industrialTools, loadRobot, surfaceTexture } from "./industrialDetails";
import { RectAreaLightUniformsLib } from "three/addons/lights/RectAreaLightUniformsLib.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { uniqueEdges } from "./featureEdges";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";
import { createWorkcellBackdrop } from "./WorkcellBackdrop";
import {
  type Pose,
  referencePose,
  fixtureParent,
  poseFromMatrix,
  difference,
} from "./poseMath";
export default function PoseScene({
  pose,
  onChange,
  mode,
  laser,
  resetView = 0,
  editable = false,
  showEstimate = true,
  showReference = false,
  previewCanvas,
}: {
  pose: Pose;
  onChange?: (p: Pose) => void;
  mode: "translate" | "rotate";
  laser: boolean;
  resetView?: number;
  editable?: boolean;
  showEstimate?: boolean;
  showReference?: boolean;
  previewCanvas?: { current: HTMLCanvasElement | null };
}) {
  const [failure, setFailure] = useState("");
  const host = useRef<HTMLDivElement>(null),
    state = useRef<{
      part: T.Group;
      observed: T.Group;
      overlayMaterial: T.LineBasicMaterial;
      tintMaterial: T.MeshBasicMaterial;
      gizmo: TransformControls;
      guide: T.Group;
      outline: T.Group;
      reset: () => void;
      invalidate: () => void;
      updateGuide: () => void;
      updatePreview: () => void;
      previewPart: T.Group;
      previewOutline: T.Group;
      stationary: () => number[][];
    } | null>(null),
    callback = useRef(onChange);
  callback.current = onChange;
  useEffect(() => {
    const el = host.current!,
      scene = new T.Scene();
    scene.background = new T.Color("#3d4953");
    scene.fog = new T.Fog("#3d4953", 3.2, 7.0);
    const camera = new T.PerspectiveCamera(36, 1, 0.01, 10);
    camera.up.set(0, 0, 1);
    let renderer: T.WebGLRenderer;
    try {
      renderer = new T.WebGLRenderer({
        antialias: true,
        preserveDrawingBuffer: true,
      });
    } catch {
      setFailure("WebGL unavailable. Numeric pose controls remain available.");
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = T.VSMShadowMap;
    renderer.shadowMap.autoUpdate = false;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.outputColorSpace = T.SRGBColorSpace;
    renderer.toneMappingExposure = 1.0;
    el.appendChild(renderer.domElement);
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping = true;
    const reset = () => {
      // Flush residual pan/rotation inertia before restoring the inspection view.
      const damping = orbit.enableDamping;
      orbit.enableDamping = false;
      orbit.update();
      camera.position.set(0.92, -1.24, 1.07);
      orbit.target.set(0.28, 0, 0.63);
      orbit.update();
      orbit.enableDamping = damping;
    };
    reset();
    scene.environmentIntensity = .65;
    // Three samples environment directions in a left-handed Y-up frame. The
    // YXZ order keeps source +Y aligned with scene +Z while yawing the workshop.
    scene.environmentRotation.set(Math.PI / 2, 2.6, 0,"YXZ");
    RectAreaLightUniformsLib.init();
    const key = new T.RectAreaLight("#fff3e4", 3.1, 1.5, 1.0);
    key.position.set(-.25, -.8, 1.5);
    key.lookAt(0.25, 0, 0.65);
    scene.add(key);
    const fill = new T.RectAreaLight("#e1e7eb", 1.2, 1.0, 0.9);
    fill.position.set(1.1, 0.5, 1.0);
    fill.lookAt(0.25, 0, 0.6);
    scene.add(fill);
    const rim = new T.DirectionalLight("#d2e0e8", 0.5);
    rim.position.set(-0.5, 0.6, 1.3);
    scene.add(rim);
    scene.add(new T.HemisphereLight("#d5e2eb", "#25272b", 0.25));
    // Low-energy shadow key supplements the broad area lights.
    const light = new T.DirectionalLight("#fff3e4", .7);
    light.position.set(-.3, -.2, 2.2);
    light.castShadow = true;
    light.shadow.mapSize.set(512, 512);
    light.shadow.intensity = .32;
    light.shadow.blurSamples = 8;
    light.shadow.camera.left = -1;
    light.shadow.camera.right = 1;
    light.shadow.camera.top = 1;
    light.shadow.camera.bottom = -1;
    light.shadow.bias = -0.0002;
    light.shadow.normalBias = 0.002;
    light.shadow.radius = 6;
    scene.add(light);
    const paint = new T.MeshPhysicalMaterial({
        color: "#c7c1b1",
        metalness: 0.02,
        roughness: 0.57,
        clearcoat: .22,
        clearcoatRoughness: .38,
        envMapIntensity: 0.8,
      }),
      metal = new T.MeshStandardMaterial({
        color: "#9ba2a8",
        metalness: 0.9,
        roughness: 0.52,
        envMapIntensity: 1.15,
      }),
      dark = new T.MeshStandardMaterial({
        color: "#24292d",
        metalness: 0.45,
        roughness: 0.5,
      }),
      black = new T.MeshStandardMaterial({
        color: "#080d12",
        metalness: 0,
        roughness: 0.86,
      }),
      steel = new T.MeshStandardMaterial({
        color: "#636c73",
        metalness: 0.85,
        roughness: 0.38,
      }),
      bench = new T.MeshStandardMaterial({
        color: "#171e24",
        metalness: 0.25,
        roughness: 0.7,
        envMapIntensity: 0.5,
      });
    const fixture = new T.Group();
    fixture.applyMatrix4(fixtureParent);
    scene.add(fixture);
    const mesh = (
      g: T.BufferGeometry,
      m: T.Material,
      parent: T.Object3D,
      pos: number[],
    ) => {
      const o = new T.Mesh(g, m);
      o.position.fromArray(pos);
      o.castShadow = true;
      o.receiveShadow = true;
      parent.add(o);
      return o;
    };
    const box = (
      parent: T.Object3D,
      size: [number, number, number],
      pos: number[],
      mat: T.Material,
    ) => mesh(new RoundedBoxGeometry(...size, 3, 0.003), mat, parent, pos);
    const tools = industrialTools({paint, metal, dark, black, steel});
    const textures: T.Texture[] = [surfaceTexture("paint"), surfaceTexture("metal"), surfaceTexture("bench")];
    textures.forEach(texture=>{texture.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());});
    paint.roughnessMap = textures[0]; paint.bumpMap = textures[0]; paint.bumpScale = 0.00006;
    metal.roughnessMap = textures[1]; metal.bumpMap = textures[1]; metal.bumpScale = 0.000025;
    bench.color.set("#363f47"); bench.metalness = .82; bench.roughness = .72;
    bench.envMapIntensity = .4;
    bench.roughnessMap = textures[2]; bench.bumpMap = textures[2]; bench.bumpScale = 0.00003;
    const cyl = (
      parent: T.Object3D,
      r: number,
      len: number,
      pos: number[],
      mat: T.Material,
      axis = "z",
    ) => {
      const o = mesh(new T.CylinderGeometry(r, r, len, 64), mat, parent, pos);
      o.rotation.z = axis === "x" ? Math.PI / 2 : 0;
      o.rotation.x = axis === "z" ? Math.PI / 2 : 0;
      return o;
    };
    // Through-holes with bevelled openings and visible dark bore walls.
    const plate = new T.Shape();
    plate.moveTo(-.75,-.55);plate.lineTo(.95,-.55);plate.lineTo(.95,.55);plate.lineTo(-.75,.55);plate.closePath();
    for (let x=-.65;x<.9;x+=.12) for(let y=-.45;y<.5;y+=.12) {
      const hole = new T.Path();hole.absarc(x,y,.007,0,Math.PI*2,true);plate.holes.push(hole);
    }
    mesh(new T.ExtrudeGeometry(plate,{depth:.045,bevelEnabled:true,bevelSize:.001,
      bevelThickness:.001,bevelSegments:2,curveSegments:8}),bench,fixture,[0,0,-.047]);
    box(fixture,[1.7,1.1,.012],[.1,0,-.063],black);
    box(fixture,[.39,.29,.018],[-.22,0,.007],steel);
    // The existing asset's base is at z=.055. A physical 39 mm mounting plinth
    // bridges the support plate at .016 without moving the robot or its wrist.
    box(fixture,[.31,.24,.037],[-.245,0,.0345],dark);
    box(fixture,[.31,.24,.002],[-.245,0,.054],black);
    for(const x of [-.38,-.06]) for(const y of [-.11,.11]) tools.socket(fixture,[x,y,.018],"z",.006);
    const flange = (parent: T.Object3D, x: number, female: boolean) => {
      const ring = new T.Shape();
      ring.absarc(0, 0, 0.078, 0, Math.PI * 2, false);
      const hole = new T.Path();
      hole.absarc(0, 0, 0.029, 0, Math.PI * 2, true);
      ring.holes.push(hole);
      if (female) {
        for (let i = 0; i < 6; i++) {
          const a = (i * Math.PI) / 3,
            h = new T.Path();
          h.absarc(
            -Math.cos(a) * 0.057,
            Math.sin(a) * 0.057,
            0.0065,
            0,
            Math.PI * 2,
            true,
          );
          ring.holes.push(h);
        }
        const key = new T.Path();
        key.absarc(-0.037, 0.026, 0.0055, 0, Math.PI * 2, true);
        ring.holes.push(key);
      }
      const o = mesh(
        new T.ExtrudeGeometry(ring, {
          depth: 0.024,
          bevelEnabled: true,
          bevelSize: 0.0003,
          bevelThickness: 0.0003,
          bevelSegments: 2,
          curveSegments: 64,
        }),
        metal,
        parent,
        [female ? x : x - 0.024, 0, 0],
      );
      o.rotation.y = Math.PI / 2;
      if (!female) {
        for (let i = 0; i < 6; i++) {
          const a = (i * Math.PI) / 3;
          cyl(
            parent,
            0.006,
            0.012,
            [x + 0.006, Math.sin(a) * 0.057, Math.cos(a) * 0.057],
            steel,
            "x",
          );
        }
        cyl(parent, 0.005, 0.014, [x + 0.007, 0.026, 0.037], metal, "x");
      }
    };
    const wrist = new T.Group();
    wrist.position.set(0.39, 0, 0.69);
    fixture.add(wrist);
    flange(wrist, 0, false);
    tools.cable(fixture,[[.37,.065,.745],[.31,.11,.78],[.16,.12,.78],[-.1,.1,.83],[-.23,.1,.72]],.007);
    const observed = new T.Group();
    fixture.add(observed);
    const localReference = poseFromMatrix(
      fixtureParent
        .clone()
        .invert()
        .multiply(
          new T.Matrix4().compose(
            new T.Vector3().fromArray(referencePose().p),
            new T.Quaternion().fromArray(referencePose().q),
            new T.Vector3(1, 1, 1),
          ),
        ),
    );
    observed.position.fromArray(localReference.p);
    observed.quaternion.fromArray(localReference.q);
    flange(observed, -0.055, true);
    tools.gripper(observed);
    const labelCanvas = document.createElement("canvas");
    labelCanvas.width = 512;
    labelCanvas.height = 128;
    const ctx = labelCanvas.getContext("2d")!;
    ctx.font = "bold 54px Arial";
    ctx.fillStyle = "#18262d";
    ctx.textAlign = "center";
    ctx.fillText("AUTOFRAME", 256, 78);
    const labelTexture = new T.CanvasTexture(labelCanvas);
    labelTexture.colorSpace = T.SRGBColorSpace;
    const label = mesh(
      new T.PlaneGeometry(0.039, 0.009),
      new T.MeshBasicMaterial({
        map: labelTexture,
        transparent: true,
        depthWrite: false,
      }),
      observed,
      [0.051, -0.0586, 0],
    );
    label.rotation.x = Math.PI / 2;
    const overlayMaterial = new T.LineBasicMaterial({
      color: "#e8a13b",
      transparent: true,
      opacity: 0.83,
      depthWrite: false,
      depthTest: true,
      toneMapped: false,
    });
    const tintMaterial = new T.MeshBasicMaterial({
      color: "#f5a623",
      transparent: true,
      opacity: 0.035,
      toneMapped: false,
      depthWrite: false,
      polygonOffset: true,
      polygonOffsetFactor: -1,
    });
    // Bake only asset-local transforms; pose remains exclusively on the instance group.
    // Two shared buffers replace per-fastener overlay draw calls.
    const fills: T.BufferGeometry[] = [], edges: T.BufferGeometry[] = [];
    observed.traverse(o=>{
      if (!(o instanceof T.Mesh) || o === label) return;
      o.updateMatrix();
      const fill = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
      for (const name of Object.keys(fill.attributes)) if(name !== "position") fill.deleteAttribute(name);
      fill.applyMatrix4(o.matrix); fills.push(fill);
      if(o.userData.featureEdge !== false)
        edges.push(new T.EdgesGeometry(o.geometry,28).applyMatrix4(o.matrix));
    });
    const fillGeometry = mergeGeometries(fills), edgeGeometry = uniqueEdges(edges);
    fills.forEach(g=>g.dispose()); edges.forEach(g=>g.dispose());
    // Consolidate stationary detail by finish. Socket heads and jaw grooves retain
    // their exact vertices, but no longer require separate visible draw calls.
    const replacedGeometries = new Set<T.BufferGeometry>();
    const finishBuckets = new Map<T.Material,T.BufferGeometry[]>();
    for (const o of [...observed.children]) {
      if (!(o instanceof T.Mesh) || o === label || Array.isArray(o.material)) continue;
      replacedGeometries.add(o.geometry);
      const g = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
      g.applyMatrix4(o.matrix);
      if(!finishBuckets.has(o.material)) finishBuckets.set(o.material,[]);
      finishBuckets.get(o.material)!.push(g); observed.remove(o);
    }
    for(const [material,geometries] of finishBuckets) {
      const o = new T.Mesh(mergeGeometries(geometries),material);
      o.castShadow=o.receiveShadow=true;observed.add(o);
      geometries.forEach(g=>g.dispose());
    }
    const solidPositions=new Set<string>();let solidVertices=0;
    observed.traverse(o=>{
      if(!(o instanceof T.Mesh)||o===label)return;
      const p=o.geometry.getAttribute("position");solidVertices+=p.count;
      for(let i=0;i<p.count;i++)solidPositions.add(`${p.getX(i)},${p.getY(i)},${p.getZ(i)}`);
    });
    const overlayPositions=fillGeometry.getAttribute("position");let missingVertices=0;
    for(let i=0;i<overlayPositions.count;i++)
      if(!solidPositions.has(`${overlayPositions.getX(i)},${overlayPositions.getY(i)},${overlayPositions.getZ(i)}`))missingVertices++;
    el.dataset.geometryProof=JSON.stringify({solidVertices,overlayVertices:overlayPositions.count,missingVertices});
    const makeOverlay = (
      lineMaterial: T.LineBasicMaterial,
      tint?: T.MeshBasicMaterial,
    ) => {
      const group = new T.Group();
      if(tint) {
        const depth = new T.Mesh(fillGeometry,new T.MeshBasicMaterial({colorWrite:false,
          depthWrite:true,polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1}));
        depth.renderOrder=1;group.add(depth);
        const fill=new T.Mesh(fillGeometry,tint);fill.renderOrder=2;group.add(fill);
      }
      const edge = new T.LineSegments(edgeGeometry,lineMaterial);
      edge.renderOrder = 3; group.add(edge);
      scene.add(group);
      return group;
    };
    const part = makeOverlay(overlayMaterial, tintMaterial);
    const outline = makeOverlay(
      new T.LineBasicMaterial({
        color: "#06bdd2",
        transparent: true,
        opacity: 0.48,
        depthWrite: false,
        toneMapped: false,
      }),
    );
    outline.position.fromArray(referencePose().p);
    outline.quaternion.fromArray(referencePose().q);
    // One renderer, shared geometry/materials, one pose state. Only the tool is
    // drawn for the thumbnail; the robot/workshop are never redrawn for it.
    const previewScene = new T.Scene();
    previewScene.background = new T.Color("#454f58");
    previewScene.environment = scene.environment;
    previewScene.environmentIntensity = scene.environmentIntensity;
    previewScene.environmentRotation.copy(scene.environmentRotation);
    scene.children.filter(o=>o instanceof T.Light).forEach(o=>{
      const light=o.clone() as T.Light;light.castShadow=false;previewScene.add(light);
    });
    const previewFixture=new T.Group();previewFixture.applyMatrix4(fixtureParent);
    previewFixture.add(observed.clone(),wrist.clone());previewScene.add(previewFixture);
    const previewPart=part.clone(), previewOutline=outline.clone();
    previewScene.add(previewPart,previewOutline);
    const previewCamera=new T.PerspectiveCamera(36,320/176,.01,4);
    previewCamera.up.set(0,0,1);previewCamera.position.set(.77,-.36,.91);
    previewCamera.lookAt(.55,0,.72);
    const previewTarget=new T.WebGLRenderTarget(320,176);
    previewTarget.texture.colorSpace=T.SRGBColorSpace;
    const previewPixels=new Uint8Array(320*176*4);
    const previewImage=new ImageData(320,176);
    const workcell=createWorkcellBackdrop(renderer);
    const backdrop=workcell.createView(),previewBackdrop=workcell.createView();
    scene.background=backdrop.texture;previewScene.background=previewBackdrop.texture;
    scene.fog=null;
    const scannerStart=fixture.children.length;
    const scanner = new T.Group();
    scanner.position.set(-.35, -.08, .87);
    scanner.quaternion.setFromUnitVectors(new T.Vector3(1,0,0),
      new T.Vector3(.52,0,.69).sub(scanner.position).normalize());
    fixture.add(scanner);
    tools.scanner(scanner);
    tools.cylinder(fixture,.008,.8,[-.38,.005,.4],steel,"z");
    tools.box(fixture,[.09,.09,.022],[-.38,.005,.012],dark);
    tools.box(fixture,[.07,.045,.055],[-.38,.005,.825],steel);
    tools.cable(fixture,[[-.42,.005,.85],[-.48,.01,.78],[-.43,.01,.42],[-.44,.01,.04]],.004);
    const contactCanvas=document.createElement("canvas");contactCanvas.width=contactCanvas.height=128;
    const contactContext=contactCanvas.getContext("2d")!;
    const contactGradient=contactContext.createRadialGradient(64,64,24,64,64,64);
    contactGradient.addColorStop(0,"rgba(255,255,255,1)");
    contactGradient.addColorStop(1,"rgba(255,255,255,0)");
    contactContext.fillStyle=contactGradient;contactContext.fillRect(0,0,128,128);
    const contactTexture=new T.CanvasTexture(contactCanvas);contactTexture.colorSpace=T.SRGBColorSpace;
    textures.push(contactTexture);
    const contactMaterial=new T.MeshBasicMaterial({color:"#10171c",map:contactTexture,
      transparent:true,opacity:.3,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-1});
    for(const [width,height,x,y] of [[.45,.35,-.22,0],[.14,.14,-.38,.005]]) {
      const shadow=mesh(new T.PlaneGeometry(width,height),contactMaterial,fixture,[x,y,-.0008]);
      shadow.castShadow=false;shadow.renderOrder=1;
    }
    fixture.children.slice(scannerStart).forEach(o=>o.traverse(child=>{
      if(child instanceof T.Mesh)child.castShadow=false;
    }));
    let robotGroup:T.Group|null=null;
    const stationary=()=>{
      fixture.updateMatrixWorld(true);
      return [fixture,wrist,scanner,robotGroup].filter((o):o is T.Group=>o!==null)
        .map(o=>o.matrixWorld.toArray());
    };
    const guide = new T.Group();
    fixture.add(guide);
    fixture.updateMatrixWorld(true);
    const origin = scanner.localToWorld(new T.Vector3(0.056, 0, 0)),
      ray = new T.Raycaster();
    const solids = fixture.children.filter(
      (o) => o instanceof T.Mesh || o === wrist || o === observed,
    );
    const updateGuide = () => {
      fixture.updateMatrixWorld(true);
      guide.children.forEach((o) => {
        if (o instanceof T.Line) {
          o.geometry.dispose();
          (o.material as T.Material).dispose();
        }
      });
      guide.clear();
      for (let i = 0; i < 5; i++) {
        const a = (i / 5) * Math.PI * 2,
          aim = new T.Vector3(
            0.5,
            Math.sin(a) * 0.045,
            0.69 + Math.cos(a) * 0.035,
          );
        ray.set(origin, fixture.localToWorld(aim).sub(origin).normalize());
        const hits = ray.intersectObjects(solids, true);
        if (hits[0])
          guide.add(
            new T.Line(
              new T.BufferGeometry().setFromPoints([
                fixture.worldToLocal(origin.clone()), fixture.worldToLocal(hits[0].point.clone()),
              ]),
              new T.LineBasicMaterial({
                color: "#008fa8",
                transparent: true,
                opacity: 0.25,
                toneMapped: false,
              }),
            ),
          );
      }
    };
    const axes = new T.AxesHelper(0.09);
    axes.position.set(0.53, -0.07, 0.58);
    fixture.add(axes);
    let dirty = true, previewDirty=true, backdropDirty=true,previewBackdropDirty=true,
      id = 0, disposed = false, renderCount = 0, previewCount=0;
    const invalidate = () => {
      dirty = true;
      if (!id && !document.hidden && !disposed) id = requestAnimationFrame(draw);
    };
    const gizmo = new TransformControls(camera, renderer.domElement);
    gizmo.setSpace("world");
    gizmo.setSize(0.7);
    gizmo.attach(part);
    scene.add(gizmo.getHelper());
    gizmo.enabled = editable;
    gizmo.getHelper().visible = editable && showEstimate;
    gizmo.addEventListener("dragging-changed", (e) => {
      orbit.enabled = !e.value;
    });
    gizmo.addEventListener("change", invalidate);
    orbit.addEventListener("change",()=>{backdropDirty=true;invalidate();});
    gizmo.addEventListener("objectChange", () =>
      callback.current?.({
        p: part.position.toArray(),
        q: part.quaternion.toArray(),
      }),
    );
    state.current = {
      part,
      observed,
      overlayMaterial,
      tintMaterial,
      gizmo,
      guide,
      outline,
      reset,
      invalidate,
      updateGuide,
      updatePreview:()=>{previewDirty=true;invalidate();},
      previewPart,
      previewOutline,
      stationary,
    };
    const resize = new ResizeObserver(() => {
      renderer.setSize(el.clientWidth, el.clientHeight);
      camera.aspect = el.clientWidth / Math.max(1, el.clientHeight);
      camera.fov = camera.aspect < 1.1 ? 55 : 36;
      camera.updateProjectionMatrix();
      backdropDirty=true;
      invalidate();
    });
    resize.observe(el);
    const draw = () => {
      id = 0;
      if (document.hidden || disposed) return;
      const changed = orbit.update();
      if (dirty) {
        const start = performance.now();
        renderer.shadowMap.enabled=false;
        if(backdropDirty){backdrop.render(camera,el.clientWidth,el.clientHeight);backdropDirty=false;}
        if(previewBackdropDirty){previewBackdrop.render(previewCamera,320,176);previewBackdropDirty=false;}
        renderer.shadowMap.enabled=true;
        const thumbnail=previewCanvas?.current;
        if(previewDirty && thumbnail) {
          renderer.shadowMap.enabled=false;
          renderer.setRenderTarget(previewTarget);
          renderer.render(previewScene,previewCamera);
          renderer.readRenderTargetPixels(previewTarget,0,0,320,176,previewPixels);
          for(let y=0;y<176;y++)previewImage.data.set(
            previewPixels.subarray((175-y)*320*4,(176-y)*320*4),y*320*4);
          thumbnail.getContext("2d")?.putImageData(previewImage,0,0);
          thumbnail.dataset.frame=String(++previewCount);
          renderer.setRenderTarget(null);
          renderer.setViewport(0,0,el.clientWidth,el.clientHeight);
          renderer.shadowMap.enabled=true;previewDirty=false;
        }
        renderer.render(scene, camera);
        el.dataset.renderStats = JSON.stringify({frame:++renderCount,triangles:renderer.info.render.triangles,
          calls:renderer.info.render.calls,geometries:renderer.info.memory.geometries,
          textures:renderer.info.memory.textures,lastRenderMs:performance.now()-start,
          cameraPosition:camera.position.toArray(),orbitTarget:orbit.target.toArray()});
        dirty = false;
      }
      if (changed && !id) id = requestAnimationFrame(draw);
    };
    const visibility = () => {
      cancelAnimationFrame(id); id = 0;
      if (!document.hidden) invalidate();
    };
    const abort = new AbortController();
    let workshopTexture:T.DataTexture|null=null, workshopEnvironment:T.WebGLRenderTarget|null=null;
    fetch("assets/industrial/foundry_1k.hdr",{signal:abort.signal}).then(r=>{
      if(!r.ok)throw new Error("Workshop environment unavailable");return r.arrayBuffer();
    }).then(buffer=>{
      if(disposed)return;
      const decoded=new HDRLoader().parse(buffer);
      // Muted industrial greys, preserving linear luminance and dynamic range.
      // The same texture lights the materials and supplies the distant backdrop.
      for(let i=0;i<decoded.data.length;i+=4) {
        const r=T.DataUtils.fromHalfFloat(decoded.data[i]),g=T.DataUtils.fromHalfFloat(decoded.data[i+1]),
          b=T.DataUtils.fromHalfFloat(decoded.data[i+2]),l=.2126*r+.7152*g+.0722*b;
        decoded.data[i]=T.DataUtils.toHalfFloat(l+(r-l)*.1);
        decoded.data[i+1]=T.DataUtils.toHalfFloat(l+(g-l)*.1);
        decoded.data[i+2]=T.DataUtils.toHalfFloat(l+(b-l)*.1);
      }
      const hdr=new T.DataTexture(decoded.data,decoded.width,decoded.height,
        T.RGBAFormat,T.HalfFloatType);
      hdr.colorSpace=T.LinearSRGBColorSpace;hdr.mapping=T.EquirectangularReflectionMapping;
      hdr.flipY=true;hdr.minFilter=T.LinearFilter;hdr.magFilter=T.LinearFilter;
      hdr.needsUpdate=true;
      const generator=new T.PMREMGenerator(renderer);
      workshopEnvironment=generator.fromEquirectangular(hdr);generator.dispose();workshopTexture=hdr;
      scene.environment=workshopEnvironment.texture;scene.environmentIntensity=.85;
      previewScene.environment=scene.environment;previewScene.environmentIntensity=scene.environmentIntensity;
      workcell.setEnvironment(workshopEnvironment.texture,scene.environmentRotation);
      el.dataset.environmentAsset=JSON.stringify({width:decoded.width,height:decoded.height,bytes:buffer.byteLength});
      previewDirty=true;backdropDirty=true;previewBackdropDirty=true;invalidate();
    }).catch(error=>{
      if(!abort.signal.aborted)setFailure(`Workshop environment could not load: ${String(error)}`);
    });
    loadRobot({paint,metal,dark,black,steel},abort.signal).then(robot=>{
      if(disposed) {robot.traverse(o=>{if(o instanceof T.Mesh)o.geometry.dispose();});return;}
      fixture.add(robot); solids.push(robot);robotGroup=robot;
      el.dataset.stationaryTransforms=JSON.stringify(stationary());
      renderer.shadowMap.needsUpdate=true;
      el.dataset.robotAsset = JSON.stringify(robot.userData.asset);
      updateGuide(); invalidate();
    }).catch(error=>{
      if(!abort.signal.aborted) setFailure(`Industrial robot asset could not load: ${String(error)}`);
    });
    document.addEventListener("visibilitychange", visibility);
    visibility();
    return () => {
      disposed = true; abort.abort();
      cancelAnimationFrame(id);
      document.removeEventListener("visibilitychange", visibility);
      resize.disconnect();
      gizmo.dispose();
      orbit.dispose();
      const geometries = new Set<T.BufferGeometry>(), materials = new Set<T.Material>();
      replacedGeometries.forEach(g=>geometries.add(g));
      scene.traverse(o=>{
        if(o instanceof T.Mesh || o instanceof T.Line) {
          geometries.add(o.geometry);
          (Array.isArray(o.material)?o.material:[o.material]).forEach(m=>materials.add(m));
        }
      });
      light.shadow.map?.dispose();light.shadow.mapPass?.dispose();
      previewTarget.dispose();
      workcell.dispose();
      workshopTexture?.dispose();workshopEnvironment?.dispose();
      geometries.forEach(g=>g.dispose()); materials.forEach(m=>m.dispose());
      textures.forEach(t=>t.dispose());
      labelTexture.dispose();
      renderer.dispose();
      el.replaceChildren();
      state.current = null;
    };
  }, []);
  useEffect(() => {
    const s = state.current;
    if (s) {
      s.part.position.fromArray(pose.p);
      s.part.quaternion.fromArray(pose.q);
      s.gizmo.setMode(mode);
      s.guide.visible = laser;
      s.outline.visible = showReference;
      s.part.visible = showEstimate;
      s.gizmo.enabled = editable && showEstimate;
      s.gizmo.getHelper().visible = editable && showEstimate;
      const aligned = difference(pose).aligned;
      s.overlayMaterial.color.set(aligned ? "#06bdd2" : "#f5a623");
      s.tintMaterial.color.copy(s.overlayMaterial.color);
      s.part.updateMatrixWorld(true);
      s.previewPart.position.copy(s.part.position);s.previewPart.quaternion.copy(s.part.quaternion);
      s.previewPart.visible=showEstimate;s.previewOutline.visible=showReference;
      s.previewPart.updateMatrixWorld(true);
      s.observed.updateWorldMatrix(true, false);
      if (host.current) {
        host.current.dataset.stationaryTransforms=JSON.stringify(s.stationary());
        host.current.dataset.gizmoVisible=String(s.gizmo.getHelper().visible);
        host.current.dataset.observedTransform = JSON.stringify(
          s.observed.matrixWorld.toArray(),
        );
        host.current.dataset.estimateTransform = JSON.stringify(
          s.part.matrixWorld.toArray(),
        );
      }
      if(previewCanvas?.current) {
        previewCanvas.current.dataset.estimateTransform=JSON.stringify(s.previewPart.matrixWorld.toArray());
        previewCanvas.current.dataset.observedTransform=JSON.stringify(s.observed.matrixWorld.toArray());
      }
      // Stationary scanner and observed geometry: pose playback never rebuilds the guide.
      s.updatePreview();
    }
  }, [pose, mode, laser, editable, showEstimate, showReference]);
  useEffect(() => state.current?.reset(), [resetView]);
  return (
    <div className="pose-canvas" ref={host}>
      {failure && (
        <p
          role="alert"
          style={{ position: "absolute", top: "40%", padding: 24 }}
        >
          {failure}
        </p>
      )}
    </div>
  );
}
