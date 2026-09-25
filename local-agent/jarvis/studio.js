// Studio photo de Jarvis : retouche non destructive, entièrement dans le navigateur.
(() => {
  const DEFAULTS = {
    exposure: 0, contrast: 0, highlights: 0, shadows: 0, saturation: 0, vibrance: 0, temperature: 0, tint: 0,
    sharpen: 0, blur: 0, vignette: 0, grain: 0, denoise: 0, clarity: 0, enhance: 0, enh: null, filter: "none", filterAmt: 100, rot: 0, flipH: false, flipV: false,
    crop: null, levels: null, text: { value: "", size: 6, color: "#ffffff", pos: "bas-droite" }
  };
  const SLIDERS = [
    ["Lumière", [["exposure", "Exposition"], ["contrast", "Contraste"], ["highlights", "Hautes lumières"], ["shadows", "Ombres"]]],
    ["Couleur", [["saturation", "Saturation"], ["vibrance", "Vibrance"], ["temperature", "Température"], ["tint", "Teinte"]]],
    ["Qualité", [["denoise", "Réduction du bruit", 0], ["clarity", "Clarté"], ["sharpen", "Netteté", 0]]],
    ["Effets", [["blur", "Flou", 0], ["vignette", "Vignette", 0], ["grain", "Grain", 0]]]
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

  const S = { full: null, prev: null, name: "photo", p: clone(DEFAULTS), hist: [], fut: [], tab: "adjust", cropRatio: null, cropBox: null,
              compare: false, baseHist: [], erase: false };
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
        <canvas id="st-mask"></canvas>
        <div class="st-busy" id="st-busy"><div class="reactor fast" style="--s:54px"><i></i><i></i><i></i></div><span>Reconstruction du fond…</span></div>
        <div id="st-crop"><i data-h="nw"></i><i data-h="ne"></i><i data-h="sw"></i><i data-h="se"></i></div>
        <div class="st-badge" id="st-badge">Original</div>
      </div>
      <div class="st-panel">
        <div class="st-tabs">
          <button data-tab="adjust" class="on">Réglages</button><button data-tab="filters">Filtres</button>
          <button data-tab="heal">Gomme magique</button><button data-tab="crop">Recadrer</button><button data-tab="text">Texte</button><button data-tab="export">Exporter</button>
        </div>
        <div class="st-pane on" data-pane="adjust">
          <button class="st-btn primary wide" id="st-enhance" style="margin:0 0 10px">✨ Améliorer automatiquement</button>
          <div class="st-row"><label>Intensité de l'amélioration <span id="v-enhance">0</span></label>
            <input type="range" min="0" max="100" value="0" data-k="enhance"></div>
          <p class="st-note" style="margin:-4px 0 4px">Rendu naturel : lumière, balance des blancs, bruit et netteté sont dosés selon ta photo.
            Les couleurs et la peau sont préservées.</p>
          <div id="st-sliders"></div>
        </div>
        <div class="st-pane" data-pane="filters">
          <div class="st-filters" id="st-filters"></div>
          <div class="st-row" style="margin-top:14px"><label>Intensité du filtre <span id="v-filterAmt">100</span></label>
            <input type="range" min="0" max="100" value="100" data-k="filterAmt"></div>
        </div>
        <div class="st-pane" data-pane="heal">
          <p class="st-note" style="margin-top:0">Peins sur ce que tu veux faire disparaître (personne, objet, texte, tache…),
            puis clique sur « Effacer ». Le fond se reconstruit à partir de ce qui l'entoure.</p>
          <div class="st-label">Moteur</div>
          <div class="st-grid two">
            <button class="st-btn" id="st-eng-classic" title="Instantané, idéal pour ciel, mer, murs, herbe">⚡ Classique</button>
            <button class="st-btn" id="st-eng-ai" title="Intelligence artificielle LaMa : reconstruit les formes (bords d'objets, visages de fond…)">✦ IA</button>
          </div>
          <div id="st-ai-box" class="st-note" hidden></div>
          <div class="st-row" style="margin-top:12px"><label>Taille du pinceau <span id="v-brush">30</span></label>
            <input type="range" min="4" max="150" value="30" id="st-brush"></div>
          <div class="st-grid two">
            <button class="st-btn on" id="st-paint">🖌 Pinceau</button><button class="st-btn" id="st-erase">◌ Gomme</button>
          </div>
          <button class="st-btn primary wide" id="st-heal">✦ Effacer la zone peinte</button>
          <button class="st-btn wide" id="st-heal-again" disabled>↻ Autre proposition</button>
          <button class="st-btn wide" id="st-mask-clear">Enlever le tracé</button>
          <button class="st-btn wide" id="st-heal-undo" disabled>↶ Annuler la dernière gomme</button>
          <div class="st-msg" id="st-heal-msg"></div>
          <p class="st-note">Astuce : couvre bien tout l'objet, avec son ombre, en débordant un peu. Pour une grande zone,
            efface en plusieurs fois. Plus le fond est régulier (ciel, mur, sable, herbe), plus le résultat est naturel.</p>
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
          <div class="st-label" style="margin-top:4px">Redimensionner</div>
          <div class="st-row"><select id="st-size">
            <option value="1">Taille originale</option><option value="x2">Agrandir ×2</option><option value="x4">Agrandir ×4</option>
            <option value="3840">4K (3840 px)</option><option value="2048">Grande (2048 px)</option>
            <option value="1080">Réseaux sociaux (1080 px)</option><option value="800">Petite (800 px)</option>
            <option value="custom">Personnalisée…</option></select></div>
          <div class="st-grid two" style="align-items:end">
            <div class="st-row"><label>Largeur (px)</label><input type="number" id="st-w" min="1" max="16000"></div>
            <div class="st-row"><label>Hauteur (px)</label><input type="number" id="st-h" min="1" max="16000"></div>
          </div>
          <label class="check"><input type="checkbox" id="st-lock" checked> Garder les proportions</label>
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
  const mask = q("#st-mask"), mctx = mask.getContext("2d", { willReadFrequently: true });

  // curseurs
  const sl = q("#st-sliders");
  for (const [group, items] of SLIDERS) {
    sl.insertAdjacentHTML("beforeend", `<div class="st-label">${group}</div>`);
    for (const [k, label, min = -100] of items)
      sl.insertAdjacentHTML("beforeend", `<div class="st-row"><label>${label} <span id="v-${k}">0</span></label>
        <input type="range" min="${min}" max="100" value="0" data-k="${k}"></div>`);
  }
  root.querySelectorAll("input[data-k]").forEach(inp => {
    inp.addEventListener("input", () => { S.p[inp.dataset.k] = +inp.value;
      if (inp.dataset.k === "enhance" && !S.p.enh && S.prev) S.p.enh = analyze(S.prev); q(`#v-${inp.dataset.k}`).textContent = inp.value; schedule(); });
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
    makePrev(); S.baseHist = []; q("#st-heal-undo").disabled = true;
    S.name = (name || "photo").replace(/\.[^.]+$/, "");
    S.p = clone(DEFAULTS); S.hist = []; S.fut = [];
    q("#st-name").textContent = `${name || "photo"} · ${img.naturalWidth}×${img.naturalHeight}`;
    q("#st-empty").hidden = true; canvas.hidden = false;
    sync(); render(); buildFilterThumbs(); setTab(S.tab);
  }
  function makePrev() {
    const k = Math.min(1, 1400 / Math.max(S.full.width, S.full.height));
    S.prev = document.createElement("canvas");
    S.prev.width = Math.round(S.full.width * k); S.prev.height = Math.round(S.full.height * k);
    const c = S.prev.getContext("2d"); c.imageSmoothingQuality = "high"; c.drawImage(S.full, 0, 0, S.prev.width, S.prev.height);
    mask.width = S.prev.width; mask.height = S.prev.height;
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
    const scale = Math.max(W, H) / 1400;
    const dn = p.denoise / 100, cl = p.clarity / 100;
    let LB, L0;
    if (p.enhance > 0 && p.enh) enhance(d, W, H, p.enh, p.enhance / 100, scale);
    if (dn) denoiseYCC(d, W, H, dn, dn * .6, scale);
    if (cl) { const L = new Float32Array(W * H); for (let j = 0; j < W * H; j++) L[j] = luma(d[j * 4], d[j * 4 + 1], d[j * 4 + 2]);
      LB = boxBlur(L, W, H, Math.max(3, Math.round(18 * scale)), 3); L0 = L; }
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
    for (let y = 0, i = 0, j = 0; y < H; y++) for (let x = 0; x < W; x++, i += 4, j++) {
      let r = lut[0][d[i]], g = lut[1][d[i + 1]], b = lut[2][d[i + 2]];
      if (cl) { const det = (L0[j] - LB[j]) * cl * 1.4; r += det; g += det; b += det; }
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
    if (p.sharpen > 0) usm(d, W, H, p.sharpen / 100 * 1.1, Math.max(1, Math.round(1.1 * scale)), 3);
    c.putImageData(img, 0, 0);
    if (p.blur > 0) {
      const t = document.createElement("canvas"); t.width = W; t.height = H;
      const tc = t.getContext("2d"); tc.filter = `blur(${(p.blur / 100) * Math.max(W, H) / 150}px)`; tc.drawImage(cv, 0, 0);
      c.clearRect(0, 0, W, H); c.drawImage(t, 0, 0);
    }
    drawText(c, W, H, p.text);
  }
  // ------------------------------------------------ amélioration naturelle --
  function analyze(src) {
    const k = Math.min(1, 480 / Math.max(src.width, src.height)), c = document.createElement("canvas");
    c.width = Math.max(1, Math.round(src.width * k)); c.height = Math.max(1, Math.round(src.height * k));
    const cx = c.getContext("2d", { willReadFrequently: true }); cx.drawImage(src, 0, 0, c.width, c.height);
    const W = c.width, H = c.height, d = cx.getImageData(0, 0, W, H).data, n = W * H;
    const hist = new Uint32Array(256), L = new Float32Array(n);
    let sr = 0, sg = 0, sb = 0, cnt = 0;
    for (let j = 0; j < n; j++) {
      const r = d[j * 4], g = d[j * 4 + 1], b = d[j * 4 + 2], l = luma(r, g, b); L[j] = l; hist[l | 0]++;
      if (l > 40 && l < 220 && Math.max(r, g, b) - Math.min(r, g, b) < 45) { sr += r; sg += g; sb += b; cnt++; }
    }
    const pct = q => { let s = 0; const t = q * n; for (let v = 0; v < 256; v++) { s += hist[v]; if (s >= t) return v; } return 255; };
    // balance des blancs : seulement sur les tons neutres, et limitée pour rester naturelle
    let wb = [1, 1, 1];
    if (cnt > n * .03) { const m = (sr + sg + sb) / 3; wb = [m / sr, m / sg, m / sb].map(x => Math.min(1.07, Math.max(.93, x))); }
    return { black: pct(.005), white: pct(.995), mid: pct(.5), wb, noise: noiseSigma(src) };
  }
  function noiseSigma(src) {
    // estimation du bruit (méthode d'Immerkær) limitée aux zones unies de l'aperçu
    const W = src.width, H = src.height, d = src.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, W, H).data, L = toY(d, W * H);
    const vals = [], grads = [];
    for (let y = 1; y < H - 1; y += 2) for (let x = 1; x < W - 1; x += 2) {
      const j = y * W + x, a = L[j - W - 1], b = L[j - W], c = L[j - W + 1], dd = L[j - 1], e = L[j], f = L[j + 1], g = L[j + W - 1], h = L[j + W], i = L[j + W + 1];
      vals.push(Math.abs(a - 2 * b + c - 2 * dd + 4 * e - 2 * f + g - 2 * h + i));
      grads.push(Math.hypot(c + 2 * f + i - a - 2 * dd - g, g + 2 * h + i - a - 2 * b - c));
    }
    const lim = [...grads].sort((x, y) => x - y)[Math.floor(grads.length * .4)] || 0;
    let sum = 0, n = 0; for (let k = 0; k < vals.length; k++) if (grads[k] <= lim) { sum += vals[k]; n++; }
    return n ? Math.sqrt(Math.PI / 2) / 6 * sum / n : 0;
  }
  function enhance(d, W, H, e, a, scale) {
    // Réglages volontairement prudents : on corrige, on ne transforme pas.
    // 1. bruit : couleur surtout, luminance à peine (le grain naturel reste)
    const nz = Math.min(1, Math.max(0, (e.noise - .8) / 2.5));
    denoiseYCC(d, W, H, a * (.45 + .35 * nz), a * (.1 + .3 * nz), scale);
    // 2. lumière : même courbe sur R, V, B (comme un logiciel photo), niveaux et tons moyens modérés
    const lo = e.black < 40 ? e.black * .6 * a : 0, hi = e.white > 190 ? 255 - (255 - e.white) * .6 * a : 255;
    const midN = Math.min(.9, Math.max(.05, (e.mid - lo) / Math.max(1, hi - lo)));
    let gam = Math.min(1.2, Math.max(.8, Math.log(.46) / Math.log(midN)));
    gam = 1 + (gam - 1) * .5 * a;
    const lut = new Uint8ClampedArray(256);
    for (let v = 0; v < 256; v++) {
      let x = Math.min(1, Math.max(0, (v - lo) / Math.max(1, hi - lo)));
      x = Math.pow(x, gam); x += (x * x * (3 - 2 * x) - x) * .18 * a; lut[v] = Math.round(x * 255);
    }
    // balance des blancs très légère : l'ambiance (lumière chaude, soirée…) est conservée
    const wf = .35 * a, wr = 1 + (e.wb[0] - 1) * wf, wg = 1 + (e.wb[1] - 1) * wf, wbb = 1 + (e.wb[2] - 1) * wf, vib = .08 * a;
    for (let i = 0; i < d.length; i += 4) {
      let r = lut[clamp(d[i] * wr) | 0], g = lut[clamp(d[i + 1] * wg) | 0], b = lut[clamp(d[i + 2] * wbb) | 0];
      const l = luma(r, g, b), sat = (Math.max(r, g, b) - Math.min(r, g, b)) / 255;
      const skin = r > g && g > b && r > 70 && r - b > 15 && r - b < 130;
      const k = 1 + vib * (1 - sat) * (1 - sat) * (skin ? .2 : 1);
      d[i] = clamp(l + (r - l) * k); d[i + 1] = clamp(l + (g - l) * k); d[i + 2] = clamp(l + (b - l) * k);
    }
    // 3. netteté fine, seuil élevé (pas de bruit accentué, pas de halo), relief à peine perceptible
    usm(d, W, H, .28 * a, Math.max(1, Math.round(scale)), 6 + 2 * e.noise);
    localContrast(d, W, H, .05 * a, Math.max(4, Math.round(22 * scale)));
  }
  function toY(d, n) { const Y = new Float32Array(n); for (let j = 0; j < n; j++) Y[j] = luma(d[j * 4], d[j * 4 + 1], d[j * 4 + 2]); return Y; }
  function denoiseYCC(d, W, H, ac, al, scale) {
    if (ac <= 0 && al <= 0) return;
    const n = W * H, Y = toY(d, n), Cb = new Float32Array(n), Cr = new Float32Array(n);
    for (let j = 0; j < n; j++) { Cb[j] = d[j * 4 + 2] - Y[j]; Cr[j] = d[j * 4] - Y[j]; }
    const rc = Math.max(1, Math.round(2 * scale)), Yb = boxBlur(Y, W, H, rc, 2);
    const Cb2 = boxBlur(Cb, W, H, rc, 2), Cr2 = boxBlur(Cr, W, H, rc, 2);
    const Ys = al > 0 ? boxBlur(Y, W, H, Math.max(1, Math.round(scale)), 2) : null;
    for (let j = 0; j < n; j++) {
      const e = Y[j] - Yb[j], wc = ac * Math.exp(-(e * e) / 288); // pas de bavure de couleur sur les contours
      let cb = Cb[j] + (Cb2[j] - Cb[j]) * wc, cr = Cr[j] + (Cr2[j] - Cr[j]) * wc, y = Y[j];
      if (Ys) { const e2 = Y[j] - Ys[j]; y += (Ys[j] - y) * al * Math.exp(-(e2 * e2) / 128); }
      const r = y + cr, b = y + cb, g = (y - .299 * r - .114 * b) / .587;
      d[j * 4] = clamp(r); d[j * 4 + 1] = clamp(g); d[j * 4 + 2] = clamp(b);
    }
  }
  function usm(d, W, H, amount, radius, thr) {
    // masque flou sur la luminance, avec seuil doux (n'accentue pas le bruit) et limite anti-halo
    const n = W * H, Y = toY(d, n), Yb = boxBlur(Y, W, H, radius, 2);
    for (let j = 0; j < n; j++) {
      let det = Y[j] - Yb[j]; const a = Math.abs(det);
      if (a < thr) det *= a / thr;
      const delta = Math.max(-22, Math.min(22, det * amount * 1.6));
      d[j * 4] = clamp(d[j * 4] + delta); d[j * 4 + 1] = clamp(d[j * 4 + 1] + delta); d[j * 4 + 2] = clamp(d[j * 4 + 2] + delta);
    }
  }
  function localContrast(d, W, H, amount, radius) {
    const n = W * H, Y = toY(d, n), Yb = boxBlur(Y, W, H, radius, 3);
    for (let j = 0; j < n; j++) {
      const l = Y[j] / 255, delta = (Y[j] - Yb[j]) * amount * 4 * l * (1 - l) * 1.5;
      d[j * 4] = clamp(d[j * 4] + delta); d[j * 4 + 1] = clamp(d[j * 4 + 1] + delta); d[j * 4 + 2] = clamp(d[j * 4 + 2] + delta);
    }
  }
  function chan(d, ch, n) { const a = new Float32Array(n); for (let j = 0; j < n; j++) a[j] = d[j * 4 + ch]; return a; }
  function boxBlur(a, W, H, r, passes) {
    // flou « boîte » séparable, répété pour approcher un flou gaussien
    const src = Float32Array.from(a), tmp = new Float32Array(a.length), k = 1 / (2 * r + 1);
    for (let pass = 0; pass < passes; pass++) {
      for (let y = 0; y < H; y++) { const o = y * W; let s = 0;
        for (let x = -r; x <= r; x++) s += src[o + Math.min(W - 1, Math.max(0, x))];
        for (let x = 0; x < W; x++) { tmp[o + x] = s * k; s += src[o + Math.min(W - 1, x + r + 1)] - src[o + Math.max(0, x - r)]; } }
      for (let x = 0; x < W; x++) { let s = 0;
        for (let y = -r; y <= r; y++) s += tmp[Math.min(H - 1, Math.max(0, y)) * W + x];
        for (let y = 0; y < H; y++) { src[y * W + x] = s * k; s += tmp[Math.min(H - 1, y + r + 1) * W + x] - tmp[Math.max(0, y - r) * W + x]; } }
    }
    return src;
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
    else if (S.tab === "heal") { out = geometry(S.prev, { ...S.p, rot: 0, flipH: false, flipV: false }, false); pixels(out, { ...S.p, text: null }, false); }
    else out = process(S.prev, S.p, false);
    canvas.width = out.width; canvas.height = out.height; ctx.drawImage(out, 0, 0);
    q("#st-badge").style.display = S.compare ? "block" : "none";
    if (cropping) placeCrop();
    placeMask();
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
    let tw = Math.round(+q("#st-w").value) || out.width, th = Math.round(+q("#st-h").value) || out.height;
    if (tw * th > 60e6) { const f = Math.sqrt(60e6 / (tw * th)); tw = Math.floor(tw * f); th = Math.floor(th * f); }
    if (tw !== out.width || th !== out.height) out = resample(out, tw, th);
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
    const keep = [q("#st-size").value, q("#st-w").value, q("#st-h").value];
    q("#st-size").value = "1080"; sizeFromPreset();
    const x = exportData();
    [q("#st-size").value, q("#st-w").value, q("#st-h").value] = keep;
    if (window.jarvisAttach) window.jarvisAttach(x.data, x.name, "Que penses-tu de cette photo retouchée ? Propose aussi une légende.");
    close();
  });

  // -------------------------------------------------------- gomme magique --
  function placeMask() {
    if (S.tab !== "heal" || !S.prev || S.compare) { mask.style.display = "none"; return; }
    const r = canvas.getBoundingClientRect(), sr = q("#st-stage").getBoundingClientRect();
    Object.assign(mask.style, { display: "block", left: `${r.left - sr.left}px`, top: `${r.top - sr.top}px`, width: `${r.width}px`, height: `${r.height}px` });
  }
  let painting = null;
  const brushPos = e => { const r = mask.getBoundingClientRect(); return [(e.clientX - r.left) * mask.width / r.width, (e.clientY - r.top) * mask.height / r.height]; };
  function stroke(a, b) {
    const r = mask.getBoundingClientRect();
    mctx.globalCompositeOperation = S.erase ? "destination-out" : "source-over";
    mctx.strokeStyle = mctx.fillStyle = "#ff3d6e"; mctx.lineCap = mctx.lineJoin = "round";
    mctx.lineWidth = +q("#st-brush").value * mask.width / r.width;
    mctx.beginPath(); mctx.moveTo(a[0], a[1]); mctx.lineTo(b[0], b[1]); mctx.stroke();
  }
  mask.addEventListener("pointerdown", e => { e.preventDefault(); mask.setPointerCapture(e.pointerId); painting = brushPos(e); stroke(painting, painting); });
  mask.addEventListener("pointermove", e => { if (!painting) return; const pt = brushPos(e); stroke(painting, pt); painting = pt; });
  ["pointerup", "pointercancel"].forEach(ev => mask.addEventListener(ev, () => { painting = null; }));
  q("#st-brush").oninput = e => q("#v-brush").textContent = e.target.value;
  q("#st-paint").onclick = () => { S.erase = false; q("#st-paint").classList.add("on"); q("#st-erase").classList.remove("on"); };
  q("#st-erase").onclick = () => { S.erase = true; q("#st-erase").classList.add("on"); q("#st-paint").classList.remove("on"); };
  q("#st-mask-clear").onclick = () => mctx.clearRect(0, 0, mask.width, mask.height);
  const healMsg = (t, err) => { const m = q("#st-heal-msg"); m.textContent = t; m.style.color = err ? "var(--err)" : "var(--ok)"; };

  function runWorker(data) {
    return new Promise((resolve, reject) => {
      const w = new Worker("/inpaint.js");
      w.onmessage = e => { w.terminate(); e.data.error ? reject(new Error(e.data.error)) : resolve(e.data.rgb); };
      w.onerror = e => { w.terminate(); reject(new Error(e.message || "erreur du moteur")); };
      w.postMessage(data, [data.rgb.buffer, data.hole.buffer]);
    });
  }
  async function heal(variant = 0) {
    if (!S.full) return;
    const maskCopy = document.createElement("canvas"); maskCopy.width = mask.width; maskCopy.height = mask.height;
    maskCopy.getContext("2d").drawImage(mask, 0, 0);
    const md = mctx.getImageData(0, 0, mask.width, mask.height).data;
    let x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1;
    for (let y = 0; y < mask.height; y++) for (let x = 0; x < mask.width; x++) if (md[(y * mask.width + x) * 4 + 3] > 20) {
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    if (x1 < 0) return healMsg("Peins d'abord sur la zone à effacer.", true);
    const k0 = S.full.width / mask.width, bw = (x1 - x0 + 1) * k0, bh = (y1 - y0 + 1) * k0;
    const ai = S.engine === "ai";
    const margin = Math.max(40 * k0, (ai ? [1.0, 1.6, 0.7] : [1.2, 1.2, 1.2])[variant % 3] * Math.max(bw, bh));
    const rx = Math.max(0, Math.floor(x0 * k0 - margin)), ry = Math.max(0, Math.floor(y0 * k0 - margin));
    const rw = Math.min(S.full.width, Math.ceil((x1 + 1) * k0 + margin)) - rx, rh = Math.min(S.full.height, Math.ceil((y1 + 1) * k0 + margin)) - ry;
    const k = Math.min(1, (ai ? 1024 : 900) / Math.max(rw, rh)), ww = Math.max(8, Math.round(rw * k)), wh = Math.max(8, Math.round(rh * k));
    // image et masque de travail
    const work = document.createElement("canvas"); work.width = ww; work.height = wh;
    const wc = work.getContext("2d", { willReadFrequently: true }); wc.imageSmoothingQuality = "high";
    wc.drawImage(S.full, rx, ry, rw, rh, 0, 0, ww, wh);
    const px = wc.getImageData(0, 0, ww, wh), rgb = new Float32Array(ww * wh * 3);
    for (let i = 0; i < ww * wh; i++) { rgb[i * 3] = px.data[i * 4]; rgb[i * 3 + 1] = px.data[i * 4 + 1]; rgb[i * 3 + 2] = px.data[i * 4 + 2]; }
    const mw = document.createElement("canvas"); mw.width = ww; mw.height = wh;
    const mwc = mw.getContext("2d", { willReadFrequently: true });
    mwc.drawImage(mask, rx / k0, ry / k0, rw / k0, rh / k0, 0, 0, ww, wh);
    const ma = mwc.getImageData(0, 0, ww, wh).data, raw = new Uint8Array(ww * wh), hole = new Uint8Array(ww * wh);
    for (let i = 0; i < ww * wh; i++) raw[i] = ma[i * 4 + 3] > 10 ? 1 : 0;
    for (let y = 0; y < wh; y++) for (let x = 0; x < ww; x++) { // léger débord pour couvrir les contours
      let h = 0; for (let dy = -2; dy <= 2 && !h; dy++) for (let dx = -2; dx <= 2; dx++) {
        const xx = x + dx, yy = y + dy; if (xx >= 0 && yy >= 0 && xx < ww && yy < wh && raw[yy * ww + xx]) { h = 1; break; } }
      hole[y * ww + x] = h; }
    const holeCopy = hole.slice();
    q("#st-busy span").textContent = ai ? "L'IA reconstruit la zone… (5 à 20 s)" : "Reconstruction du fond…";
    q("#st-busy").style.display = "flex"; q("#st-heal").disabled = true;
    const t0 = performance.now();
    try {
      if (ai) {
        // IA LaMa sur le PC : on envoie la zone et son masque, on récupère la zone reconstruite
        const mk = new ImageData(ww, wh);
        for (let i = 0; i < ww * wh; i++) { const v = hole[i] ? 255 : 0; mk.data[i * 4] = mk.data[i * 4 + 1] = mk.data[i * 4 + 2] = v; mk.data[i * 4 + 3] = 255; }
        const mc = document.createElement("canvas"); mc.width = ww; mc.height = wh; mc.getContext("2d").putImageData(mk, 0, 0);
        const r = await (await fetch("/ai_inpaint", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image: work.toDataURL("image/png"), mask: mc.toDataURL("image/png") }) })).json();
        if (r.error) throw new Error(r.error);
        const im = new Image(); im.src = r.image; await im.decode();
        wc.clearRect(0, 0, ww, wh); wc.drawImage(im, 0, 0, ww, wh);
      } else {
        const out = await runWorker({ rgb, hole, W: ww, H: wh, fineR: [6, 4, 5][variant % 3] });
        for (let i = 0; i < ww * wh; i++) { px.data[i * 4] = out[i * 3]; px.data[i * 4 + 1] = out[i * 3 + 1]; px.data[i * 4 + 2] = out[i * 3 + 2]; px.data[i * 4 + 3] = 255; }
        wc.putImageData(px, 0, 0);
      }
      // masque adouci pour fondre la reconstruction dans la photo
      const hm = new ImageData(ww, wh); for (let i = 0; i < ww * wh; i++) if (holeCopy[i]) { hm.data[i * 4 + 3] = 255; }
      const hc = document.createElement("canvas"); hc.width = ww; hc.height = wh; hc.getContext("2d").putImageData(hm, 0, 0);
      const fill = document.createElement("canvas"); fill.width = rw; fill.height = rh;
      const fc = fill.getContext("2d"); fc.imageSmoothingQuality = "high"; fc.drawImage(work, 0, 0, rw, rh);
      const soft = document.createElement("canvas"); soft.width = rw; soft.height = rh;
      const sc = soft.getContext("2d"); sc.filter = `blur(${Math.max(1, 1.5 / k)}px)`; sc.drawImage(hc, 0, 0, rw, rh);
      fc.globalCompositeOperation = "destination-in"; fc.drawImage(soft, 0, 0);
      // sauvegarde pour annuler, puis application
      const snap = document.createElement("canvas"); snap.width = S.full.width; snap.height = S.full.height; snap.getContext("2d").drawImage(S.full, 0, 0);
      S.baseHist.push(snap); if (S.baseHist.length > 6) S.baseHist.shift();
      S.full.getContext("2d").drawImage(fill, rx, ry);
      makePrev(); buildFilterThumbs(); render(); q("#st-heal-undo").disabled = false;
      S.lastHeal = { mask: maskCopy, variant }; q("#st-heal-again").disabled = false;
      healMsg(`Zone effacée en ${((performance.now() - t0) / 1000).toFixed(1)} s. Pas convaincu ? « Autre proposition ». Une trace reste ? Repeins-la.`);
    } catch (err) { healMsg("Échec : " + err.message, true); }
    finally { q("#st-busy").style.display = "none"; q("#st-heal").disabled = S.engine === "ai" && !(aiState && aiState.state === "ready"); }
  }
  q("#st-heal").onclick = () => heal(0);
  q("#st-heal-again").onclick = async () => {
    // annule la dernière gomme et recalcule la même zone avec un autre réglage
    const last = S.lastHeal, snap = S.baseHist.pop(); if (!last || !snap) return;
    S.full = snap; makePrev(); mctx.drawImage(last.mask, 0, 0);
    await heal(last.variant + 1);
  };
  q("#st-heal-undo").onclick = () => {
    const snap = S.baseHist.pop(); if (!snap) return;
    S.full = snap; makePrev(); buildFilterThumbs(); render(); q("#st-heal-undo").disabled = !S.baseHist.length; healMsg("Gomme annulée.");
    S.lastHeal = null; q("#st-heal-again").disabled = true;
  };

  // ------------------------------------------------------------- moteur IA --
  let aiState = null;
  try { S.engine = localStorage.getItem("jarvis-heal-engine") || "classic"; } catch (e) { S.engine = "classic"; }
  function setEngine(e) {
    S.engine = e; try { localStorage.setItem("jarvis-heal-engine", e); } catch (err) {}
    q("#st-eng-classic").classList.toggle("on", e === "classic"); q("#st-eng-ai").classList.toggle("on", e === "ai");
    refreshAI();
  }
  async function refreshAI() {
    const box = q("#st-ai-box");
    if (S.engine !== "ai") { box.hidden = true; q("#st-heal").disabled = false; return; }
    try { aiState = await (await fetch("/ai_status")).json(); } catch (e) { aiState = { state: "error", error: "Jarvis ne répond pas" }; }
    box.hidden = false;
    const ready = aiState.state === "ready";
    q("#st-heal").disabled = !ready;
    if (ready) box.innerHTML = "✦ IA LaMa prête. Idéale quand l'objet cache le bord d'un autre (tasse, meuble, personne…).";
    else if (aiState.state === "installing")
      box.innerHTML = `${esc2(aiState.step)}<div class="st-prog"><span style="width:${aiState.progress || 0}%"></span></div>`;
    else box.innerHTML = (aiState.state === "error" ? `<span style="color:var(--err)">Échec : ${esc2(aiState.error)}</span><br>` : "") +
      "L'IA de retouche s'installe une seule fois (≈ 110 Mo, quelques minutes). Elle fonctionne ensuite sans internet, sur ton PC." +
      '<button class="st-btn primary wide" id="st-ai-install">Installer l\'IA de retouche</button>';
    const btn = q("#st-ai-install");
    if (btn) btn.onclick = async () => { await fetch("/ai_install", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }); refreshAI(); };
    if (aiState.state === "installing" && root.classList.contains("open")) setTimeout(refreshAI, 1000);
  }
  const esc2 = t => String(t || "").replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  q("#st-eng-classic").onclick = () => setEngine("classic");
  q("#st-eng-ai").onclick = () => setEngine("ai");
  setEngine(S.engine);

  // --------------------------------------------------------------- qualité --
  q("#st-enhance").onclick = () => { if (!S.prev) return;
    S.p.enh = analyze(S.prev); S.p.enhance = S.p.enhance > 0 ? S.p.enhance : 40; commit(); sync(); render(); };

  // --------------------------------------------------------- redimensionner --
  function baseSize() {
    if (!S.full) return [0, 0];
    const rot = ((S.p.rot % 360) + 360) % 360, swap = rot === 90 || rot === 270;
    let w = swap ? S.full.height : S.full.width, h = swap ? S.full.width : S.full.height;
    if (S.p.crop) { w = Math.round(w * S.p.crop.w); h = Math.round(h * S.p.crop.h); }
    return [Math.max(1, w), Math.max(1, h)];
  }
  function sizeFromPreset() {
    const v = q("#st-size").value; if (v === "custom") return;
    const [w, h] = baseSize(); let tw = w, th = h;
    if (v === "x2" || v === "x4") { const f = v === "x2" ? 2 : 4; tw = w * f; th = h * f; }
    else if (+v > 1) { const f = +v / Math.max(w, h); tw = Math.round(w * f); th = Math.round(h * f); }
    q("#st-w").value = tw; q("#st-h").value = th;
  }
  q("#st-size").onchange = sizeFromPreset;
  ["#st-w", "#st-h"].forEach(id => q(id).addEventListener("input", e => {
    q("#st-size").value = "custom";
    if (!q("#st-lock").checked) return;
    const [w, h] = baseSize(), v = +e.target.value || 1;
    if (id === "#st-w") q("#st-h").value = Math.max(1, Math.round(v * h / w)); else q("#st-w").value = Math.max(1, Math.round(v * w / h));
  }));
  function resample(src, tw, th) {
    let cur = src;
    // étapes successives (÷2 ou ×2) : bien plus net qu'un seul redimensionnement
    while (cur.width / tw >= 2 || cur.width * 2 <= tw) {
      const f = cur.width > tw ? .5 : 2, t = document.createElement("canvas");
      t.width = Math.round(cur.width * f); t.height = Math.round(cur.height * f);
      const c = t.getContext("2d"); c.imageSmoothingQuality = "high"; c.drawImage(cur, 0, 0, t.width, t.height); cur = t;
    }
    const out = document.createElement("canvas"); out.width = tw; out.height = th;
    const oc = out.getContext("2d", { willReadFrequently: true }); oc.imageSmoothingQuality = "high"; oc.drawImage(cur, 0, 0, tw, th);
    if (tw > src.width * 1.2) { const im = oc.getImageData(0, 0, tw, th); sharpen(im, tw, th, .35); oc.putImageData(im, 0, 0); }
    return out;
  }

  // ------------------------------------------------------------- navigation --
  function setTab(t) {
    S.tab = t;
    root.querySelectorAll(".st-tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === t));
    root.querySelectorAll(".st-pane").forEach(p => p.classList.toggle("on", p.dataset.pane === t));
    if (t !== "crop") { cropEl.style.display = "none"; S.cropBox = null; }
    if (t === "export" && q("#st-size").value !== "custom") sizeFromPreset();
    if (t === "heal") refreshAI();
    render();
  }
  root.querySelector(".st-tabs").addEventListener("click", e => { const b = e.target.closest("button"); if (b) setTab(b.dataset.tab); });
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
  addEventListener("resize", () => { if (S.tab === "crop") placeCrop(); placeMask(); });
  function close() { root.classList.remove("open"); }
  q("#st-close").onclick = close;

  window.openStudio = path => {
    root.classList.add("open"); buttons();
    if (path) loadFrom(`/file?path=${encodeURIComponent(path)}`, path.split(/[\\/]/).pop());
    else if (!S.prev) gallery();
  };
})();
