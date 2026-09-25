// Gomme magique : remplissage d'une zone à partir du décor environnant.
// Algorithme multi-échelle par correspondance de motifs (PatchMatch + vote, méthode de Wexler et al.).
// S'exécute dans un Web Worker : reçoit {rgb, hole, W, H} et renvoie {rgb}.
"use strict";
const R = 6; // rayon des motifs (13×13) : meilleur raccord des lignes (horizon, murs…)

function down(l) {
  const W = l.W >> 1, H = l.H >> 1, rgb = new Float32Array(W * H * 3), hole = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const o = y * W + x, a = (2 * y) * l.W + 2 * x, b = a + 1, c = a + l.W, d = c + 1;
    for (let ch = 0; ch < 3; ch++)
      rgb[o * 3 + ch] = (l.rgb[a * 3 + ch] + l.rgb[b * 3 + ch] + l.rgb[c * 3 + ch] + l.rgb[d * 3 + ch]) / 4;
    hole[o] = l.hole[a] | l.hole[b] | l.hole[c] | l.hole[d];
  }
  return { rgb, hole, W, H };
}

function dilate(hole, W, H, r) {
  // dilatation carrée séparable
  const tmp = new Uint8Array(W * H), out = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) { let run = -1e9;
    for (let x = 0; x < W; x++) { if (hole[y * W + x]) run = x; if (x - run <= r) tmp[y * W + x] = 1; }
    run = 1e9; for (let x = W - 1; x >= 0; x--) { if (hole[y * W + x]) run = x; if (run - x <= r) tmp[y * W + x] = 1; } }
  for (let x = 0; x < W; x++) { let run = -1e9;
    for (let y = 0; y < H; y++) { if (tmp[y * W + x]) run = y; if (y - run <= r) out[y * W + x] = 1; }
    run = 1e9; for (let y = H - 1; y >= 0; y--) { if (tmp[y * W + x]) run = y; if (run - y <= r) out[y * W + x] = 1; } }
  return out;
}

function diffuse(rgb, hole, W, H) {
  // remplissage « en pelure d'oignon » par moyenne des voisins connus
  const known = new Uint8Array(W * H);
  let left = 0;
  for (let i = 0; i < W * H; i++) { known[i] = hole[i] ? 0 : 1; if (hole[i]) left++; }
  while (left > 0) {
    const newly = [];
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const i = y * W + x; if (known[i]) continue;
      let s0 = 0, s1 = 0, s2 = 0, n = 0;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue;
        const j = yy * W + xx; if (!known[j]) continue;
        s0 += rgb[j * 3]; s1 += rgb[j * 3 + 1]; s2 += rgb[j * 3 + 2]; n++;
      }
      if (n) { rgb[i * 3] = s0 / n; rgb[i * 3 + 1] = s1 / n; rgb[i * 3 + 2] = s2 / n; newly.push(i); }
    }
    if (!newly.length) break;
    for (const i of newly) known[i] = 1;
    left -= newly.length;
  }
}

function inpaint(rgb, hole, W, H) {
  const levels = [{ rgb, hole, W, H }];
  for (;;) {
    const l = levels[levels.length - 1];
    if (Math.min(l.W, l.H) < 4 * R + 8 || levels.length > 9) break;
    let minx = 1e9, maxx = -1, miny = 1e9, maxy = -1;
    for (let y = 0; y < l.H; y++) for (let x = 0; x < l.W; x++) if (l.hole[y * l.W + x]) {
      if (x < minx) minx = x; if (x > maxx) maxx = x; if (y < miny) miny = y; if (y > maxy) maxy = y; }
    if (maxx < 0 || Math.max(maxx - minx, maxy - miny) < 2 * R + 2) break;
    levels.push(down(l));
  }

  let prev = null;
  for (let L = levels.length - 1; L >= 0; L--) {
    const { hole, W, H } = levels[L], cur = new Float32Array(levels[L].rgb), N = W * H;
    // valeur initiale des pixels à remplir
    if (!prev) diffuse(cur, hole, W, H);
    else for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const i = y * W + x; if (!hole[i]) continue;
      const px = Math.min(prev.W - 1, x >> 1), py = Math.min(prev.H - 1, y >> 1), j = py * prev.W + px;
      cur[i * 3] = prev.cur[j * 3]; cur[i * 3 + 1] = prev.cur[j * 3 + 1]; cur[i * 3 + 2] = prev.cur[j * 3 + 2];
    }
    const near = dilate(hole, W, H, R), valid = new Uint8Array(N), srcs = [];
    const dist2b = new Float32Array(N); // distance (chanfrein) au pixel connu le plus proche
    for (let i = 0; i < N; i++) dist2b[i] = hole[i] ? 1e9 : 0;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const i = y * W + x; if (!dist2b[i]) continue;
      if (x > 0) dist2b[i] = Math.min(dist2b[i], dist2b[i - 1] + 1); if (y > 0) dist2b[i] = Math.min(dist2b[i], dist2b[i - W] + 1); }
    for (let y = H - 1; y >= 0; y--) for (let x = W - 1; x >= 0; x--) { const i = y * W + x; if (!dist2b[i]) continue;
      if (x < W - 1) dist2b[i] = Math.min(dist2b[i], dist2b[i + 1] + 1); if (y < H - 1) dist2b[i] = Math.min(dist2b[i], dist2b[i + W] + 1); }
    for (let y = R; y < H - R; y++) for (let x = R; x < W - R; x++) {
      const i = y * W + x; if (!near[i]) { valid[i] = 1; srcs.push(i); } }
    const targets = [];
    for (let y = R; y < H - R; y++) for (let x = R; x < W - R; x++) if (near[y * W + x]) targets.push(y * W + x);
    if (srcs.length < 20 || !targets.length) { prev = { cur, W, H, nnf: null }; continue; }

    const nnf = new Int32Array(N).fill(-1), dist = new Float32Array(N);
    const rnd = () => srcs[(Math.random() * srcs.length) | 0];
    const patchDist = (t, s, best) => {
      let d = 0;
      for (let dy = -R; dy <= R; dy++) {
        let tp = (t + dy * W - R) * 3, sp = (s + dy * W - R) * 3;
        for (let k = 0; k < (2 * R + 1) * 3; k++) { const e = cur[tp + k] - cur[sp + k]; d += e * e; }
        if (d > best) return d;
      }
      return d;
    };
    for (const t of targets) {
      let s = -1;
      if (prev && prev.nnf) {
        const x = t % W, y = (t / W) | 0, px = Math.min(prev.W - 1, x >> 1), py = Math.min(prev.H - 1, y >> 1);
        const c = prev.nnf[py * prev.W + px];
        if (c >= 0) { const sx = (c % prev.W) * 2 + (x & 1), sy = ((c / prev.W) | 0) * 2 + (y & 1);
          if (sx < W && sy < H && valid[sy * W + sx]) s = sy * W + sx; }
      }
      nnf[t] = s >= 0 ? s : rnd();
    }

    const iters = L === levels.length - 1 ? 10 : L === 0 ? 4 : 6;
    const accR = new Float32Array(N), accG = new Float32Array(N), accB = new Float32Array(N), accW = new Float32Array(N);
    for (let it = 0; it < iters; it++) {
      for (const t of targets) dist[t] = patchDist(t, nnf[t], Infinity);
      const fwd = it % 2 === 0, n = targets.length;
      for (let k = 0; k < n; k++) {
        const t = targets[fwd ? k : n - 1 - k];
        let best = dist[t], bs = nnf[t];
        // propagation depuis les voisins déjà traités
        const nb = fwd ? [t - 1, t - W] : [t + 1, t + W], sh = fwd ? [1, W] : [-1, -W];
        for (let m = 0; m < 2; m++) {
          const q = nb[m]; if (q < 0 || q >= N || nnf[q] < 0 || !near[q]) continue;
          const c = nnf[q] + sh[m];
          if (c >= 0 && c < N && valid[c] && c !== bs) { const d = patchDist(t, c, best); if (d < best) { best = d; bs = c; } }
        }
        // recherche aléatoire à rayon décroissant
        const sx = bs % W, sy = (bs / W) | 0;
        for (let w = Math.max(W, H); w >= 1; w >>= 1) {
          const cx = Math.min(W - R - 1, Math.max(R, sx + ((Math.random() * 2 - 1) * w | 0)));
          const cy = Math.min(H - R - 1, Math.max(R, sy + ((Math.random() * 2 - 1) * w | 0)));
          const c = cy * W + cx;
          if (valid[c] && c !== bs) { const d = patchDist(t, c, best); if (d < best) { best = d; bs = c; } }
        }
        nnf[t] = bs; dist[t] = best;
      }
      // vote : chaque pixel à remplir prend la moyenne des motifs qui le recouvrent
      accR.fill(0); accG.fill(0); accB.fill(0); accW.fill(0);
      let sum = 0; for (const t of targets) sum += dist[t];
      const sigma2 = 2 * Math.max(1, sum / targets.length);
      for (const t of targets) {
        const s = nnf[t], w = (Math.exp(-dist[t] / sigma2) + 1e-4) * Math.pow(1.3, -Math.min(dist2b[t], 40));
        for (let dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) {
          const p = t + dy * W + dx; if (!hole[p]) continue;
          const q = (s + dy * W + dx) * 3;
          accR[p] += cur[q] * w; accG[p] += cur[q + 1] * w; accB[p] += cur[q + 2] * w; accW[p] += w;
        }
      }
      for (let p = 0; p < N; p++) if (hole[p] && accW[p] > 0) {
        cur[p * 3] = accR[p] / accW[p]; cur[p * 3 + 1] = accG[p] / accW[p]; cur[p * 3 + 2] = accB[p] / accW[p]; }
    }
    prev = { cur, W, H, nnf };
  }
  return prev.cur;
}

self.onmessage = e => {
  const { rgb, hole, W, H } = e.data;
  try {
    const out = inpaint(rgb, hole, W, H);
    self.postMessage({ rgb: out }, [out.buffer]);
  } catch (err) {
    self.postMessage({ error: String(err && err.message || err) });
  }
};
