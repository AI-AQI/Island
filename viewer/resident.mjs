/** Ambient daily life. Receives navigation and world time, never the economy. */
const routines = {
  morning: ['garden', 'yard', 'flowers', 'orchard'],
  day: ['orchard', 'cafe', 'flowers', 'garden', 'overlook'],
  evening: ['overlook', 'cafe', 'flowers', 'home'],
  late: ['home', 'flowers'],
  night: ['home'],
};
export function routinePeriod(hour) {
  if (hour < 6 || hour >= 22) return 'night';
  if (hour < 10) return 'morning';
  if (hour < 16) return 'day';
  if (hour < 20) return 'evening';
  return 'late';
}

export function createResident({ nav, sites }) {
  const byId = new Map(sites.map(s => [s.id, s]));
  let mode = '', index = 0, site = null, route = [], phase = 'idle';
  let dwell = 0, gestureTimer = 0, stuck = 0, retry = 0, suspended = false;
  function suspend() {
    suspended = true; mode = ''; site = null; route = []; phase = 'idle';
    dwell = gestureTimer = stuck = retry = 0;
  }
  function plan(position, currentMode) {
    let candidates;
    if (currentMode === 'rain') {
      candidates = sites.filter(s => s.shelter).map(s => ({ s, path: nav.findPath(position, s.position) }))
        .filter(s => s.path.length).sort((a, b) => a.path.length - b.path.length);
    } else {
      const list = routines[currentMode];
      candidates = list.map((_, i) => byId.get(list[(index + i) % list.length]))
        .filter(Boolean).map(s => ({ s, path: nav.findPath(position, s.position) })).filter(s => s.path.length);
    }
    if (!candidates.length) { site = null; route = []; phase = 'idle'; retry = 4; return; }
    site = candidates[0].s; route = candidates[0].path; phase = 'walking'; stuck = 0;
    if (currentMode !== 'rain') index = routines[currentMode].indexOf(site.id);
  }
  function label() {
    if (!site) return '在岛上歇一会儿';
    if (mode === 'rain') return phase === 'walking' ? `去${site.label}避雨` : '檐下听雨';
    if (mode === 'night') return phase === 'walking' ? '回小院休息' : '在廊下休息';
    if (phase === 'walking') return `去${site.label}`;
    return { garden: '看看菜苗，浇浇水', flowers: '照料院边的花草', orchard: '在果树林里转转', cafe: '在咖啡馆歇脚', overlook: '在溪边看流水', yard: '整理花园工作台', home: '享受小院里的安静' }[site.id];
  }
  function update({ dt, position, hour, weather, busy = false, enabled = true }) {
    const result = { position: [...position], moving: false, action: null, facing: null, label: label(), phase, site: site?.id || null };
    if (!enabled) { if (!suspended) suspend(); return { ...result, label: '由你带她逛逛', phase: 'controlled', site: null }; }
    suspended = false;
    if (!Number.isFinite(dt) || dt <= 0) return result;
    dt = Math.min(dt, .1);
    const nextMode = weather === 'rain' ? 'rain' : routinePeriod(hour);
    if (nextMode !== mode) { mode = nextMode; index = 0; site = null; route = []; dwell = gestureTimer = retry = 0; }
    if (retry > 0) retry -= dt;
    if (!site && retry <= 0) plan(position, mode);
    if (site && !busy) {
      if (phase === 'walking') {
        let remaining = 2.0 * dt;
        while (route.length && remaining > 0) {
          const target = route[0], dx = target[0] - result.position[0], dz = target[1] - result.position[1], distance = Math.hypot(dx, dz);
          if (distance < .065) { route.shift(); continue; }
          const amount = Math.min(distance, remaining), before = result.position;
          result.position = nav.move(before, dx / distance * amount, dz / distance * amount);
          const moved = Math.hypot(result.position[0] - before[0], result.position[1] - before[1]);
          if (moved > .0001) { result.moving = true; result.facing = Math.atan2(dx, dz); stuck = 0; }
          else { stuck += dt; break; }
          remaining -= amount;
        }
        if (stuck > 1.4) { plan(position, mode); retry = 1; }
        if (!route.length) { phase = 'dwelling'; dwell = 0; gestureTimer = 1.2; }
      } else {
        dwell += dt; gestureTimer -= dt;
        const target = site.lookAt || site.position;
        result.facing = Math.atan2(target[0] - position[0], target[1] - position[1]);
        if (site.action && mode !== 'rain' && mode !== 'night' && gestureTimer <= 0) { result.action = site.action; gestureTimer = 8; }
        if (mode !== 'rain' && mode !== 'night' && dwell >= site.duration) {
          index = (index + 1) % routines[mode].length; plan(position, mode);
        }
      }
    }
    return { ...result, label: label(), phase, site: site?.id || null };
  }
  return { update, suspend };
}
