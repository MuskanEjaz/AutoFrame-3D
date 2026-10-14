import { useEffect, useRef, useState } from "react";
import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { industrialTools, loadRobot, surfaceTexture } from "./industrialDetails";
import { RectAreaLightUniformsLib } from "three/addons/lights/RectAreaLightUniformsLib.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
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
}: {
  pose: Pose;
  onChange?: (p: Pose) => void;
  mode: "translate" | "rotate";
  laser: boolean;
  resetView?: number;
  editable?: boolean;
  showEstimate?: boolean;
  showReference?: boolean;
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
    } | null>(null),
    callback = useRef(onChange);
  callback.current = onChange;
  useEffect(() => {
    const el = host.current!,
      scene = new T.Scene();
    scene.background = new T.Color("#0d1217");
    scene.fog = new T.Fog("#0d1217", 2.05, 3.5);
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
    renderer.shadowMap.type = T.PCFSoftShadowMap;
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
      camera.position.set(0.89, -1.23, 1.01);
      orbit.target.set(0.25, 0, 0.57);
      orbit.update();
      orbit.enableDamping = damping;
    };
    reset();
    const pm = new T.PMREMGenerator(renderer),
      room = new RoomEnvironment(),
      env = pm.fromScene(room, 0.04);
    scene.environment = env.texture;
    scene.environmentIntensity = 0.48;
    room.dispose();
    pm.dispose();
    RectAreaLightUniformsLib.init();
    const key = new T.RectAreaLight("#fff0dc", 3.0, 1.2, 0.8);
    key.position.set(0.2, -1.0, 1.45);
    key.lookAt(0.25, 0, 0.65);
    scene.add(key);
    const fill = new T.RectAreaLight("#d3e4f2", 1.3, 0.8, 0.9);
    fill.position.set(1.1, 0.5, 1.0);
    fill.lookAt(0.25, 0, 0.6);
    scene.add(fill);
    const rim = new T.DirectionalLight("#b9d6e6", 0.7);
    rim.position.set(-0.5, 0.6, 1.3);
    scene.add(rim);
    scene.add(new T.HemisphereLight("#d5e2eb", "#25272b", 0.25));
    // Low-energy shadow key supplements the broad area lights.
    const light = new T.DirectionalLight("#fff0dd", 2.2);
    light.position.set(0.2, -0.5, 1.8);
    light.castShadow = true;
    light.shadow.mapSize.set(1024, 1024);
    light.shadow.camera.left = -1;
    light.shadow.camera.right = 1;
    light.shadow.camera.top = 1;
    light.shadow.camera.bottom = -1;
    light.shadow.bias = -0.0002;
    light.shadow.normalBias = 0.002;
    light.shadow.radius = 4;
    scene.add(light);
    const paint = new T.MeshStandardMaterial({
        color: "#d4d0c5",
        metalness: 0.08,
        roughness: 0.38,
        envMapIntensity: 0.65,
      }),
      metal = new T.MeshStandardMaterial({
        color: "#b8bdc2",
        metalness: 0.94,
        roughness: 0.34,
        envMapIntensity: 1.15,
      }),
      dark = new T.MeshStandardMaterial({
        color: "#242a30",
        metalness: 0.32,
        roughness: 0.46,
      }),
      black = new T.MeshStandardMaterial({
        color: "#080d12",
        metalness: 0,
        roughness: 0.86,
      }),
      steel = new T.MeshStandardMaterial({
        color: "#46505a",
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
    const textures = [surfaceTexture("paint"), surfaceTexture("metal"), surfaceTexture("bench")];
    paint.roughnessMap = textures[0]; paint.bumpMap = textures[0]; paint.bumpScale = 0.00006;
    metal.roughnessMap = textures[1]; metal.bumpMap = textures[1]; metal.bumpScale = 0.000025;
    bench.color.set("#646c73"); bench.metalness = 0.8; bench.roughness = 0.48;
    bench.roughnessMap = textures[2]; bench.bumpMap = textures[2]; bench.bumpScale = 0.00003;
    const workshop = new T.MeshStandardMaterial({
      color: "#0c151c",
      metalness: 0,
      roughness: 0.9,
    });
    const trim = new T.MeshStandardMaterial({
      color: "#1c2932",
      metalness: 0.1,
      roughness: 0.8,
    });
    // Distant workshop structure, no large foreground cabinet slabs.
    box(scene, [3.4, 0.035, 1.8], [0, 2.1, 0.7], workshop);
    for (const x of [-1.3, -.7, .05, .8, 1.5])
      box(scene, [.035, .045, 1.6], [x, 1.9, .7], trim);
    for (const z of [.15, .65, 1.15])
      box(scene, [3.2, .08, .025], [0, 1.85, z], trim);
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
      color: "#f5a623",
      transparent: true,
      opacity: 0.76,
      depthWrite: false,
      depthTest: false,
      toneMapped: false,
    });
    const tintMaterial = new T.MeshBasicMaterial({
      color: "#f5a623",
      transparent: true,
      opacity: 0.055,
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
    const fillGeometry = mergeGeometries(fills), edgeGeometry = mergeGeometries(edges);
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
    const makeOverlay = (
      lineMaterial: T.LineBasicMaterial,
      tint?: T.MeshBasicMaterial,
    ) => {
      const group = new T.Group();
      if(tint) group.add(new T.Mesh(fillGeometry,tint));
      const edge = new T.LineSegments(edgeGeometry,lineMaterial);
      edge.renderOrder = 2; group.add(edge);
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
    let dirty = true, id = 0, disposed = false, renderCount = 0;
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
    orbit.addEventListener("change", invalidate);
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
    };
    const resize = new ResizeObserver(() => {
      renderer.setSize(el.clientWidth, el.clientHeight);
      camera.aspect = el.clientWidth / Math.max(1, el.clientHeight);
      camera.fov = camera.aspect < 1.1 ? 55 : 36;
      camera.updateProjectionMatrix();
      invalidate();
    });
    resize.observe(el);
    const draw = () => {
      id = 0;
      if (document.hidden || disposed) return;
      const changed = orbit.update();
      if (dirty) {
        const start = performance.now();
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
    loadRobot({paint,metal,dark,black,steel},abort.signal).then(robot=>{
      if(disposed) {robot.traverse(o=>{if(o instanceof T.Mesh)o.geometry.dispose();});return;}
      fixture.add(robot); solids.push(robot);
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
      geometries.forEach(g=>g.dispose()); materials.forEach(m=>m.dispose());
      textures.forEach(t=>t.dispose());
      labelTexture.dispose();
      env.dispose();
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
      s.observed.updateWorldMatrix(true, false);
      if (host.current) {
        host.current.dataset.observedTransform = JSON.stringify(
          s.observed.matrixWorld.toArray(),
        );
        host.current.dataset.estimateTransform = JSON.stringify(
          s.part.matrixWorld.toArray(),
        );
      }
      // Stationary scanner and observed geometry: pose playback never rebuilds the guide.
      s.invalidate();
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
