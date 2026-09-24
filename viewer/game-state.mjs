export const GROW_MS = 18000;
export const SAVE_KEY = 'dusk-island-living-v1';

export function newGame() {
  return { version: 1, layoutRevision: 2, plots: Array.from({ length: 3 }, () => ({ stage: 'empty', wateredAt: null })), inventory: 0, coins: 0, deliveries: 0, harvested: 0, position: null };
}

export function restoreGame(raw) {
  const clean = newGame();
  try {
    const saved = JSON.parse(raw);
    if (saved?.version !== 1 || !Array.isArray(saved.plots) || saved.plots.length !== 3) return clean;
    for (const key of ['inventory', 'coins', 'deliveries', 'harvested']) {
      if (!Number.isSafeInteger(saved[key]) || saved[key] < 0) return newGame();
      clean[key] = saved[key];
    }
    clean.plots = saved.plots.map(p => {
      if (!p || !['empty', 'planted', 'growing'].includes(p.stage)) throw new Error('Invalid plot');
      if (p.stage === 'growing' && (!Number.isFinite(p.wateredAt) || p.wateredAt < 0)) throw new Error('Invalid timer');
      return { stage: p.stage, wateredAt: p.stage === 'growing' ? p.wateredAt : null };
    });
    if (Array.isArray(saved.position) && saved.position.length === 2 && saved.position.every(Number.isFinite)) clean.position = saved.position;
    clean.layoutRevision = [2,3].includes(saved.layoutRevision) ? saved.layoutRevision : 1;
    return clean;
  } catch { return newGame(); }
}

export function migrateLayout(state, scale) {
  if (state.layoutRevision >= 2) return;
  if (state.position) state.position = state.position.map((v, i) => v * scale[i]);
  state.layoutRevision = 2;
}

export function migrateReferenceLayout(state, nav, spawn) {
  if(state.layoutRevision>=3)return;
  // The river and buildings moved independently; use the nearest safe ground,
  // keeping economy and growth timers intact instead of resetting the save.
  const p=state.position||spawn;
  state.position=nav.nearestPoint(...p);state.layoutRevision=3;
}

export function plotStatus(plot, now = Date.now()) {
  if (plot.stage !== 'growing') return plot.stage;
  return now - plot.wateredAt >= GROW_MS ? 'ready' : 'growing';
}

export function tendPlot(state, index, now = Date.now()) {
  const plot = state.plots[index];
  if (!plot) return null;
  const status = plotStatus(plot, now);
  if (status === 'empty') { plot.stage = 'planted'; return 'planted'; }
  if (status === 'planted') { plot.stage = 'growing'; plot.wateredAt = now; return 'watered'; }
  if (status === 'ready') {
    plot.stage = 'empty'; plot.wateredAt = null;
    state.inventory++; state.harvested++;
    return 'harvested';
  }
  return 'waiting';
}

export function deliver(state) {
  if (state.inventory < 3) return false;
  state.inventory -= 3; state.coins += 30; state.deliveries++;
  return true;
}
