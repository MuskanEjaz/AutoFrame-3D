import { useEffect, useRef, useState } from "react";
import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { type Pose, targetPose, errors } from "./assemblyPose";
export default function AssemblyScene({
  pose,
  onChange,
  mode,
  laser,
  resetView = 0,
  preview = false,
}: {
  pose: Pose;
  onChange?: (p: Pose) => void;
  mode: "translate" | "rotate";
  laser: boolean;
  resetView?: number;
  preview?: boolean;
}) {
  const [failure, setFailure] = useState("");
  const host = useRef<HTMLDivElement>(null),
    state = useRef<{
      part: T.Group;
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
    scene.background = new T.Color("#121b22");
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
    el.appendChild(renderer.domElement);
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping = true;
    const reset = () => {
      camera.position.set(1.25, -1.65, 1.16);
      orbit.target.set(0.15, 0, 0.46);
      orbit.update();
    };
    reset();
    const pm = new T.PMREMGenerator(renderer),
      room = new RoomEnvironment(),
      env = pm.fromScene(room, 0.04);
    scene.environment = env.texture;
    room.dispose();
    pm.dispose();
    scene.add(new T.HemisphereLight("#deefff", "#30303a", 1.4));
    const light = new T.DirectionalLight("#fff0dd", 4);
    light.position.set(0.2, -0.5, 1.8);
    light.castShadow = true;
    light.shadow.mapSize.set(2048, 2048);
    light.shadow.camera.left = -1;
    light.shadow.camera.right = 1;
    light.shadow.camera.top = 1;
    light.shadow.camera.bottom = -1;
    light.shadow.bias = -0.0002;
    scene.add(light);
    const paint = new T.MeshStandardMaterial({
        color: "#cbc8bb",
        metalness: 0.3,
        roughness: 0.32,
      }),
      metal = new T.MeshStandardMaterial({
        color: "#a8b3bd",
        metalness: 0.85,
        roughness: 0.25,
      }),
      dark = new T.MeshStandardMaterial({
        color: "#252c32",
        metalness: 0.6,
        roughness: 0.34,
      }),
      black = new T.MeshStandardMaterial({ color: "#10161b", roughness: 0.5 });
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
        scene,
        start.clone().add(end).multiplyScalar(0.5).toArray(),
      );
      o.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), dir.normalize());
    };
    box(scene, [1.7, 1.1, 0.055], [0.1, 0, -0.03], dark);
    for (let x = -0.65; x < 0.9; x += 0.1)
      for (let y = -0.45; y < 0.5; y += 0.1)
        cyl(scene, 0.006, 0.001, [x, y, -0.001], black);
    cyl(scene, 0.18, 0.055, [-0.28, 0, 0.03], metal);
    cyl(scene, 0.135, 0.16, [-0.28, 0, 0.12], paint);
    cyl(scene, 0.112, 0.2, [-0.28, 0, 0.22], dark, "y");
    link([-0.28, 0, 0.23], [-0.4, 0, 0.54], 0.095);
    cyl(scene, 0.105, 0.19, [-0.4, 0, 0.54], dark, "y");
    cyl(scene, 0.081, 0.197, [-0.4, 0, 0.54], metal, "y");
    link([-0.4, 0, 0.54], [0.12, 0, 0.69], 0.09);
    cyl(scene, 0.095, 0.18, [0.12, 0, 0.69], dark, "x");
    cyl(scene, 0.085, 0.16, [0.24, 0, 0.69], paint, "x");
    cyl(scene, 0.082, 0.04, [0.345, 0, 0.69], dark, "x");
    for (const [x, z, r] of [
      [-0.28, 0.22, 0.083],
      [-0.4, 0.54, 0.073],
    ]) {
      for (let i = 0; i < 8; i++) {
        const a = (i * Math.PI) / 4;
        cyl(
          scene,
          0.004,
          0.008,
          [x + Math.sin(a) * r, -0.104, z + Math.cos(a) * r],
          dark,
          "y",
        );
      }
      cyl(scene, 0.043, 0.012, [x, -0.106, z], paint, "y");
      cyl(scene, 0.018, 0.014, [x, -0.115, z], dark, "y");
    }
    for (let i = 0; i < 8; i++) {
      const a = (i * Math.PI) / 4;
      cyl(
        scene,
        0.006,
        0.008,
        [-0.28 + Math.sin(a) * 0.15, Math.cos(a) * 0.15, 0.061],
        dark,
      );
    }
    for (const x of [0.19, 0.29])
      cyl(scene, 0.087, 0.009, [x, 0, 0.69], metal, "x");
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
      scene,
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
            dark,
            "x",
          );
        }
        cyl(parent, 0.005, 0.014, [x + 0.007, 0.026, 0.037], metal, "x");
      }
    };
    const wrist = new T.Group();
    wrist.position.set(0.39, 0, 0.69);
    scene.add(wrist);
    flange(wrist, 0, false);
    const part = new T.Group();
    scene.add(part);
    flange(part, -0.055, true);
    cyl(part, 0.07, 0.025, [-0.018, 0, 0], dark, "x");
    box(part, [0.105, 0.11, 0.1], [0.045, 0, 0], metal);
    box(part, [0.023, 0.118, 0.105], [0.105, 0, 0], dark);
    for (const y of [-0.038, 0.038]) {
      box(part, [0.08, 0.029, 0.076], [0.15, y, 0], dark);
      box(part, [0.07, 0.019, 0.052], [0.217, y, 0], metal);
      for (const z of [-0.032, 0.032])
        cyl(part, 0.004, 0.004, [0.06, y * 1.5, z], dark, "y");
    }
    const outline = new T.Group(),
      target = targetPose();
    outline.position.fromArray(target.p);
    outline.quaternion.fromArray(target.q);
    scene.add(outline);
    part.traverse((o) => {
      if (o instanceof T.Mesh) {
        const e = new T.LineSegments(
          new T.EdgesGeometry(o.geometry, 30),
          new T.LineBasicMaterial({
            color: "#42d7df",
            transparent: true,
            opacity: 0.25,
          }),
        );
        e.position.copy(o.position);
        e.quaternion.copy(o.quaternion);
        outline.add(e);
      }
    });
    const scanner = new T.Group();
    scanner.position.set(0.6, 0.3, 0.99);
    scanner.quaternion.setFromUnitVectors(
      new T.Vector3(1, 0, 0),
      new T.Vector3(0.39, 0, 0.69).sub(scanner.position).normalize(),
    );
    scene.add(scanner);
    box(scanner, [0.1, 0.07, 0.07], [0, 0, 0], dark);
    cyl(
      scanner,
      0.018,
      0.006,
      [0.05, 0, 0],
      new T.MeshStandardMaterial({
        color: "#34cad7",
        emissive: "#0d7b87",
        emissiveIntensity: 0.5,
      }),
      "x",
    );
    cyl(scene, 0.008, 0.98, [0.6, 0.3, 0.49], metal);
    const guide = new T.Group();
    scene.add(guide);
    scene.updateMatrixWorld(true);
    const origin = scanner.localToWorld(new T.Vector3(0.055, 0, 0)),
      ray = new T.Raycaster();
    const solids = scene.children.filter(
      (o) => o instanceof T.Mesh || o === wrist || o === part,
    );
    const updateGuide = () => {
      scene.updateMatrixWorld(true);
      guide.children.forEach((o) => {
        if (o instanceof T.Line) {
          o.geometry.dispose();
          (o.material as T.Material).dispose();
        }
      });
      guide.clear();
      for (let i = 0; i < 15; i++) {
        const a = (i / 15) * Math.PI * 2,
          aim = new T.Vector3(
            0.39,
            Math.sin(a) * 0.052,
            0.69 + Math.cos(a) * 0.052,
          );
        ray.set(origin, aim.clone().sub(origin).normalize());
        const hits = ray.intersectObjects(solids, true);
        if (hits[0])
          guide.add(
            new T.Line(
              new T.BufferGeometry().setFromPoints([origin, hits[0].point]),
              new T.LineBasicMaterial({
                color: "#4adce4",
                transparent: true,
                opacity: 0.25,
              }),
            ),
          );
      }
    };
    const axes = new T.AxesHelper(0.1);
    axes.position.set(0.39, 0, 0.69);
    scene.add(axes);
    let dirty = true;
    const invalidate = () => {
      dirty = true;
    };
    const gizmo = new TransformControls(camera, renderer.domElement);
    gizmo.setSpace("world");
    gizmo.setSize(0.7);
    gizmo.attach(part);
    scene.add(gizmo.getHelper());
    gizmo.enabled = !preview;
    gizmo.getHelper().visible = !preview;
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
    draw();
    return () => {
      cancelAnimationFrame(id);
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
      env.dispose();
      renderer.dispose();
      el.replaceChildren();
      state.current = null;
    };
  }, [preview]);
  useEffect(() => {
    const s = state.current;
    if (s) {
      s.part.position.fromArray(pose.p);
      s.part.quaternion.fromArray(pose.q);
      s.gizmo.setMode(mode);
      s.guide.visible = laser;
      s.outline.visible = !errors(pose).ok;
      if (laser) s.updateGuide();
      s.invalidate();
    }
  }, [pose, mode, laser]);
  useEffect(() => state.current?.reset(), [resetView]);
  return (
    <div className="assembly-canvas" ref={host}>
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
