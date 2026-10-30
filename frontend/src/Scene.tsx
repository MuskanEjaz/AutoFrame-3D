import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { toCreasedNormals } from "three/addons/utils/BufferGeometryUtils.js";

export interface GeometryPayload {
  config: Record<string, unknown>;
  mesh: { vertices: number[][]; faces: number[][] };
  scan: number[][];
  ground_truth_T_object_from_scan: number[][];
  estimated_T_object_from_scan: number[][];
}
interface SceneProps {
  data: GeometryPayload | null;
  showScan: boolean; showEstimate: boolean; showTruth: boolean;
  viewCommand?: { id: number; view: string };
}
function objectToWorld(transform: number[][]) {
  return new THREE.Matrix4().fromArray(transform.flat()).transpose().invert();
}

export default function Scene({ data, showScan, showEstimate, showTruth, viewCommand }: SceneProps) {
  const host = useRef<HTMLDivElement>(null);
  const objects = useRef<{ scan?: THREE.Object3D; estimate?: THREE.Object3D; truth?: THREE.Object3D }>({});
  const savedCamera = useRef<{ key: unknown; position: THREE.Vector3; target: THREE.Vector3 } | null>(null);
  const command = useRef<(view: string) => void>(() => {});
  const invalidate = useRef<() => void>(() => {});
  const [renderError, setRenderError] = useState<string | null>(null);

  useEffect(() => {
    const container = host.current;
    if (!container) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#0d141e");
    const camera = new THREE.PerspectiveCamera(36, 1, 0.0001, 100);
    camera.up.set(0, 0, 1);
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
      setRenderError(null);
    } catch {
      setRenderError("3D rendering unavailable. Recorded metrics and evidence remain available.");
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.9;
    renderer.setSize(container.clientWidth, container.clientHeight);
    camera.aspect = container.clientWidth / Math.max(container.clientHeight, 1);
    container.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    const pmrem = new THREE.PMREMGenerator(renderer);
    const room = new RoomEnvironment();
    const environment = pmrem.fromScene(room, 0.04);
    scene.environment = environment.texture;
    room.dispose(); pmrem.dispose();
    scene.add(new THREE.HemisphereLight("#c5def9", "#28323e", 0.7));
    const ownedGeometry: THREE.BufferGeometry[] = [];
    const ownedMaterial: THREE.Material[] = [];
    const key = data?.config.object_id ?? data?.config.object_kind;
    if (data) {
      const scanGeometry = new THREE.BufferGeometry();
      scanGeometry.setAttribute("position", new THREE.Float32BufferAttribute(data.scan.flat(), 3));
      ownedGeometry.push(scanGeometry);
      // Screen-sized circular points retain every observed point, including outliers.
      const pointCanvas = document.createElement("canvas"); pointCanvas.width = pointCanvas.height = 32;
      const context = pointCanvas.getContext("2d")!;
      context.fillStyle = "white"; context.beginPath(); context.arc(16, 16, 14, 0, Math.PI * 2); context.fill();
      const pointTexture = new THREE.CanvasTexture(pointCanvas);
      const pointsMaterial = new THREE.PointsMaterial({ color: "#e3b67b", size: 2.1, sizeAttenuation: false,
        map: pointTexture, alphaTest: 0.4 });
      ownedMaterial.push(pointsMaterial);
      const scan = new THREE.Points(scanGeometry, pointsMaterial);
      scene.add(scan);
      const indexed = new THREE.BufferGeometry();
      indexed.setAttribute("position", new THREE.Float32BufferAttribute(data.mesh.vertices.flat(), 3));
      indexed.setIndex(data.mesh.faces.flat());
      // Split shading normals at real creases, without moving vertices or changing triangles.
      const meshGeometry = toCreasedNormals(indexed, Math.PI / 5);
      indexed.dispose(); ownedGeometry.push(meshGeometry);
      const metal = new THREE.MeshStandardMaterial({ color: "#9eafc1", metalness: 0.82, roughness: 0.29,
        envMapIntensity: 0.95, side: THREE.DoubleSide });
      ownedMaterial.push(metal);
      const estimate = new THREE.Mesh(meshGeometry, metal);
      estimate.matrixAutoUpdate = false;
      estimate.matrix.copy(objectToWorld(data.estimated_T_object_from_scan)); scene.add(estimate);
      const edges = new THREE.EdgesGeometry(meshGeometry, 28); ownedGeometry.push(edges);
      const lineMaterial = new THREE.LineBasicMaterial({ color: "#55dce5", transparent: true, opacity: 0.85, depthWrite: false });
      ownedMaterial.push(lineMaterial);
      const truth = new THREE.LineSegments(edges, lineMaterial);
      truth.matrixAutoUpdate = false;
      truth.matrix.copy(objectToWorld(data.ground_truth_T_object_from_scan)); scene.add(truth);
      objects.current = { scan, estimate, truth };
      scene.updateMatrixWorld(true);
      // Include GT even while hidden: revealing it never crops or refits away disagreement.
      const bounds = new THREE.Box3().setFromObject(scan).union(new THREE.Box3().setFromObject(estimate)).union(new THREE.Box3().setFromObject(truth));
      const center = bounds.getCenter(new THREE.Vector3());
      const radius = Math.max(bounds.getBoundingSphere(new THREE.Sphere()).radius, 0.0001);
      camera.near = radius / 500; camera.far = radius * 100;
      controls.minDistance = radius * 0.2; controls.maxDistance = radius * 20;
      const standardView = (view: string) => {
        const directions: Record<string, THREE.Vector3> = {
          fit: new THREE.Vector3(1, -1.7, 0.85), front: new THREE.Vector3(0, -1, 0.02),
          side: new THREE.Vector3(1, 0, 0.02), top: new THREE.Vector3(0, -0.001, 1),
        };
        const direction = (directions[view] ?? directions.fit).clone().normalize();
        const right = new THREE.Vector3().crossVectors(camera.up, direction).normalize();
        const up = new THREE.Vector3().crossVectors(direction, right).normalize();
        const tanVertical = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
        const tanHorizontal = tanVertical * camera.aspect;
        let distance = radius;
        // Fit all shared bounds corners; never recenter individual layers.
        for (const x of [bounds.min.x, bounds.max.x]) for (const y of [bounds.min.y, bounds.max.y]) for (const z of [bounds.min.z, bounds.max.z]) {
          const offset = new THREE.Vector3(x, y, z).sub(center);
          distance = Math.max(distance, Math.abs(offset.dot(right)) / tanHorizontal + offset.dot(direction),
            Math.abs(offset.dot(up)) / tanVertical + offset.dot(direction));
        }
        distance *= 1.12;
        controls.target.copy(center);
        camera.position.copy(center).add((directions[view] ?? directions.fit).clone().normalize().multiplyScalar(distance));
        camera.lookAt(center); camera.updateProjectionMatrix(); controls.update();
      };
      command.current = standardView;
      const previousCamera = savedCamera.current;
      if (previousCamera && previousCamera.key === key) {
        camera.position.copy(previousCamera.position); controls.target.copy(previousCamera.target);
        camera.lookAt(controls.target); camera.updateProjectionMatrix();
      } else standardView("fit");
      const groundZ = bounds.min.z - radius * 0.12;
      const floorGeometry = new THREE.PlaneGeometry(radius * 8, radius * 8); ownedGeometry.push(floorGeometry);
      const floorMaterial = new THREE.MeshBasicMaterial({ color: "#101925" }); ownedMaterial.push(floorMaterial);
      const floor = new THREE.Mesh(floorGeometry, floorMaterial); floor.position.set(center.x, center.y, groundZ); scene.add(floor);
      const grid = new THREE.GridHelper(radius * 5, 16, "#344659", "#253449");
      grid.rotation.x = Math.PI / 2; grid.position.set(center.x, center.y, groundZ + radius * 0.002);
      (grid.material as THREE.Material).transparent = true; (grid.material as THREE.Material).opacity = 0.25;
      ownedGeometry.push(grid.geometry); ownedMaterial.push(grid.material as THREE.Material); scene.add(grid);
      for (const [color, intensity, direction] of [
        ["#edf4ff", 2.2, [1, -2, 3]], ["#8bb5dd", 0.7, [-2, -1, 1]], ["#57c4d7", 1.4, [0, 2, 2]],
      ] as [string, number, number[]][]) {
        const light = new THREE.DirectionalLight(color, intensity);
        light.position.copy(center).add(new THREE.Vector3(...direction).multiplyScalar(radius * 3));
        light.target.position.copy(center); scene.add(light, light.target);
      }
      // Dispose the sprite texture with the material.
      pointsMaterial.addEventListener("dispose", () => pointTexture.dispose());
    }
    let needsRender = true;
    invalidate.current = () => { needsRender = true; };
    controls.addEventListener("change", invalidate.current);
    const resize = new ResizeObserver(() => {
      if (!container.clientWidth || !container.clientHeight) return;
      camera.aspect = container.clientWidth / container.clientHeight; camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
      needsRender = true;
    }); resize.observe(container);
    let frame = 0;
    const render = () => {
      controls.update();
      if (needsRender) { renderer.render(scene, camera); needsRender = false; }
      frame = requestAnimationFrame(render);
    }; render();
    return () => {
      if (data) savedCamera.current = { key, position: camera.position.clone(), target: controls.target.clone() };
      cancelAnimationFrame(frame); resize.disconnect(); controls.dispose();
      ownedGeometry.forEach(g => g.dispose()); ownedMaterial.forEach(m => m.dispose());
      environment.dispose(); objects.current = {}; command.current = () => {};
      invalidate.current = () => {};
      renderer.dispose(); container.removeChild(renderer.domElement);
    };
  }, [data]);

  useEffect(() => {
    if (objects.current.scan) objects.current.scan.visible = showScan;
    if (objects.current.estimate) objects.current.estimate.visible = showEstimate;
    if (objects.current.truth) objects.current.truth.visible = showTruth;
    invalidate.current();
  }, [showScan, showEstimate, showTruth, data]);
  useEffect(() => { if (viewCommand) command.current(viewCommand.view); }, [viewCommand]);
  return <div className="scene-host" ref={host} aria-label="Interactive 3D registration view">{renderError && <div className="loading-state" role="status">{renderError}</div>}</div>;
}
