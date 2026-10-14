import * as T from "three";

// Retain actual mesh feature segments, deduplicated across mechanical components.
export function uniqueEdges(geometries: T.BufferGeometry[]) {
  const values: number[] = [], seen = new Set<string>();
  for(const g of geometries) {
    const p=g.getAttribute("position");
    for(let i=0;i<p.count;i+=2) {
      const a=[p.getX(i),p.getY(i),p.getZ(i)], b=[p.getX(i+1),p.getY(i+1),p.getZ(i+1)];
      const keyA=a.map(v=>Math.round(v*1e5)).join(","), keyB=b.map(v=>Math.round(v*1e5)).join(",");
      const key=[keyA,keyB].sort().join(":");
      if(!seen.has(key)){seen.add(key);values.push(...a,...b);}
    }
  }
  return new T.BufferGeometry().setAttribute("position",new T.Float32BufferAttribute(values,3));
}
