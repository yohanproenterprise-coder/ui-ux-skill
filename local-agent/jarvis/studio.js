// Studio photo de Jarvis : retouche non destructive, entièrement dans le navigateur.
(() => {
  const DEFAULTS = {
    exposure: 0, contrast: 0, highlights: 0, shadows: 0, saturation: 0, vibrance: 0, temperature: 0, tint: 0,
    sharpen: 0, blur: 0, vignette: 0, grain: 0, filter: "none", filterAmt: 100, rot: 0, flipH: false, flipV: false,
    crop: null, levels: null, text: { value: "", size: 6, color: "#ffffff", pos: "bas-droite" }
  };
  const SLIDERS = [
    ["Lumière", [["exposure", "Exposition"], ["contrast", "Contraste"], ["highlights", "Hautes lumières"], ["shadows", "Ombres"]]],
    ["Couleur", [["saturation", "Saturation"], ["vibrance", "Vibrance"], ["temperature", "Température"], ["tint", "Teinte"]]],
    ["Effets", [["sharpen", "Netteté", 0], ["blur", "Flou", 0], ["vignette", "Vignette", 0], ["grain", "Grain", 0]]]
  ];
  const clamp = v => v < 0 ? 0 : v > 255 ? 255 : v;
  const luma = (r, g, b) => .299 * r + .587 * g + .114 * b;
  const FILTERS = {
    none: ["Original", (r, g, b) => [r, g, b]],
    auto: ["Éclat", (r, g, b) => { const l = luma(r, g, b); return [l + (r - l) * 1.25 + 6, l + (g - l) * 1.25 + 6, l + (b - l) * 1.25 + 4]; }],
    nb: ["Noir & blanc", (r, g, b) => { const l = luma(r, g, b); return [l, l, l]; }],
    noir: ["Noir intense", (r, g, b) => { const l = (luma(r, g, b) - 128) * 1.45 + 128; return [l, l, l]; }],
    sepia: ["Sépia", (r, g, b) => [r * .393 + g * .769 + b * .189, r * .349 + g * .686 + b * .168, r * .272 + g * .534 + b * .131]],
    vintage: ["Vintage", (r, g, b) => { const l = luma(r, g, b); return [(l + (r - l) * .7) * .88 + 34, (l + (g - l) * .7) * .84 + 26, (l + (b - l) * .7) * .72 + 22]; }],
    fade: ["Pastel", (r, g, b) => [r * .82 + 36, g * .82 + 36, b * .82 + 40]],
    vif: ["Vif", (r, g, b) => { const l = luma(r, g, b); return [(l + (r - l) * 1.45 - 128) * 1.08 + 128, (l + (g - l) * 1.45 - 128) * 1.08 + 128, (l + (b - l) * 1.45 - 128) * 1.08 + 128]; }],
    chaud: ["Chaud", (r, g, b) => [r + 18, g + 6, b - 16]],
    froid: ["Froid", (r, g, b) => [r - 14, g + 2, b + 20]],
    cinema: ["Cinéma", (r, g, b) => { const l = luma(r, g, b), t = (l - 128) / 128;
      return t < 0 ? [r + 22 * t, g - 6 * t, b - 26 * t] : [r + 20 * t, g + 6 * t, b - 18 * t]; }],
    drama: ["Dramatique", (r, g, b) => { const l = luma(r, g, b); return [(l + (r - l) * .7 - 128) * 1.4 + 128, (l + (g - l) * .7 - 128) * 1.4 + 128, (l + (b - l) * .7 - 128) * 1.4 + 128]; }]
  };

  const S = { full: null, prev: null, name: "photo", p: clone(DEFAULTS), hist: [], fut: [], tab: "adjust", cropRatio: null, cropBox: null, compare: false };
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  const el = (tag, attrs = {}, html = "") => { const e = document.createElement(tag); Object.assign(e, attrs); if (html) e.innerHTML = html; return e; };
  const q = s => document.querySelector(s);

  // ---------------------------------------------------------------- interface --
  const root = el("div", { id: "studio" });
  root.innerHTML = `
    <div class="st-top">
      <h2><span class="reactor" style="--s:22px"><i></i><i></i><i></i></span>STUDIO<small id="st-name"></small></h2>
      <button class="pill" id="st-open" title="Ouvrir une autre photo"><svg><use href="#i-image"/></svg><span class="lbl">Ouvrir</span></button>
      <button class="pill" id="st-undo" title="Annuler (Ctrl+Z)">↶<span class="lbl">Annuler</span></button>
      <button class="pill" id="st-redo" title="Rétablir (Ctrl+Y)">↷<span class="lbl">Rétablir</span></button>
      <button class="pill" id="st-compare" title="Maintenir pour voir l'original">◐<span class="lbl">Avant / après</span></button>
      <button class="pill" id="st-reset" title="Tout réinitialiser">⟲<span class="lbl">Réinitialiser</span></button>
      <button class="pill primary" id="st-close">Fermer</button>
    </div>
    <div class="st-body">
      <div class="st-stage" id="st-stage">
        <div class="st-empty" id="st-empty">
          <div class="st-drop" id="st-drop">
            <div class="reactor" style="--s:64px;margin:0 auto"><i></i><i></i><i></i></div>
            <h3>Glisse une photo ici</h3>
            <p>ou colle-la (Ctrl+V), ou choisis-la sur ton PC</p>
            <button class="st-btn primary" id="st-pick">Choisir une photo</button>
          </div>
          <div class="st-label">Photos récentes sur ce PC</div>
          <div class="st-gallery" id="st-gallery"><span class="st-note">Chargement…</span></div>
        </div>
        <canvas id="st-canvas" hidden></canvas>
        <div id="st-crop"><i data-h="nw"></i><i data-h="ne"></i><i data-h="sw"></i><i data-h="se"></i></div>
        <div class="st-badge" id="st-badge">Original</div>
      </div>
      <div class="st-panel">
        <div class="st-tabs">
          <button data-tab="adjust" class="on">Réglages</button><button data-tab="filters">Filtres</button>
          <button data-tab="crop">Recadrer</button><button data-tab="text">Texte</button><button data-tab="export">Exporter</button>
        </div>
        <div class="st-pane on" data-pane="adjust">
          <button class="st-btn primary wide" id="st-auto" style="margin:0 0 8px">✨ Amélioration automatique</button>
          <div id="st-sliders"></div>
        </div>
        <div class="st-pane" data-pane="filters">
          <div class="st-filters" id="st-filters"></div>
          <div class="st-row" style="margin-top:14px"><label>Intensité du filtre <span id="v-filterAmt">100</span></label>
            <input type="range" min="0" max="100" value="100" data-k="filterAmt"></div>
        </div>
        <div class="st-pane" data-pane="crop">
          <div class="st-label" style="margin-top:0">Format</div>
          <div class="st-grid" id="st-ratios">
            <button class="st-btn on" data-r="">Libre</button><button class="st-btn" data-r="1">Carré</button><button class="st-btn" data-r="0.8">4:5</button>
            <button class="st-btn" data-r="1.5">3:2</button><button class="st-btn" data-r="1.7778">16:9</button><button class="st-btn" data-r="0.5625">9:16</button>
          </div>
          <div class="st-label">Rotation</div>
          <div class="st-grid two">
            <button class="st-btn" data-geo="left">↺ Gauche</button><button class="st-btn" data-geo="right">↻ Droite</button>
            <button class="st-btn" data-geo="flipH">⇋ Miroir</button><button class="st-btn" data-geo="flipV">⇵ Retourner</button>
          </div>
          <button class="st-btn primary wide" id="st-crop-apply">Appliquer le recadrage</button>
          <button class="st-btn wide" id="st-crop-clear">Enlever le recadrage</button>
          <p class="st-note">Déplace le cadre ou tire ses coins sur la photo.</p>
        </div>
        <div class="st-pane" data-pane="text">
          <div class="st-row"><label>Texte (signature, légende…)</label><input type="text" id="st-text" placeholder="Ex : © Yohan 2026"></div>
          <div class="st-row"><label>Taille <span id="v-tsize">6</span></label><input type="range" min="2" max="20" value="6" id="st-tsize"></div>
          <div class="st-grid two">
            <div class="st-row"><label>Couleur</label><input type="color" id="st-tcolor" value="#ffffff"></div>
            <div class="st-row"><label>Position</label><select id="st-tpos">
              <option value="bas-droite">Bas droite</option><option value="bas-gauche">Bas gauche</option><option value="bas-centre">Bas centre</option>
              <option value="haut-gauche">Haut gauche</option><option value="haut-droite">Haut droite</option><option value="centre">Centre</option></select></div>
          </div>
        </div>
        <div class="st-pane" data-pane="export">
          <div class="st-row"><label>Format</label><select id="st-fmt">
            <option value="image/jpeg">JPEG (photos, léger)</option><option value="image/png">PNG (qualité maximale)</option><option value="image/webp">WebP (web, très léger)</option></select></div>
          <div class="st-row"><label>Qualité <span id="v-quality">90</span></label><input type="range" min="40" max="100" value="90" id="st-quality"></div>
          <div class="st-row"><label>Taille</label><select id="st-size">
            <option value="0">Originale</option><option value="3840">4K (3840 px)</option><option value="2048">Grande (2048 px)</option>
            <option value="1080">Réseaux sociaux (1080 px)</option><option value="800">Petite (800 px)</option></select></div>
          <button class="st-btn primary wide" id="st-save">Enregistrer dans Jarvis</button>
          <button class="st-btn wide" id="st-download">Télécharger</button>
          <button class="st-btn wide" id="st-ask">Envoyer à Jarvis (conseils, légende…)</button>
          <div class="st-msg" id="st-msg"></div>
          <p class="st-note">L'original n'est jamais modifié : Jarvis enregistre une copie dans le dossier « photos ».</p>
        </div>
      </div>
    </div>
    <input type="file" id="st-file" accept="image/*" hidden>`;
  document.body.appendChild(root);
  const canvas = q("#st-canvas"), ctx = canvas.getContext("2d", { willReadFrequently: true });

  // curseurs
  const sl = q("#st-sliders");
  for (const [group, items] of SLIDERS) {
    sl.insertAdjacentHTML("beforeend", `<div class="st-label">${group}</div>`);
    for (const [k, label, min = -100] of items)
      sl.insertAdjacentHTML("beforeend", `<div class="st-row"><label>${label} <span id="v-${k}">0</span></label>
        <input type="range" min="${min}" max="100" value="0" data-k="${k}"></div>`);
  }
  root.querySelectorAll("input[data-k]").forEach(inp => {
    inp.addEventListener("input", () => { S.p[inp.dataset.k] = +inp.value; q(`#v-${inp.dataset.k}`).textContent = inp.value; schedule(); });
    inp.addEventListener("change", commit);
    inp.addEventListener("dblclick", () => { S.p[inp.dataset.k] = inp.dataset.k === "filterAmt" ? 100 : 0; commit(); sync(); schedule(); });
  });

  // ------------------------------------------------------------- chargement --
  async function loadFrom(src, name) {
    const img = new Image();
    img.decoding = "async";
    img.src = src;
    try { await img.decode(); } catch (e) { return msg("Impossible d'ouvrir cette image (format non pris en charge, ex : HEIC).", true); }
    S.full = document.createElement("canvas");
    S.full.width = img.naturalWidth; S.full.height = img.naturalHeight;
    S.full.getContext("2d").drawImage(img, 0, 0);
    const k = Math.min(1, 1400 / Math.max(img.naturalWidth, img.naturalHeight));
    S.prev = document.createElement("canvas");
    S.prev.width = Math.round(img.naturalWidth * k); S.prev.height = Math.round(img.naturalHeight * k);
    S.prev.getContext("2d").drawImage(img, 0, 0, S.prev.width, S.prev.height);
    S.name = (name || "photo").replace(/\.[^.]+$/, "");
    S.p = clone(DEFAULTS); S.hist = []; S.fut = [];
    q("#st-name").textContent = `${name || "photo"} · ${img.naturalWidth}×${img.naturalHeight}`;
    q("#st-empty").hidden = true; canvas.hidden = false;
    sync(); render(); buildFilterThumbs(); setTab(S.tab);
  }
  function openFile(f) {
    if (!f || !f.type.startsWith("image/")) return;
    const r = new FileReader(); r.onload = () => loadFrom(r.result, f.name); r.readAsDataURL(f);
  }
  async function gallery() {
    const g = q("#st-gallery");
    try {
      const list = await (await fetch("/images")).json();
      g.innerHTML = list.length ? "" : '<span class="st-note">Aucune photo trouvée dans Images, Bureau, Téléchargements ou Documents.</span>';
      list.forEach(it => {
        const b = el("button", { title: it.path });
        b.innerHTML = `<img loading="lazy" alt="" src="/file?path=${encodeURIComponent(it.path)}">`;
        b.onclick = () => loadFrom(`/file?path=${encodeURIComponent(it.path)}`, it.name);
        g.appendChild(b);
      });
    } catch (e) { g.innerHTML = '<span class="st-note">Galerie indisponible.</span>'; }
  }

  // --------------------------------------------------------------- rendu --
  function geometry(src, p, withCrop) {
    const rot = ((p.rot % 360) + 360) % 360, swap = rot === 90 || rot === 270;
    const g = document.createElement("canvas");
    g.width = swap ? src.height : src.width; g.height = swap ? src.width : src.height;
    const c = g.getContext("2d");
    c.translate(g.width / 2, g.height / 2); c.rotate(rot * Math.PI / 180); c.scale(p.flipH ? -1 : 1, p.flipV ? -1 : 1);
    c.drawImage(src, -src.width / 2, -src.height / 2);
    if (!withCrop || !p.crop) return g;
    const { x, y, w, h } = p.crop, out = document.createElement("canvas");
    out.width = Math.max(1, Math.round(w * g.width)); out.height = Math.max(1, Math.round(h * g.height));
    out.getContext("2d").drawImage(g, x * g.width, y * g.height, w * g.width, h * g.height, 0, 0, out.width, out.height);
    return out;
  }
  function autoLevels(src) {
    const c = document.createElement("canvas"), k = Math.min(1, 300 / Math.max(src.width, src.height));
    c.width = Math.max(1, src.width * k); c.height = Math.max(1, src.height * k);
    const cx = c.getContext("2d"); cx.drawImage(src, 0, 0, c.width, c.height);
    const d = cx.getImageData(0, 0, c.width, c.height).data, hist = [new Array(256).fill(0), new Array(256).fill(0), new Array(256).fill(0)];
    for (let i = 0; i < d.length; i += 4) { hist[0][d[i]]++; hist[1][d[i + 1]]++; hist[2][d[i + 2]]++; }
    const n = d.length / 4, cut = n * .005;
    return hist.map(h => { let lo = 0, hi = 255, s = 0; while (lo < 255 && (s += h[lo]) < cut) lo++; s = 0; while (hi > 0 && (s += h[hi]) < cut) hi--;
      return hi - lo < 30 ? [0, 255] : [lo, hi]; });
  }
  function pixels(cv, p, full) {
    const c = cv.getContext("2d", { willReadFrequently: true }), W = cv.width, H = cv.height;
    const img = c.getImageData(0, 0, W, H), d = img.data;
    const lut = [0, 1, 2].map(ch => {
      const t = new Float32Array(256), lv = p.levels && p.levels[ch];
      const ex = Math.pow(2, p.exposure / 100), ct = p.contrast >= 0 ? 1 + p.contrast / 60 : 1 + p.contrast / 110;
      for (let v = 0; v < 256; v++) {
        let x = lv ? (v - lv[0]) * 255 / (lv[1] - lv[0]) : v;
        x = (x * ex - 128) * ct + 128;
        t[v] = x;
      }
      return t;
    });
    const f = FILTERS[p.filter] ? FILTERS[p.filter][1] : null, fa = p.filterAmt / 100;
    const sat = 1 + p.saturation / 100, vib = p.vibrance / 100, temp = p.temperature * .3, tint = p.tint * .25;
    const hl = p.highlights / 100, sh = p.shadows / 100, vg = p.vignette / 100, grain = p.grain * .35;
    const cx = W / 2, cy = H / 2, maxd = Math.hypot(cx, cy);
    for (let y = 0, i = 0; y < H; y++) for (let x = 0; x < W; x++, i += 4) {
      let r = lut[0][d[i]], g = lut[1][d[i + 1]], b = lut[2][d[i + 2]];
      if (hl || sh) {
        const l = luma(r, g, b) / 255;
        const adj = (sh > 0 ? sh * 70 * Math.pow(1 - l, 2) : sh * 50 * (1 - l)) + (hl < 0 ? hl * 70 * l * l : hl * 45 * l * l);
        r += adj; g += adj; b += adj;
      }
      if (temp || tint) { r += temp; b -= temp; g += tint; }
      if (sat !== 1 || vib) {
        const l = luma(r, g, b), mx = Math.max(r, g, b), mn = Math.min(r, g, b);
        const k = sat * (1 + vib * (1 - (mx - mn) / 255));
        r = l + (r - l) * k; g = l + (g - l) * k; b = l + (b - l) * k;
      }
      if (f && p.filter !== "none") {
        const [fr, fg, fb] = f(r, g, b);
        r += (fr - r) * fa; g += (fg - g) * fa; b += (fb - b) * fa;
      }
      if (vg) {
        const dd = Math.hypot(x - cx, y - cy) / maxd, k = 1 - vg * Math.pow(Math.max(0, dd - .35) / .65, 1.6) * .85;
        r *= k; g *= k; b *= k;
      }
      if (grain) { const n = (Math.random() - .5) * grain; r += n; g += n; b += n; }
      d[i] = clamp(r); d[i + 1] = clamp(g); d[i + 2] = clamp(b);
    }
    if (p.sharpen > 0) sharpen(img, W, H, p.sharpen / 100 * (full ? 1.2 : 1));
    c.putImageData(img, 0, 0);
    if (p.blur > 0) {
      const t = document.createElement("canvas"); t.width = W; t.height = H;
      const tc = t.getContext("2d"); tc.filter = `blur(${(p.blur / 100) * Math.max(W, H) / 150}px)`; tc.drawImage(cv, 0, 0);
      c.clearRect(0, 0, W, H); c.drawImage(t, 0, 0);
    }
    drawText(c, W, H, p.text);
  }
  function sharpen(img, W, H, a) {
    const s = new Uint8ClampedArray(img.data), d = img.data, k = 1 + 4 * a;
    for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
      const i = (y * W + x) * 4;
      for (let ch = 0; ch < 3; ch++)
        d[i + ch] = s[i + ch] * k - a * (s[i + ch - 4] + s[i + ch + 4] + s[i + ch - W * 4] + s[i + ch + W * 4]);
    }
  }
  function drawText(c, W, H, t) {
    if (!t || !t.value) return;
    const size = Math.max(10, W * t.size / 100), m = size * .7;
    c.font = `600 ${size}px "Segoe UI", Inter, system-ui, sans-serif`;
    const [v, hpos] = t.pos === "centre" ? ["centre", "centre"] : t.pos.split("-");
    c.textAlign = hpos === "gauche" ? "left" : hpos === "droite" ? "right" : "center";
    c.textBaseline = v === "haut" ? "top" : v === "bas" ? "bottom" : "middle";
    const x = hpos === "gauche" ? m : hpos === "droite" ? W - m : W / 2, y = v === "haut" ? m : v === "bas" ? H - m : H / 2;
    c.shadowColor = "rgba(0,0,0,.55)"; c.shadowBlur = size * .25; c.shadowOffsetY = size * .05;
    c.fillStyle = t.color; c.fillText(t.value, x, y);
    c.shadowColor = "transparent";
  }
  function process(src, p, full) {
    const g = geometry(src, p, true);
    pixels(g, p, full);
    return g;
  }
  let pending = false;
  function schedule() { if (!pending) { pending = true; requestAnimationFrame(() => { pending = false; render(); }); } }
  function render() {
    if (!S.prev) return;
    const cropping = S.tab === "crop";
    let out;
    if (S.compare) out = geometry(S.prev, { ...DEFAULTS, rot: S.p.rot, flipH: S.p.flipH, flipV: S.p.flipV, crop: S.p.crop }, true);
    else if (cropping) { out = geometry(S.prev, S.p, false); pixels(out, { ...S.p, text: null }, false); }
    else out = process(S.prev, S.p, false);
    canvas.width = out.width; canvas.height = out.height; ctx.drawImage(out, 0, 0);
    q("#st-badge").style.display = S.compare ? "block" : "none";
    if (cropping) placeCrop();
  }
  function buildFilterThumbs() {
    const box = q("#st-filters"); box.innerHTML = "";
    const k = 110 / Math.max(S.prev.width, S.prev.height), base = document.createElement("canvas");
    base.width = Math.max(1, S.prev.width * k); base.height = Math.max(1, S.prev.height * k);
    base.getContext("2d").drawImage(S.prev, 0, 0, base.width, base.height);
    for (const [key, [label]] of Object.entries(FILTERS)) {
      const b = el("button", { className: S.p.filter === key ? "on" : "" }), c = document.createElement("canvas");
      c.width = base.width; c.height = base.height; c.getContext("2d").drawImage(base, 0, 0);
      pixels(c, { ...DEFAULTS, filter: key }, false);
      b.appendChild(c); b.appendChild(document.createTextNode(label));
      b.onclick = () => { S.p.filter = key; commit(); box.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b)); schedule(); };
      box.appendChild(b);
    }
  }

  // ---------------------------------------------------------- historique --
  let lastCommitted = JSON.stringify(DEFAULTS);
  function commit() {
    const now = JSON.stringify(S.p);
    if (now === lastCommitted) return;
    S.hist.push(lastCommitted); S.fut = []; lastCommitted = now; buttons();
  }
  function undo() { if (!S.hist.length) return; S.fut.push(JSON.stringify(S.p)); S.p = JSON.parse(S.hist.pop()); lastCommitted = JSON.stringify(S.p); sync(); render(); }
  function redo() { if (!S.fut.length) return; S.hist.push(JSON.stringify(S.p)); S.p = JSON.parse(S.fut.pop()); lastCommitted = JSON.stringify(S.p); sync(); render(); }
  function buttons() { q("#st-undo").disabled = !S.hist.length; q("#st-redo").disabled = !S.fut.length; }
  function sync() {
    root.querySelectorAll("input[data-k]").forEach(inp => { inp.value = S.p[inp.dataset.k]; q(`#v-${inp.dataset.k}`).textContent = S.p[inp.dataset.k]; });
    q("#st-text").value = S.p.text.value; q("#st-tsize").value = S.p.text.size; q("#v-tsize").textContent = S.p.text.size;
    q("#st-tcolor").value = S.p.text.color; q("#st-tpos").value = S.p.text.pos;
    q("#st-filters").querySelectorAll("button").forEach((b, i) => b.classList.toggle("on", Object.keys(FILTERS)[i] === S.p.filter));
    buttons();
  }

  // ------------------------------------------------------------- recadrage --
  const cropEl = q("#st-crop");
  function placeCrop() {
    if (!S.cropBox) S.cropBox = S.p.crop ? { ...S.p.crop } : { x: .05, y: .05, w: .9, h: .9 };
    const r = canvas.getBoundingClientRect(), sr = q("#st-stage").getBoundingClientRect(), b = S.cropBox;
    Object.assign(cropEl.style, { display: "block", left: `${r.left - sr.left + b.x * r.width}px`, top: `${r.top - sr.top + b.y * r.height}px`,
      width: `${b.w * r.width}px`, height: `${b.h * r.height}px` });
  }
  function applyRatio(ratio) {
    S.cropRatio = ratio;
    if (!ratio) return placeCrop();
    const aspect = canvas.width / canvas.height; // w_norm/h_norm = ratio / aspect
    let w = .9, h = w * aspect / ratio;
    if (h > .9) { h = .9; w = h * ratio / aspect; }
    S.cropBox = { x: (1 - w) / 2, y: (1 - h) / 2, w, h }; placeCrop();
  }
  let drag = null;
  cropEl.addEventListener("pointerdown", e => {
    e.preventDefault(); cropEl.setPointerCapture(e.pointerId);
    drag = { h: e.target.dataset.h || "move", x: e.clientX, y: e.clientY, b: { ...S.cropBox } };
  });
  cropEl.addEventListener("pointermove", e => {
    if (!drag) return;
    const r = canvas.getBoundingClientRect(), dx = (e.clientX - drag.x) / r.width, dy = (e.clientY - drag.y) / r.height, b = { ...drag.b };
    if (drag.h === "move") { b.x = Math.min(Math.max(0, b.x + dx), 1 - b.w); b.y = Math.min(Math.max(0, b.y + dy), 1 - b.h); }
    else {
      const west = drag.h.includes("w"), north = drag.h.includes("n");
      let x1 = b.x, y1 = b.y, x2 = b.x + b.w, y2 = b.y + b.h;
      if (west) x1 = Math.min(Math.max(0, x1 + dx), x2 - .05); else x2 = Math.max(Math.min(1, x2 + dx), x1 + .05);
      if (north) y1 = Math.min(Math.max(0, y1 + dy), y2 - .05); else y2 = Math.max(Math.min(1, y2 + dy), y1 + .05);
      if (S.cropRatio) {
        const aspect = canvas.width / canvas.height, hNeed = (x2 - x1) * aspect / S.cropRatio;
        if (north) y1 = Math.max(0, y2 - hNeed); else y2 = Math.min(1, y1 + hNeed);
        const wFix = (y2 - y1) * S.cropRatio / aspect;
        if (west) x1 = x2 - wFix; else x2 = x1 + wFix;
      }
      Object.assign(b, { x: x1, y: y1, w: x2 - x1, h: y2 - y1 });
    }
    S.cropBox = b; placeCrop();
  });
  cropEl.addEventListener("pointerup", () => { drag = null; });
  q("#st-ratios").addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    q("#st-ratios").querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
    applyRatio(b.dataset.r ? +b.dataset.r : null);
  });
  root.querySelectorAll("[data-geo]").forEach(b => b.onclick = () => {
    const g = b.dataset.geo;
    if (g === "left") S.p.rot -= 90; else if (g === "right") S.p.rot += 90;
    else if (g === "flipH") S.p.flipH = !S.p.flipH; else S.p.flipV = !S.p.flipV;
    S.p.crop = null; S.cropBox = null; commit(); render();
  });
  q("#st-crop-apply").onclick = () => { S.p.crop = { ...S.cropBox }; commit(); setTab("adjust"); };
  q("#st-crop-clear").onclick = () => { S.p.crop = null; S.cropBox = null; commit(); render(); };

  // ----------------------------------------------------------------- texte --
  const setText = () => { S.p.text = { value: q("#st-text").value, size: +q("#st-tsize").value, color: q("#st-tcolor").value, pos: q("#st-tpos").value };
    q("#v-tsize").textContent = S.p.text.size; schedule(); };
  ["#st-text", "#st-tsize", "#st-tcolor", "#st-tpos"].forEach(s => { q(s).addEventListener("input", setText); q(s).addEventListener("change", commit); });

  // ---------------------------------------------------------------- export --
  q("#st-quality").oninput = e => q("#v-quality").textContent = e.target.value;
  function exportData() {
    let out = process(S.full, S.p, true);
    const max = +q("#st-size").value;
    if (max && Math.max(out.width, out.height) > max) {
      const k = max / Math.max(out.width, out.height), t = document.createElement("canvas");
      t.width = Math.round(out.width * k); t.height = Math.round(out.height * k);
      const tc = t.getContext("2d"); tc.imageSmoothingQuality = "high"; tc.drawImage(out, 0, 0, t.width, t.height); out = t;
    }
    const fmt = q("#st-fmt").value, ext = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp" }[fmt];
    if (fmt === "image/jpeg") { const t = document.createElement("canvas"); t.width = out.width; t.height = out.height;
      const tc = t.getContext("2d"); tc.fillStyle = "#fff"; tc.fillRect(0, 0, t.width, t.height); tc.drawImage(out, 0, 0); out = t; }
    return { data: out.toDataURL(fmt, +q("#st-quality").value / 100), name: `${S.name}-retouche.${ext}`, w: out.width, h: out.height };
  }
  function msg(text, err) { const m = q("#st-msg"); m.textContent = text; m.style.color = err ? "var(--err)" : "var(--ok)"; }
  async function busyDo(btn, fn) { const t = btn.textContent; btn.disabled = true; btn.textContent = "Traitement…";
    await new Promise(r => setTimeout(r, 30)); try { await fn(); } finally { btn.disabled = false; btn.textContent = t; } }
  q("#st-save").onclick = e => busyDo(e.target, async () => {
    const x = exportData();
    const r = await (await fetch("/save_image", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: x.name, data: x.data }) })).json();
    r.error ? msg(r.error, true) : msg(`Enregistrée (${x.w}×${x.h}) : ${r.path}`);
  });
  q("#st-download").onclick = e => busyDo(e.target, async () => {
    const x = exportData(), a = el("a", { href: x.data, download: x.name }); document.body.appendChild(a); a.click(); a.remove();
    msg(`Téléchargée (${x.w}×${x.h}).`);
  });
  q("#st-ask").onclick = e => busyDo(e.target, async () => {
    const sizeSel = q("#st-size"), old = sizeSel.value; sizeSel.value = "1080";
    const x = exportData(); sizeSel.value = old;
    if (window.jarvisAttach) window.jarvisAttach(x.data, x.name, "Que penses-tu de cette photo retouchée ? Propose aussi une légende.");
    close();
  });

  // ------------------------------------------------------------- navigation --
  function setTab(t) {
    S.tab = t;
    root.querySelectorAll(".st-tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === t));
    root.querySelectorAll(".st-pane").forEach(p => p.classList.toggle("on", p.dataset.pane === t));
    if (t !== "crop") { cropEl.style.display = "none"; S.cropBox = null; }
    render();
  }
  root.querySelector(".st-tabs").addEventListener("click", e => { const b = e.target.closest("button"); if (b) setTab(b.dataset.tab); });
  q("#st-auto").onclick = () => { if (!S.prev) return; S.p.levels = autoLevels(S.prev); S.p.vibrance = Math.max(S.p.vibrance, 18);
    S.p.sharpen = Math.max(S.p.sharpen, 15); commit(); sync(); render(); };
  q("#st-reset").onclick = () => { if (!S.prev) return; S.p = clone(DEFAULTS); commit(); sync(); setTab("adjust"); };
  q("#st-undo").onclick = undo; q("#st-redo").onclick = redo;
  const cmp = q("#st-compare");
  cmp.addEventListener("pointerdown", () => { S.compare = true; render(); });
  ["pointerup", "pointerleave", "pointercancel"].forEach(ev => cmp.addEventListener(ev, () => { if (S.compare) { S.compare = false; render(); } }));
  q("#st-pick").onclick = q("#st-open").onclick = () => q("#st-file").click();
  q("#st-file").onchange = e => { openFile(e.target.files[0]); e.target.value = ""; };
  const drop = q("#st-drop");
  root.addEventListener("dragover", e => { e.preventDefault(); e.stopPropagation(); drop.classList.add("over"); });
  root.addEventListener("dragleave", () => drop.classList.remove("over"));
  root.addEventListener("drop", e => { e.preventDefault(); e.stopPropagation(); drop.classList.remove("over"); openFile(e.dataTransfer.files[0]); });
  document.addEventListener("paste", e => { if (root.classList.contains("open") && e.clipboardData.files.length) { e.stopPropagation(); openFile(e.clipboardData.files[0]); } }, true);
  document.addEventListener("keydown", e => {
    if (!root.classList.contains("open") || e.target.matches("input[type=text]")) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? redo() : undo(); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") { e.preventDefault(); redo(); }
    else if (e.key === "Escape") close();
  });
  addEventListener("resize", () => { if (S.tab === "crop") placeCrop(); });
  function close() { root.classList.remove("open"); }
  q("#st-close").onclick = close;

  window.openStudio = path => {
    root.classList.add("open"); buttons();
    if (path) loadFrom(`/file?path=${encodeURIComponent(path)}`, path.split(/[\\/]/).pop());
    else if (!S.prev) gallery();
  };
})();
