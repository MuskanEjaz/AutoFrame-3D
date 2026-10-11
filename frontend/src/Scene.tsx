import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

export interface GeometryPayload {
  config: Record<string, unknown>;
  mesh: { vertices: number[][]; faces: number[][] };
  scan: number[][];
  ground_truth_T_object_from_scan: number[][];
  estimated_T_object_from_scan: number[][];
}

interface SceneProps {
  data: GeometryPayload | null;
  showScan: boolean;
  showEstimate: boolean;
  showTruth: boolean;
}

function objectToWorld(transform: number[][]): THREE.Matrix4 {
  const objectFromScan = new THREE.Matrix4().set(...(transform.flat() as [
    number, number, number, number,
    number, number, number, number,
    number, number, number, number,
    number, number, number, number,
  ]));
  return objectFromScan.invert();
}

export default function Scene({ data, showScan, showEstimate, showTruth }: SceneProps) {
  const host = useRef<HTMLDivElement>(null);
  const objects = useRef<{ scan?: THREE.Object3D; estimate?: THREE.Object3D; truth?: THREE.Object3D }>({});

  useEffect(() => {
    const container = host.current;
    if (!container) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#10191e");
    const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 100);
    camera.up.set(0, 0, 1);
    camera.position.set(3.4, -4.2, 3.0);
    camera.lookAt(0, 0, 0);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    const grid = new THREE.GridHelper(4, 20, "#49606a", "#283941");
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -1.03;
    scene.add(grid);
    const axes = new THREE.AxesHelper(1.35);
    axes.rotation.x = Math.PI / 2;
    scene.add(axes);
    scene.add(new THREE.HemisphereLight("#d8f0eb", "#17242a", 2.2));
    const keyLight = new THREE.DirectionalLight("#fff4e8", 2.3);
    keyLight.position.set(2, -2, 4);
    scene.add(keyLight);

    let scanPoints: THREE.Points | undefined;
    let estimate: THREE.Mesh | undefined;
    let truth: THREE.Mesh | undefined;
    let controls: OrbitControls | undefined;
    if (data) {
      const scanGeometry = new THREE.BufferGeometry();
      scanGeometry.setAttribute("position", new THREE.Float32BufferAttribute(data.scan.flat(), 3));
      scanPoints = new THREE.Points(
        scanGeometry,
        new THREE.PointsMaterial({ color: "#a8bac3", size: 0.019, sizeAttenuation: true }),
      );
      scene.add(scanPoints);

      const meshGeometry = new THREE.BufferGeometry();
      meshGeometry.setAttribute("position", new THREE.Float32BufferAttribute(data.mesh.vertices.flat(), 3));
      meshGeometry.setIndex(data.mesh.faces.flat());
      meshGeometry.computeVertexNormals();
      estimate = new THREE.Mesh(
        meshGeometry,
        new THREE.MeshBasicMaterial({ color: "#ff9a62", wireframe: true, transparent: true, opacity: 0.86 }),
      );
      estimate.matrixAutoUpdate = false;
      estimate.matrix.copy(objectToWorld(data.estimated_T_object_from_scan));
      scene.add(estimate);

      truth = new THREE.Mesh(
        meshGeometry,
        new THREE.MeshBasicMaterial({ color: "#55d5c7", wireframe: true, transparent: true, opacity: 0.86 }),
      );
      truth.matrixAutoUpdate = false;
      truth.matrix.copy(objectToWorld(data.ground_truth_T_object_from_scan));
      scene.add(truth);
      objects.current = { scan: scanPoints, estimate, truth };
      controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.target.set(0, 0, 0);
      controls.minDistance = 1.5;
      controls.maxDistance = 12;
    }

    const resize = new ResizeObserver(() => {
      if (!container.clientWidth || !container.clientHeight) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    });
    resize.observe(container);
    let frame = 0;
    const render = () => {
      controls?.update();
      renderer.render(scene, camera);
      frame = requestAnimationFrame(render);
    };
    render();

    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect();
      controls?.dispose();
      scanPoints?.geometry.dispose();
      (scanPoints?.material as THREE.Material | undefined)?.dispose();
      estimate?.geometry.dispose();
      (estimate?.material as THREE.Material | undefined)?.dispose();
      (truth?.material as THREE.Material | undefined)?.dispose();
      objects.current = {};
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, [data]);

  useEffect(() => {
    if (objects.current.scan) objects.current.scan.visible = showScan;
    if (objects.current.estimate) objects.current.estimate.visible = showEstimate;
    if (objects.current.truth) objects.current.truth.visible = showTruth;
  }, [showScan, showEstimate, showTruth, data]);

  return <div className="scene-host" ref={host} aria-label="Interactive 3D registration view" />;
}