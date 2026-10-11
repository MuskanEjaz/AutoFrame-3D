"""Prepare only the two recorded display geometries; never register or sample."""
import argparse
import hashlib
import gzip
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autoframe3d import recorded_demo
from autoframe3d.tless_adapter import depth_to_camera_points, read_ply_model


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def prepare(dataset, output):
    dataset, output = Path(dataset), Path(output)
    manifest = {"schema": 1, "purpose": "Visualization only; never benchmark scoring or replay",
                "license": "CC-BY-SA-4.0", "notice": "ATTRIBUTION.md",
                "parameters": {"depth_projection": "all positive visible-mask pixels through recorded K",
                               "units": "metres", "cad_scale": 0.001,
                               "reduction": "none", "serialization": "sorted compact JSON, float64; gzip level 9, mtime 0"},
                "identity_scope": "Publication hashes, not historical execution provenance", "cases": {}}
    prepared = []
    for case in recorded_demo.evidence()["cases"]:
        record = case["variants"][0]["record"]
        scene = f"test_primesense/{record['scene_id']:06d}"
        names = [f"{scene}/scene_camera.json", f"{scene}/depth/{record['image_id']:06d}.png",
                 f"{scene}/mask_visib/{record['image_id']:06d}_{record['gt_index']:06d}.png",
                 f"models_cad/obj_{record['object_id']:06d}.ply"]
        sources = {}
        for name in names:
            source = dataset / name
            if not source.is_file():
                raise FileNotFoundError(f"Missing {source}. Supply --dataset pointing to an extracted T-LESS BOP root; required inputs: {', '.join(names)}")
            raw = source.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            expected = case["inputs"]["data/tless/bop/" + name]
            if digest != expected:
                raise ValueError(f"Input differs from recorded evidence: {source}")
            sources[name] = {"sha256": digest, "size_bytes": len(raw)}
        camera = json.loads((dataset / names[0]).read_text())[str(record["image_id"])]
        scan = depth_to_camera_points(np.asarray(Image.open(dataset / names[1]), dtype=np.uint16),
                                     np.asarray(Image.open(dataset / names[2])) > 0,
                                     np.asarray(camera["cam_K"]).reshape(3, 3), float(camera["depth_scale"]))
        model = read_ply_model(dataset / names[3])
        raw = encode({"mesh": {"vertices": model.vertices_m.tolist(), "faces": model.faces.tolist()},
                      "scan": scan.tolist()})
        raw = gzip.compress(raw, compresslevel=9, mtime=0)
        name = case["id"] + ".json.gz"
        manifest["cases"][case["id"]] = {"file": name, "publication_sha256": hashlib.sha256(raw).hexdigest(),
                                           "size_bytes": len(raw), "sources": sources,
                                           "vertices": len(model.vertices_m), "faces": len(model.faces), "scan_points": len(scan)}
        prepared.append((name, raw))
    output.mkdir(parents=True, exist_ok=True)
    for name, raw in prepared:
        (output / name).write_bytes(raw)
    (output / "manifest.json").write_bytes(encode(manifest))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=recorded_demo.ROOT / "demo_assets")
    args = parser.parse_args()
    try:
        manifest = prepare(args.dataset, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps({"files": len(manifest["cases"]), "bytes": sum(c["size_bytes"] for c in manifest["cases"].values())}))
