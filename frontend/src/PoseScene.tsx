import { useEffect, useRef, useState } from "react";
import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { RectAreaLightUniformsLib } from "three/addons/lights/RectAreaLightUniformsLib.js";
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
    renderer.shadowMap.type = T.PCFShadowMap;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.outputColorSpace = T.SRGBColorSpace;
    renderer.toneMappingExposure = 1.0;
    el.appendChild(renderer.domElement);
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping = true;
    const reset = () => {
      camera.position.set(0.98, -1.24, 1.06);
      orbit.target.set(0.31, 0, 0.64);
      orbit.update();
    };
    reset();
    const pm = new T.PMREMGenerator(renderer),
      room = new RoomEnvironment(),
      env = pm.fromScene(room, 0.04);
    scene.environment = env.texture;
    scene.environmentIntensity = 0.85;
    room.dispose();
    pm.dispose();
    RectAreaLightUniformsLib.init();
    const key = new T.RectAreaLight("#fff0dc", 4.5, 1.2, 0.8);
    key.position.set(0.2, -1.0, 1.45);
    key.lookAt(0.25, 0, 0.65);
    scene.add(key);
    const fill = new T.RectAreaLight("#d3e4f2", 1.8, 0.8, 0.9);
    fill.position.set(1.1, 0.5, 1.0);
    fill.lookAt(0.25, 0, 0.6);
    scene.add(fill);
    const rim = new T.DirectionalLight("#b9d6e6", 0.7);
    rim.position.set(-0.5, 0.6, 1.3);
    scene.add(rim);
    scene.add(new T.HemisphereLight("#d5e2eb", "#25272b", 0.45));
    // Low-energy shadow key supplements the broad area lights.
    const light = new T.DirectionalLight("#fff0dd", 0.85);
    light.position.set(0.2, -0.5, 1.8);
    light.castShadow = true;
    light.shadow.mapSize.set(2048, 2048);
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
    for (const x of [-0.63, -0.12, 0.39]) {
      box(scene, [0.45, 0.12, 0.81], [x, 1.15, 0.4], workshop);
      for (const z of [0.14, 0.39, 0.64])
        box(scene, [0.4, 0.009, 0.005], [x, 1.083, z], trim);
      box(scene, [0.014, 0.012, 0.085], [x + 0.13, 1.08, 0.49], trim);
    }
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
    const link = (a: number[], b: number[], r: number) => {
      const start = new T.Vector3().fromArray(a),
        end = new T.Vector3().fromArray(b),
        dir = end.clone().sub(start);
      const o = mesh(
        new T.CapsuleGeometry(r, dir.length() - 2 * r, 12, 32),
        paint,
        fixture,
        start.clone().add(end).multiplyScalar(0.5).toArray(),
      );
      o.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), dir.normalize());
    };
    box(fixture, [1.7, 1.1, 0.055], [0.1, 0, -0.03], bench);
    for (let x = -0.65; x < 0.9; x += 0.14)
      for (let y = -0.45; y < 0.5; y += 0.14)
        cyl(fixture, 0.004, 0.001, [x, y, -0.001], black);
    cyl(fixture, 0.18, 0.055, [-0.28, 0, 0.03], metal);
    cyl(fixture, 0.135, 0.16, [-0.28, 0, 0.12], paint);
    cyl(fixture, 0.112, 0.2, [-0.28, 0, 0.22], dark, "y");
    link([-0.28, 0, 0.23], [-0.4, 0, 0.54], 0.095);
    cyl(fixture, 0.105, 0.19, [-0.4, 0, 0.54], dark, "y");
    cyl(fixture, 0.081, 0.197, [-0.4, 0, 0.54], metal, "y");
    link([-0.4, 0, 0.54], [0.12, 0, 0.69], 0.09);
    cyl(fixture, 0.095, 0.18, [0.12, 0, 0.69], dark, "x");
    cyl(fixture, 0.085, 0.16, [0.24, 0, 0.69], paint, "x");
    cyl(fixture, 0.082, 0.04, [0.345, 0, 0.69], dark, "x");
    for (const [x, z, r] of [
      [-0.28, 0.22, 0.083],
      [-0.4, 0.54, 0.073],
    ]) {
      for (let i = 0; i < 8; i++) {
        const a = (i * Math.PI) / 4;
        cyl(
          fixture,
          0.004,
          0.008,
          [x + Math.sin(a) * r, -0.104, z + Math.cos(a) * r],
          steel,
          "y",
        );
      }
      cyl(fixture, 0.043, 0.012, [x, -0.106, z], paint, "y");
      cyl(fixture, 0.018, 0.014, [x, -0.115, z], dark, "y");
    }
    for (let i = 0; i < 8; i++) {
      const a = (i * Math.PI) / 4;
      cyl(
        fixture,
        0.006,
        0.008,
        [-0.28 + Math.sin(a) * 0.15, Math.cos(a) * 0.15, 0.061],
        steel,
      );
    }
    for (const x of [0.19, 0.29])
      cyl(fixture, 0.087, 0.009, [x, 0, 0.69], metal, "x");
    const cable = new T.CatmullRomCurve3([
      new T.Vector3(-0.28, 0.12, 0.12),
      new T.Vector3(-0.48, 0.12, 0.35),
      new T.Vector3(-0.48, 0.12, 0.6),
      new T.Vector3(-0.2, 0.12, 0.72),
      new T.Vector3(0.2, 0.07, 0.75),
    ]);
    mesh(
      new T.TubeGeometry(cable, 70, 0.012, 10, false),
      black,
      fixture,
      [0, 0, 0],
    );
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
    cyl(observed, 0.07, 0.025, [-0.018, 0, 0], dark, "x");
    box(observed, [0.105, 0.11, 0.1], [0.045, 0, 0], metal);
    box(observed, [0.023, 0.118, 0.105], [0.105, 0, 0], dark);
    for (const y of [-0.038, 0.038]) {
      box(observed, [0.08, 0.029, 0.076], [0.15, y, 0], dark);
      box(observed, [0.07, 0.019, 0.052], [0.217, y, 0], metal);
      for (const z of [-0.032, 0.032])
        cyl(observed, 0.004, 0.004, [0.06, y * 1.5, z], dark, "y");
    }
    // Every instance uses the exact observed mesh buffers and local transforms.
    for (const x of [0.012, 0.079])
      for (const z of [-0.034, 0.034]) {
        cyl(observed, 0.007, 0.002, [x, -0.056, z], black, "y");
        cyl(observed, 0.0036, 0.003, [x, -0.058, z], metal, "y");
      }
    const labelCanvas = document.createElement("canvas");
    labelCanvas.width = 512;
    labelCanvas.height = 128;
    const ctx = labelCanvas.getContext("2d")!;
    ctx.font = "bold 54px Arial";
    ctx.fillStyle = "#18262d";
    ctx.textAlign = "center";
    ctx.fillText("AUTOFRAME", 256, 78);
    const labelTexture = new T.CanvasTexture(labelCanvas);
    const label = mesh(
      new T.PlaneGeometry(0.074, 0.018),
      new T.MeshBasicMaterial({
        map: labelTexture,
        transparent: true,
        depthWrite: false,
      }),
      observed,
      [0.045, -0.057, 0],
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
    const makeOverlay = (
      lineMaterial: T.LineBasicMaterial,
      tint?: T.MeshBasicMaterial,
    ) => {
      const group = new T.Group();
      observed.traverse((o) => {
        if (o instanceof T.Mesh && o !== label) {
          if (tint) {
            const fill = new T.Mesh(o.geometry, tint);
            fill.position.copy(o.position);
            fill.quaternion.copy(o.quaternion);
            group.add(fill);
          }
          const edge = new T.LineSegments(
            new T.EdgesGeometry(o.geometry, 12),
            lineMaterial,
          );
          edge.position.copy(o.position);
          edge.quaternion.copy(o.quaternion);
          edge.renderOrder = 2;
          group.add(edge);
        }
      });
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
    scanner.position.set(0.6, 0.2, 0.88);
    scanner.quaternion.setFromUnitVectors(
      new T.Vector3(1, 0, 0),
      new T.Vector3(0.52, 0, 0.69).sub(scanner.position).normalize(),
    );
    fixture.add(scanner);
    box(scanner, [0.078, 0.052, 0.052], [0, 0, 0], dark);
    cyl(
      scanner,
      0.012,
      0.006,
      [0.041, 0, 0],
      new T.MeshStandardMaterial({
        color: "#06bdd2",
        emissive: "#008fa8",
        emissiveIntensity: 0.3,
        metalness: 0.3,
        roughness: 0.35,
      }),
      "x",
    );
    cyl(fixture, 0.006, 0.88, [0.6, 0.2, 0.44], dark);
    const guide = new T.Group();
    fixture.add(guide);
    fixture.updateMatrixWorld(true);
    const origin = scanner.localToWorld(new T.Vector3(0.045, 0, 0)),
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
      for (let i = 0; i < 9; i++) {
        const a = (i / 9) * Math.PI * 2,
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
              new T.BufferGeometry().setFromPoints([origin, hits[0].point]),
              new T.LineBasicMaterial({
                color: "#008fa8",
                transparent: true,
                opacity: 0.42,
                toneMapped: false,
              }),
            ),
          );
      }
    };
    const axes = new T.AxesHelper(0.09);
    axes.position.set(0.53, -0.07, 0.58);
    fixture.add(axes);
    let dirty = true;
    const invalidate = () => {
      dirty = true;
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
    let id = 0;
    const draw = () => {
      id = requestAnimationFrame(draw);
      if (!document.hidden) {
        orbit.update();
        if (dirty) {
          renderer.render(scene, camera);
          dirty = false;
        }
      }
    };
    const visibility = () => {
      cancelAnimationFrame(id);
      if (!document.hidden) draw();
    };
    document.addEventListener("visibilitychange", visibility);
    visibility();
    return () => {
      cancelAnimationFrame(id);
      document.removeEventListener("visibilitychange", visibility);
      resize.disconnect();
      gizmo.dispose();
      orbit.dispose();
      scene.traverse((o) => {
        if (o instanceof T.Mesh || o instanceof T.Line) {
          o.geometry.dispose();
          (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) =>
            m.dispose(),
          );
        }
      });
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
      if (laser) s.updateGuide();
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
