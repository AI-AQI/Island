import { makeTerrain } from './terrain.mjs';
// Navigation uses the same authored terrain as the Blender scene. All public
// positions are Three.js [x,z]; Blender (x,y,z) converts to (x,z,-y).
export const bend = y => 1.25 * Math.sin((y + 5.2) * .21);
export const river = y => 1.7 + 1.6 * Math.sin((y + 4) * .13) + .35 * Math.sin(y * .43);
export function groundHeight(x, z, scale = [1, 1]) {
  const y = -z / scale[1], originalX = x / scale[0] - bend(y);
  const d = Math.abs(originalX - river(y));
  return 10.65 + .3 * Math.sin(originalX * .11) + .16 * Math.cos(y * .23) - 1.05 * Math.exp(-((d / 2.7) ** 4));
}

export function makeNavigation(meta) {
  const scale = meta.terrainScale || [1, 1];
  const terrain=meta.terrain?makeTerrain(meta.terrain):null;
  const rx=meta.terrain?.radius[0]||23*scale[0],rz=meta.terrain?.radius[1]||14*scale[1];
  const step = .45, minX = -rx-1, minZ = -rz-1, cols = Math.ceil((rx*2+3) / step), rows = Math.ceil((rz*2+3) / step);
  const bridge = meta.bridge, bx = bridge.position[0], bz = -bridge.position[1];
  const bc=Math.cos(bridge.angle||0),bs=Math.sin(bridge.angle||0);
  const bridgeLocal=(x,z)=>[bc*(x-bx)-bs*(z-bz),bs*(x-bx)+bc*(z-bz)];
  const inRect = (x, z, bounds, pad) => x > bounds[0][0] - pad && x < bounds[1][0] + pad && z > -bounds[1][1] - pad && z < -bounds[0][1] + pad;
  function onBridge(x, z) { const [u,v]=bridgeLocal(x,z);return Math.abs(u) <= (bridge.walkHalfLength || 3.8) && Math.abs(v) < (bridge.walkHalfWidth || .92); }
  function canWalk(x, z) {
    const y = -z / scale[1], ox = x / scale[0] - bend(y);
    if(terrain){const r=meta.terrain.walkRadius,a=Math.atan2(-z/r[1],x/r[0]);if(Math.hypot(x/r[0],z/r[1])>terrain.outline(a))return false;}
    else if ((ox / 20.8) ** 2 + (y / 12.1) ** 2 > 1) return false;
    if (onBridge(x, z)) return true;
    if(terrain){const p=terrain.riverAt(x,-z);if(p.distance<p.width+.52)return false;}
    else if (Math.abs(ox - river(y)) < 2.42) return false;
    if (inRect(x, z, meta.house, .24) || inRect(x, z, meta.cafe, .15)) return false;
    for (const p of meta.plots) if (Math.abs(x - p.position[0]) < (p.halfSize?.[0] || 2.22) && Math.abs(z + p.position[1]) < (p.halfSize?.[1] || 2.52)) return false;
    for (const f of meta.fences) if (inRect(x, z, f, .22)) return false;
    for (const tree of meta.trees) if (Math.hypot(x - tree.position[0], z + tree.position[1]) < tree.radius) return false;
    for (const rock of meta.terrainObstacles || []) if (Math.hypot(x-rock.position[0],z+rock.position[1])<rock.radius+.15) return false;
    for (const box of meta.obstacles || []) if (inRect(x, z, box, .22)) return false;
    return true;
  }
  function height(x, z) {
    const base=terrain?terrain.height(x,z):groundHeight(x,z,scale);
    if (onBridge(x, z)) return Math.max(base, bridge.deckBase + .95 * Math.cos(Math.PI * Math.min(bridge.halfLength, Math.abs(bridgeLocal(x,z)[0])) / (bridge.halfLength * 2)));
    return base + .10;
  }
  const point = i => [minX + i % cols * step, minZ + Math.floor(i / cols) * step];
  const grid = Uint8Array.from({ length: cols * rows }, (_, i) => +canWalk(...point(i)));
  function nearest(x, z) {
    let best = -1, d = Infinity;
    for (let i = 0; i < grid.length; i++) if (grid[i]) {
      const p = point(i), n = (p[0] - x) ** 2 + (p[1] - z) ** 2;
      if (n < d) { d = n; best = i; }
    }
    return best;
  }
  function findPath(from, to) {
    if (!canWalk(...to)) return [];
    const start = nearest(...from), goal = nearest(...to);
    const score = new Float64Array(grid.length).fill(Infinity), prev = new Int32Array(grid.length).fill(-1);
    const open = new Set([start]), closed = new Set(); score[start] = 0;
    const end = point(goal);
    while (open.size) {
      let current = -1, best = Infinity;
      for (const i of open) {
        const p = point(i), f = score[i] + Math.hypot(p[0] - end[0], p[1] - end[1]);
        if (f < best) { best = f; current = i; }
      }
      if (current === goal) {
        const route = [to];
        for (let i = goal; i !== start && i !== -1; i = prev[i]) route.push(point(i));
        return route.reverse();
      }
      open.delete(current); closed.add(current);
      const cx = current % cols, cy = Math.floor(current / cols);
      for (const [dx, dy] of [[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[-1,1],[1,-1],[1,1]]) {
        const nx = cx + dx, ny = cy + dy, next = ny * cols + nx;
        if (nx < 0 || ny < 0 || nx >= cols || ny >= rows || !grid[next] || closed.has(next)) continue;
        if (dx && dy && (!grid[current + dx] || !grid[current + dy * cols])) continue;
        const cost = score[current] + step * Math.hypot(dx,dy);
        if (cost < score[next]) { score[next] = cost; prev[next] = current; open.add(next); }
      }
    }
    return [];
  }
  function move(position, dx, dz) {
    // Substeps prevent tunnelling through the river, fences or the island edge.
    let [x,z] = position;
    const steps = Math.max(1, Math.ceil(Math.hypot(dx,dz) / .09));
    for (let i=0; i<steps; i++) {
      const nx=x+dx/steps,nz=z+dz/steps;
      if (canWalk(nx,nz)) { x=nx;z=nz; }
      else if (canWalk(nx,z)) x=nx;
      else if (canWalk(x,nz)) z=nz;
    }
    return [x,z];
  }
  return { canWalk, height, findPath, move, nearestPoint: (x,z) => point(nearest(x,z)), onBridge };
}
