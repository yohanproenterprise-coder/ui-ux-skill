/* Cinematic 3D scroll scene — Three.js r147 (global THREE). Tout est généré en code : aucun modèle externe. */
(function () {
  'use strict';
  var clamp = function (v, a, b) { return Math.min(b, Math.max(a, v)); };
  var smooth = function (a, b, v) { var t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

  /* ---------- textures dessinées sur canvas ---------- */
  function mkCanvas(w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  function rnd(seed) { var s = seed; return function () { s = (s * 16807) % 2147483647; return s / 2147483647; }; }

  function paintStone(base, vein, strata, seed) {
    var c = mkCanvas(512, 512), g = c.getContext('2d'), r = rnd(seed);
    g.fillStyle = base; g.fillRect(0, 0, 512, 512);
    for (var i = 0; i < 26000; i++) { g.fillStyle = 'rgba(' + (r() > .5 ? '255,255,255' : '0,0,0') + ',' + (r() * .05).toFixed(3) + ')'; g.fillRect(r() * 512, r() * 512, 1 + r() * 2, 1 + r() * 2); }
    for (var k = 0; k < (strata ? 34 : 10); k++) {
      g.strokeStyle = vein; g.globalAlpha = .12 + r() * .25; g.lineWidth = .5 + r() * (strata ? 3 : 1.5);
      g.beginPath(); var y = r() * 512; g.moveTo(0, y);
      for (var x = 0; x <= 512; x += 32) g.lineTo(x, y + (strata ? 0 : (r() - .5) * 90) + (r() - .5) * 6);
      g.stroke();
    }
    g.globalAlpha = 1; return c;
  }
  function paintWood() {
    var c = mkCanvas(512, 512), g = c.getContext('2d'), r = rnd(7);
    g.fillStyle = '#4a2c19'; g.fillRect(0, 0, 512, 512);
    for (var i = 0; i < 420; i++) { g.strokeStyle = 'rgba(' + (r() > .5 ? '20,9,3' : '150,90,50') + ',' + (.05 + r() * .18).toFixed(2) + ')'; g.lineWidth = .6 + r() * 2.2; g.beginPath(); var x = r() * 512; g.moveTo(x, 0); g.bezierCurveTo(x + (r() - .5) * 40, 170, x + (r() - .5) * 40, 340, x + (r() - .5) * 30, 512); g.stroke(); }
    return c;
  }
  function radial(inner, outer) {
    var c = mkCanvas(256, 256), g = c.getContext('2d'), gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, inner); gr.addColorStop(.35, 'rgba(255,170,90,.18)'); gr.addColorStop(1, outer);
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256); return c;
  }
  var FINISHES = {
    travertin: function () { return { map: paintStone('#d8c7a8', '#9d8660', true, 11), rough: .78, metal: 0, bump: .9 }; },
    marbre: function () { return { map: paintStone('#15151a', '#e9e4da', false, 23), rough: .18, metal: 0, bump: .15 }; },
    noyer: function () { return { map: paintWood(), rough: .5, metal: 0, bump: .5 }; },
    ceramique: function () { return { map: paintStone('#efeae1', '#d6cfc2', false, 5), rough: .22, metal: 0, bump: .08 }; }
  };

  /* ---------- couleurs : noms de variantes Shopify -> teinte ---------- */
  var COLORS = { noir: '#161518', black: '#161518', blanc: '#f1ece4', white: '#f1ece4', or: '#d4a24a', gold: '#d4a24a', doré: '#d4a24a', argent: '#c9ccd1', silver: '#c9ccd1', cuivre: '#b8693d', bleu: '#2f5d9e', orange: '#e0702a', vert: '#4f6b57', gris: '#8b8c8f', ambre: '#d98a2b', transparent: '#e8f1f2', bois: '#7a4a2a', naturel: '#b88a5a', rouge: '#a4302a', rose: '#d9a0a0', beige: '#d8c7a8', terracotta: '#c96a3c' };
  function colorFromName(s) { s = (s || '').toLowerCase(); for (var k in COLORS) if (s.indexOf(k) > -1) return COLORS[k]; return null; }

  /* ---------- familles de modèles procéduraux (1 unité = 10 cm) ---------- */
  function brassMat(hex) { return new THREE.MeshStandardMaterial({ color: hex || 0xd9a35a, metalness: 1, roughness: .22 }); }
  function glowMat(col) { return new THREE.MeshStandardMaterial({ color: col, roughness: .55, emissive: 0xffa84d, emissiveIntensity: 0, side: THREE.DoubleSide }); }
  function mesh(geo, mat, x, y, z, shadow) { var m = new THREE.Mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); if (shadow !== false) m.castShadow = true; return m; }
  var V = function (x, y, z) { return new THREE.Vector3(x, y, z); };

  var BUILDERS = {
    table: function (o) {
      var g = new THREE.Group(), parts = [], glow = [];
      var baseMat = o.baseMat;
      var prof = [V2(.001, 0), V2(1.1, 0), V2(1.14, .06), V2(1.08, .5), V2(.95, .66), V2(.22, .72), V2(.001, .72)];
      var base = mesh(new THREE.LatheGeometry(prof, 96), baseMat); base.receiveShadow = true; g.add(base);
      var brass = brassMat(o.metal);
      var stem = new THREE.Group(); stem.add(mesh(new THREE.CylinderGeometry(.075, .075, 1.55, 32), brass, 0, 1.495, 0)); stem.add(mesh(new THREE.CylinderGeometry(.16, .2, .26, 32), brass, 0, 2.38, 0)); g.add(stem); parts.push({ o: stem, ex: V(0, .9, 0) });
      var sp = []; for (var j = 0; j <= 28; j++) { var u = j / 28; sp.push(V2(.42 + Math.pow(u, 1.35) * .95, 2.55 + u * 1.05)); }
      var sm = glowMat(o.color); var shade = new THREE.Group(); shade.add(mesh(new THREE.LatheGeometry(sp, 96), sm)); shade.add(mesh(new THREE.TorusGeometry(1.37, .018, 12, 96), brass, 0, 3.6, 0)).rotation.x = Math.PI / 2; g.add(shade); parts.push({ o: shade, ex: V(0, 2.1, 0) }); glow.push(sm);
      return { group: g, parts: parts, glow: glow, bulbs: [V(0, 2.95, 0)], bounds: { c: V(0, 1.9, 0), r: 2.6 }, hang: 0 };
    },
    pendant: function (o) {
      var g = new THREE.Group(), parts = [], glow = [], H = 7;
      var brass = brassMat(o.metal);
      var cable = new THREE.Group(); cable.add(mesh(new THREE.CylinderGeometry(.015, .015, H - 3.9, 8), new THREE.MeshStandardMaterial({ color: 0x111111 }), 0, (H + 3.9) / 2, 0)); cable.add(mesh(new THREE.CylinderGeometry(.18, .18, .12, 24), brass, 0, H - .06, 0)); g.add(cable); parts.push({ o: cable, ex: V(0, 1.2, 0) });
      var gm = glowMat(o.color); gm.transparent = false; var shape = o.shape || 'ball';
      var geo = shape === 'dome' ? new THREE.SphereGeometry(1.5, 64, 24, 0, Math.PI * 2, 0, Math.PI / 2) : new THREE.SphereGeometry(1.15, 64, 48);
      var body = mesh(geo, gm, 0, shape === 'dome' ? 3 : 3, 0); if (shape === 'dome') { body.scale.y = .8; } g.add(body); parts.push({ o: body, ex: V(0, -1.1, 0) }); glow.push(gm);
      var cap = mesh(new THREE.CylinderGeometry(.35, .35, .22, 32), brass, 0, shape === 'dome' ? 4.2 : 4.1, 0); g.add(cap); parts.push({ o: cap, ex: V(0, .6, 0) });
      return { group: g, parts: parts, glow: glow, bulbs: [V(0, 3, 0)], bounds: { c: V(0, 3.8, 0), r: 3.2 }, ceiling: H };
    },
    wall: function (o) {
      var g = new THREE.Group(), parts = [], glow = [];
      var brass = brassMat(o.metal), shape = o.shape || 'globe';
      var plate = mesh(new THREE.CylinderGeometry(.55, .55, .12, 48), brass, 0, 3, -1.1); plate.rotation.x = Math.PI / 2; g.add(plate); parts.push({ o: plate, ex: V(0, 0, -.7) });
      var gm = glowMat(o.color);
      var body = shape === 'bar' ? mesh(new THREE.BoxGeometry(o.len || 6, .28, .34), gm, 0, 3, -.8) : mesh(new THREE.SphereGeometry(.9, 48, 32), gm, 0, 3, -.15);
      g.add(body); parts.push({ o: body, ex: V(0, 0, .9) }); glow.push(gm);
      return { group: g, parts: parts, glow: glow, bulbs: [V(0, 3, shape === 'bar' ? -.6 : 0)], bounds: { c: V(0, 3, 0), r: shape === 'bar' ? 3.6 : 2 }, wall: true };
    },
    chandelier: function (o) {
      var g = new THREE.Group(), parts = [], glow = [], H = 7, n = clamp(o.heads || 6, 3, 14);
      var brass = brassMat(o.metal || 0xb8693d), gm = glowMat(o.color);
      var core = new THREE.Group(); core.add(mesh(new THREE.CylinderGeometry(.04, .04, H - 3.5, 12), brass, 0, (H + 3.5) / 2, 0)); core.add(mesh(new THREE.SphereGeometry(.28, 24, 16), brass, 0, 3.5, 0)); g.add(core); parts.push({ o: core, ex: V(0, 1, 0) });
      var bulbs = [], arms = new THREE.Group(); g.add(arms);
      for (var i = 0; i < n; i++) {
        var a = i / n * Math.PI * 2, rr = 1.7, y = 3.5 - (i % 2) * .55, r2 = rr * (1 - (i % 2) * .25);
        var curve = new THREE.QuadraticBezierCurve3(V(0, 3.5, 0), V(Math.cos(a) * r2 * .6, 3.5 + .5, Math.sin(a) * r2 * .6), V(Math.cos(a) * r2, y + .1, Math.sin(a) * r2));
        arms.add(mesh(new THREE.TubeGeometry(curve, 24, .03, 8), brass));
        var head = new THREE.Group(); head.position.set(Math.cos(a) * r2, y, Math.sin(a) * r2);
        head.add(mesh(new THREE.SphereGeometry(.24, 24, 16), gm, 0, -.05, 0)); head.add(mesh(new THREE.CylinderGeometry(.14, .2, .2, 20, 1, true), brass, 0, .18, 0)); arms.add(head);
        bulbs.push(V(Math.cos(a) * r2, y - .05, Math.sin(a) * r2));
      }
      parts.push({ o: arms, ex: V(0, -1.2, 0) }); glow.push(gm);
      return { group: g, parts: parts, glow: glow, bulbs: bulbs, bounds: { c: V(0, 3.5, 0), r: 3.4 }, ceiling: H };
    },
    flush: function (o) {
      var g = new THREE.Group(), parts = [], glow = [], H = 6, n = clamp(o.heads || 6, 3, 12), brass = brassMat(o.metal || 0xcfd2d6), gm = glowMat(o.color || 0xdfe6ea);
      var disk = mesh(new THREE.CylinderGeometry(1.9, 1.9, .2, 64), brass, 0, H - .1, 0); g.add(disk); parts.push({ o: disk, ex: V(0, .8, 0) });
      var drops = new THREE.Group(), bulbs = []; g.add(drops);
      for (var i = 0; i < n; i++) { var a = i / n * Math.PI * 2, rr = i % 2 ? 1.25 : 1.6, y = H - .9 - (i % 2) * .5; var x = Math.cos(a) * rr, z = Math.sin(a) * rr; drops.add(mesh(new THREE.CylinderGeometry(.015, .015, H - y - .3, 6), brass, x, (H + y) / 2 - .05, z)); var d = mesh(new THREE.SphereGeometry(.34, 32, 24), gm, x, y, z); d.scale.y = 1.25; drops.add(d); bulbs.push(V(x, y, z)); }
      parts.push({ o: drops, ex: V(0, -1.3, 0) }); glow.push(gm);
      return { group: g, parts: parts, glow: glow, bulbs: bulbs, bounds: { c: V(0, 4.8, 0), r: 3 }, ceiling: H };
    }
  };
  function V2(x, y) { return new THREE.Vector2(x, y); }

  /* ---------- scène ---------- */
  function init(root, opts) {
    opts = opts || {};
    var canvas = root.querySelector('.c3d__canvas');
    var chapters = [].slice.call(root.querySelectorAll('.c3d__chapter'));
    var dots = [].slice.call(root.querySelectorAll('.c3d__dot'));
    var hint = root.querySelector('.c3d__hint');
    var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    var accent = new THREE.Color(root.dataset.accent || '#ffb46b');
    var state = { model: root.dataset.model || 'table', color: root.dataset.color || '#f0e4d0', finish: root.dataset.finish || 'travertin', metal: root.dataset.metal || '#d9a35a', shape: root.dataset.shape || '', heads: +root.dataset.heads || 6, len: +root.dataset.len || 6 };

    [].forEach.call(root.querySelectorAll('.c3d__title'), function (t) {
      var words = t.textContent.trim().split(/\s+/); t.setAttribute('aria-label', t.textContent.trim()); t.innerHTML = '';
      words.forEach(function (w, i) { var s = document.createElement('span'); s.className = 'w'; s.setAttribute('aria-hidden', 'true'); s.style.transitionDelay = (i * 90) + 'ms'; s.textContent = w + ' '; t.appendChild(s); });
    });

    var renderer;
    try { renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false, powerPreference: 'high-performance' }); }
    catch (e) { root.classList.add('c3d--nogl'); chapters.forEach(function (c) { c.classList.add('is-active'); }); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputEncoding = THREE.sRGBEncoding; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    var scene = new THREE.Scene(); scene.background = new THREE.Color(0x07060a); scene.fog = new THREE.FogExp2(0x07060a, .04);
    var camera = new THREE.PerspectiveCamera(38, 1, .1, 80);
    (function () {
      var env = new THREE.Scene(); env.background = new THREE.Color(0x050407);
      function panel(w, h, col, i, x, y, z) { var m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(col).multiplyScalar(i), side: THREE.DoubleSide })); m.position.set(x, y, z); m.lookAt(0, 0, 0); env.add(m); }
      panel(8, 5, '#ffffff', 6, -6, 5, 4); panel(4, 8, '#9fb6ff', 3, 7, 3, -3); panel(10, 2, '#ffb46b', 4, 0, 1, -8); panel(6, 6, '#ffffff', 1.5, 0, 9, 0);
      var pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(env, .04).texture; pm.dispose();
    })();

    var floor = new THREE.Mesh(new THREE.CircleGeometry(30, 64), new THREE.MeshStandardMaterial({ color: 0x0d0b10, roughness: .32, metalness: .2 }));
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
    var wall = new THREE.Mesh(new THREE.PlaneGeometry(40, 20), new THREE.MeshStandardMaterial({ color: 0x1a1714, roughness: .9 })); wall.position.set(0, 8, -1.25); wall.receiveShadow = true; scene.add(wall);
    var pool = new THREE.Mesh(new THREE.PlaneGeometry(9, 9), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(radial('rgba(255,200,130,.9)', 'rgba(0,0,0,0)')), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0 }));
    pool.rotation.x = -Math.PI / 2; pool.position.y = .01; scene.add(pool);
    var haloTex = new THREE.CanvasTexture(radial('rgba(255,225,170,1)', 'rgba(0,0,0,0)'));
    var lightPt = new THREE.PointLight(0xffb46b, 0, 16, 1.5); scene.add(lightPt);
    var spot = new THREE.SpotLight(0xffd9a8, 0, 22, .7, .8, 1.2); spot.castShadow = true; spot.shadow.mapSize.set(1024, 1024); spot.shadow.bias = -.0004; scene.add(spot, spot.target);
    var rimL = new THREE.DirectionalLight(0x8fa8ff, .5); rimL.position.set(-6, 4, -5); scene.add(rimL); scene.add(new THREE.HemisphereLight(0x1b1a30, 0x050407, .35));

    var N = 700, pPos = new Float32Array(N * 3), pSeed = [];
    for (var n = 0; n < N; n++) { pPos[n * 3] = (Math.random() - .5) * 22; pPos[n * 3 + 1] = Math.random() * 9; pPos[n * 3 + 2] = (Math.random() - .5) * 22; pSeed.push(Math.random() * 6.28); }
    var pGeo = new THREE.BufferGeometry(); pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    var dust = new THREE.Points(pGeo, new THREE.PointsMaterial({ size: .05, map: haloTex, color: 0xffd9a8, transparent: true, opacity: .75, blending: THREE.AdditiveBlending, depthWrite: false }));
    scene.add(dust);

    /* modèle courant */
    var baseMat = new THREE.MeshStandardMaterial({ roughness: .8 }), curFinish = null, model = null, halos = [], camPath, tgtPath, ceil = null;
    function applyFinish(name) {
      var f = (FINISHES[name] || FINISHES.travertin)(); if (curFinish && baseMat.map) baseMat.map.dispose();
      var t = new THREE.CanvasTexture(f.map); t.encoding = THREE.sRGBEncoding; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4;
      baseMat.map = t; baseMat.bumpMap = t; baseMat.bumpScale = f.bump * .12; baseMat.roughness = f.rough; baseMat.needsUpdate = true; curFinish = name;
    }
    function build() {
      if (model) { scene.remove(model.group); halos.forEach(function (h) { scene.remove(h); }); halos = []; if (ceil) scene.remove(ceil); ceil = null; }
      applyFinish(state.finish);
      model = BUILDERS[state.model]({ color: state.color, metal: new THREE.Color(state.metal), shape: state.shape, heads: state.heads, len: state.len, baseMat: baseMat });
      model.parts.forEach(function (p) { p.base = p.o.position.clone(); });
      model.group.traverse(function (m) { if (m.isMesh) m.castShadow = true; });
      scene.add(model.group);
      model.bulbs.forEach(function (b) { var h = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTex, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, opacity: 0 })); h.userData.base = b; scene.add(h); halos.push(h); });
      wall.visible = !!model.wall;
      if (model.ceiling) { ceil = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({ color: 0x0d0b10, roughness: .9 })); ceil.rotation.x = Math.PI / 2; ceil.position.y = model.ceiling; scene.add(ceil); }
      var c = model.bounds.c, R = model.bounds.r;
      camPath = new THREE.CatmullRomCurve3([V(c.x, c.y + R * .2, c.z + R * 4.6), V(c.x + R * .5, c.y + R * .3, c.z + R * 2.5), V(c.x + R * 1.5, c.y + R * .6, c.z + R * 2.7), V(c.x - R * 1.4, c.y + R * .4, c.z + R * 2.6)], false, 'catmullrom', .5);
      tgtPath = new THREE.CatmullRomCurve3([c.clone(), c.clone(), c.clone().add(V(0, R * .05, 0)), c.clone()], false, 'catmullrom', .5);
    }
    build();
    root.addEventListener('c3d:options', function (e) { var d = e.detail || {}, rebuild = false; for (var k in d) { if (d[k] !== state[k]) { state[k] = d[k]; rebuild = true; } } if (rebuild) build(); });
    root.__c3d = { set: function (d) { root.dispatchEvent(new CustomEvent('c3d:options', { detail: d })); }, state: state, set progress(v) { target = v; prog = v; } };

    var target = 0, prog = 0, rotY = 0, rotTarget = 0, drag = false, lastX = 0, mx = 0, my = 0;
    function onScroll() { var r = root.getBoundingClientRect(), span = Math.max(1, r.height - innerHeight); target = reduced ? .3 : clamp(-r.top / span, 0, 1); }
    window.addEventListener('scroll', onScroll, { passive: true }); window.addEventListener('resize', onScroll);
    canvas.addEventListener('pointerdown', function (e) { drag = true; lastX = e.clientX; });
    window.addEventListener('pointerup', function () { drag = false; });
    window.addEventListener('pointermove', function (e) { if (drag) { rotTarget += (e.clientX - lastX) * .01; lastX = e.clientX; } mx = (e.clientX / innerWidth - .5); my = (e.clientY / innerHeight - .5); });
    function press(sel, b) { [].forEach.call(root.querySelectorAll(sel), function (o) { o.setAttribute('aria-pressed', o === b); }); }
    [].forEach.call(root.querySelectorAll('[data-finish]'), function (b) { b.addEventListener('click', function () { press('[data-finish]', b); root.__c3d.set({ finish: b.dataset.finish }); }); });
    [].forEach.call(root.querySelectorAll('[data-shade]'), function (b) { b.addEventListener('click', function () { press('[data-shade]', b); root.__c3d.set({ color: b.dataset.shade }); }); });
    /* variantes Shopify : une pastille de couleur choisit aussi la variante et le prix */
    var vjson = root.querySelector('[data-c3d-variants]'), variants = vjson ? JSON.parse(vjson.textContent) : [];
    [].forEach.call(root.querySelectorAll('[data-option-value]'), function (b) {
      var hex = colorFromName(b.dataset.optionValue); if (hex) b.style.background = hex;
      b.addEventListener('click', function () {
        press('[data-option-value][data-option-index="' + b.dataset.optionIndex + '"]', b);
        var sel = {}; [].forEach.call(root.querySelectorAll('[data-option-value][aria-pressed=true]'), function (o) { sel[o.dataset.optionIndex] = o.dataset.optionValue; });
        var v = variants.filter(function (v) { return v.options.every(function (val, i) { return !sel[i] || sel[i] === val; }); })[0];
        var idIn = root.querySelector('input[name=id]'); if (v && idIn) idIn.value = v.id;
        var pr = root.querySelector('[data-c3d-price]'); if (v && pr) pr.textContent = v.price_formatted;
        if (hex) root.__c3d.set({ color: hex });
        var m = (b.dataset.optionValue.match(/(\d+)\s*(t[eê]tes?|lumi|led|heads?)/i) || [])[1]; if (m) root.__c3d.set({ heads: +m });
      });
    });

    function resize() { var w = canvas.clientWidth || root.clientWidth, h = canvas.clientHeight || innerHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.fov = w / h < .8 ? 54 : 38; camera.updateProjectionMatrix(); }
    window.addEventListener('resize', resize); resize(); onScroll(); if (reduced) prog = target;

    var visible = true, t0 = performance.now(), last = t0, activeIdx = -1, tmp = new THREE.Vector3();
    if ('IntersectionObserver' in window) new IntersectionObserver(function (e) { visible = e[0].isIntersecting; }).observe(root);

    var film = root.dataset.film === '1';
    function frame(now) {
      requestAnimationFrame(frame); if (!visible || film) return;
      var dt = Math.min(.05, (now - last) / 1000); last = now; var t = (now - t0) / 1000;
      prog += (target - prog) * (reduced ? 1 : 1 - Math.pow(.0009, dt)); rotY += (rotTarget - rotY) * (1 - Math.pow(.001, dt));
      draw(t, dt);
    }
    /* mode « film » : rendu image par image, déterministe (pour produire une vidéo) */
    root.__c3d.film = function (t, p, d) { if (d) { for (var k in d) state[k] = d[k]; build(); } prog = target = p; draw(t, 1 / 24); };
    function draw(t, dt) {
      var glow = smooth(.07, .26, prog) * (.94 + Math.sin(t * 7.3) * .02 + Math.sin(t * 2.1) * .02);
      var ex = smooth(.46, .6, prog) * (1 - smooth(.7, .82, prog));
      var c = model.bounds.c, R = model.bounds.r;

      model.group.rotation.y = (reduced ? 0 : t * .12 + prog * 1.2) * (model.wall ? 0 : 1) + rotY;
      if (model.wall) model.group.rotation.y = Math.max(-.6, Math.min(.6, rotY * .3)) + Math.sin(t * .3) * .05;
      model.parts.forEach(function (p) { p.o.position.copy(p.base).addScaledVector(p.ex, ex); });
      var sc = model.group.position; sc.y = (model.ceiling ? 0 : Math.sin(t * .8) * .03);

      model.glow.forEach(function (m) { m.emissiveIntensity = glow * .75; m.emissive.copy(accent).lerp(m.color, .5); });
      var lc = c.clone(); lc.y += (model.ceiling ? -.4 : .3); lc.add(V(0, ex * (model.parts[model.parts.length - 1].ex.y), 0)); if (model.wall) lc.z += 1.2;
      lightPt.position.copy(lc); lightPt.intensity = glow * 9 * (.6 + .4 * Math.min(1, R / 3)) * (model.wall ? .22 : 1); lightPt.color.copy(accent);
      spot.position.set(lc.x, lc.y + .2, lc.z); spot.target.position.set(lc.x, model.wall ? lc.y : 0, model.wall ? -1.25 : lc.z); spot.intensity = glow * 26 * (model.wall ? .3 : 1);
      halos.forEach(function (h) { tmp.copy(h.userData.base); model.group.localToWorld(tmp); h.position.copy(tmp); h.material.opacity = glow * .95; h.scale.setScalar(((model.bulbs.length > 4 ? 1.4 : 2.4) + glow * (model.bulbs.length > 4 ? 1.6 : 3)) * (model.wall ? .55 : 1)); });
      pool.visible = !model.wall; pool.material.opacity = glow * .5; pool.scale.setScalar(.9 + glow * .5); pool.position.x = lc.x;
      renderer.toneMappingExposure = .9 + glow * .25;

      var cp = camPath.getPoint(clamp(prog, 0, 1)), tp = tgtPath.getPoint(clamp(prog, 0, 1));
      camera.position.set(cp.x + mx * .6, cp.y - my * .4, cp.z); camera.lookAt(tp.x, tp.y, tp.z);

      var arr = pGeo.attributes.position.array; for (var i = 0; i < N; i++) { arr[i * 3 + 1] += dt * (.12 + Math.sin(pSeed[i]) * .05); arr[i * 3] += Math.sin(t * .3 + pSeed[i]) * dt * .06; if (arr[i * 3 + 1] > 9) arr[i * 3 + 1] = 0; } pGeo.attributes.position.needsUpdate = true;
      dust.material.opacity = .35 + glow * .5;

      var idx = clamp(Math.floor(prog * chapters.length * .9999), 0, chapters.length - 1);
      if (!reduced && idx !== activeIdx) { activeIdx = idx; chapters.forEach(function (c, i) { c.classList.toggle('is-active', i === idx); }); dots.forEach(function (d, i) { d.classList.toggle('is-active', i === idx); }); if (hint) hint.style.opacity = idx === 0 ? 1 : 0; }
      renderer.render(scene, camera);
    }
    requestAnimationFrame(frame);
  }

  function boot() { [].forEach.call(document.querySelectorAll('.c3d'), function (el) { init(el); }); }
  window.Cinematic3D = { colorFromName: colorFromName, models: Object.keys(BUILDERS) };
  if (document.readyState !== 'loading') boot(); else document.addEventListener('DOMContentLoaded', boot);
})();
