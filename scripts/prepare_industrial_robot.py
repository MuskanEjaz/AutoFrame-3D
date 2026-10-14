"""Download pinned Apache-2.0 Panda visuals and bake a stationary inspection pose.

Run this, then `node scripts/pack_industrial_robot.mjs`. Runtime uses local buffers.
"""
import concurrent.futures
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend/public/assets/industrial"
TEMP = ROOT / ".tools/robot-source"
OUT.mkdir(parents=True, exist_ok=True)
TEMP.mkdir(parents=True, exist_ok=True)
revision = "71f066ad0be9cd271f7ed58c030243ef157af9f4"
base = f"https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/{revision}/franka_emika_panda/"
def get(name):
    return urllib.request.urlopen(base + name, timeout=60).read()
xml = get("panda.xml")
(TEMP / "panda.xml").write_bytes(xml)
for name in ["LICENSE", "README.md"]:
    (OUT / ("PANDA-" + name)).write_bytes(get(name))
root = ET.fromstring(xml)
bodies = []
body = root.find("worldbody/body")
while body is not None and body.attrib["name"] != "hand":
    bodies.append(body)
    body = body.find("body")
def transform(pos, quat):
    m = np.eye(4)
    m[:3, 3] = pos
    w,x,y,z = quat
    m[:3,:3] = Rotation.from_quat([x,y,z,w]).as_matrix()
    return m
def fk(q):
    m = np.eye(4)
    m[:3,3] = [-.22, 0, .055]
    frames = []
    for i,b in enumerate(bodies):
        p = np.array(list(map(float,b.get("pos", "0 0 0").split()))) * 1.08
        quat = list(map(float,b.get("quat", "1 0 0 0").split()))
        m = m @ transform(p, quat)
        if i:
            r = np.eye(4)
            r[:3,:3] = Rotation.from_rotvec([0,0,q[i-1]]).as_matrix()
            m = m @ r
        frames.append(m.copy())
    mount = m @ transform([0,0,.107 * 1.08],[1,0,0,0])
    return frames, mount
target = transform([.39,0,.69],[np.sqrt(.5),0,np.sqrt(.5),0])
def error(q):
    _,m = fk(q)
    return np.r_[m[:3,3]-target[:3,3], Rotation.from_matrix(target[:3,:3].T @ m[:3,:3]).as_rotvec() * .2]
lower = [-2.89,-1.76,-2.89,-3.07,-2.89,-.017,-2.89]
upper = [2.89,1.76,2.89,-.07,2.89,3.75,2.89]
rng = np.random.default_rng(731)
solutions = [least_squares(error,rng.uniform(lower,upper),bounds=(lower,upper),max_nfev=1000,
    gtol=1e-10,ftol=1e-10,xtol=1e-10) for _ in range(20)]
solution = min(solutions,key=lambda s: np.linalg.norm(error(s.x)))
assert np.linalg.norm(error(solution.x)) < 1e-6, error(solution.x)
frames,_ = fk(solution.x)
parts = []
for b,m in zip(bodies,frames):
    for g in b.findall("geom"):
        if g.get("class") == "visual":
            parts.append({"file":g.attrib["mesh"] + ".obj", "material":g.attrib["material"], "matrix":m.T.flatten().tolist()})
files = sorted({p["file"] for p in parts})
def download(name):
    data = get("assets/" + name)
    (TEMP / name).write_bytes(data)
    return len(data)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    total = sum(pool.map(download,files))
manifest = {"revision":revision,"source":base,"scale":1.08,"jointAngles":solution.x.tolist(),"downloadBytes":total,"parts":parts}
(TEMP / "manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
print(json.dumps({"revision":revision,"downloadBytes":total,"parts":len(parts),"mountError":np.linalg.norm(error(solution.x))}))
