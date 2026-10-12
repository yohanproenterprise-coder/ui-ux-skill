/* Galerie Lumineuse — atelier 3D : 4 formes de luminaires, rotation au doigt, teinte 2200–4000 K, allumé/éteint. */
(function () {
  'use strict';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var clamp = function (v, a, b) { return Math.max(a, Math.min(b, v)); }, sm = function (t) { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };
  var threeP;
  function loadThree() {
    if (window.THREE) return Promise.resolve();
    if (threeP) return threeP;
    threeP = new Promise(function (res, rej) { var s = document.createElement('script'); s.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
    return threeP;
  }
  function kelvin(k) {
    var t = k / 100, r, g, b;
    r = t <= 66 ? 255 : 329.698727446 * Math.pow(t - 60, -.1332047592);
    g = t <= 66 ? 99.4708025861 * Math.log(t) - 161.1195681661 : 288.1221695283 * Math.pow(t - 60, -.0755148492);
    b = t >= 66 ? 255 : (t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307);
    var c = function (v) { return clamp(Math.round(v), 0, 255); };
    return { r: c(r), g: c(g), b: c(b) };
  }
  function kcol(k) { var c = kelvin(k); return new THREE.Color(c.r / 255, c.g / 255, c.b / 255); }
  function marbleTex(seed) {
    var c = document.createElement('canvas'); c.width = c.height = 512; var x = c.getContext('2d'), rs = seed * 9301 + 49297;
    function R() { rs = (rs * 9301 + 49297) % 233280; return rs / 233280; }
    x.fillStyle = '#efe6d7'; x.fillRect(0, 0, 512, 512);
    for (var i = 0; i < 7; i++) { var g = x.createRadialGradient(R() * 512, R() * 512, 10, R() * 512, R() * 512, 260); g.addColorStop(0, 'rgba(255,225,170,.45)'); g.addColorStop(1, 'rgba(255,225,170,0)'); x.fillStyle = g; x.fillRect(0, 0, 512, 512); }
    try { x.filter = 'blur(1.2px)'; } catch (e) {}
    for (var v = 0; v < 26; v++) { x.beginPath(); var px = R() * 512, py = R() * 512, a = R() * 6.28; x.moveTo(px, py); for (var s = 0; s < 40; s++) { a += (R() - .5) * .9; px += Math.cos(a) * 14; py += Math.sin(a) * 14; x.lineTo(px, py); } x.strokeStyle = 'rgba(' + (110 + R() * 40 | 0) + ',' + (70 + R() * 30 | 0) + ',' + (30 + R() * 20 | 0) + ',' + (.25 + R() * .45) + ')'; x.lineWidth = .6 + R() * 2.6; x.stroke(); }
    var t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
  }
  function glowTex() { var c = document.createElement('canvas'); c.width = c.height = 256; var x = c.getContext('2d'), g = x.createRadialGradient(128, 128, 0, 128, 128, 128); g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(.25, 'rgba(255,255,255,.35)'); g.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = g; x.fillRect(0, 0, 256, 256); return new THREE.CanvasTexture(c); }

  function build(root) {
    var cv = root.querySelector('canvas');
    var r = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true, powerPreference: 'high-performance' });
    r.setPixelRatio(Math.min(devicePixelRatio, 2)); r.outputEncoding = THREE.sRGBEncoding; r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = .9;
    var scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(34, 1, .1, 60); cam.position.set(0, .2, 12.6);
    scene.add(new THREE.AmbientLight(0xffe8d0, .12)); var key = new THREE.DirectionalLight(0xffeedd, .35); key.position.set(3, 4, 6); scene.add(key);
    var pl = new THREE.PointLight(0xffb060, 0, 22, 2); scene.add(pl);
    var rootG = new THREE.Group(); scene.add(rootG);
    var GT = glowTex(), MT = marbleTex(3);
    var floor = new THREE.Mesh(new THREE.CircleGeometry(4.2, 64), new THREE.MeshBasicMaterial({ color: 0xffb060, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, map: GT })); floor.rotation.x = -Math.PI / 2; floor.position.y = -2.7; scene.add(floor);
    var COPPER = new THREE.MeshStandardMaterial({ color: 0xc57a3e, metalness: .85, roughness: .28 }), CORD = new THREE.MeshStandardMaterial({ color: 0x2a1a10, roughness: .8 });
    var emis = [], bulbs = [];
    function eMat(base, extra) { var m = new THREE.MeshStandardMaterial(Object.assign({ color: base, emissive: new THREE.Color(1, .62, .25), emissiveIntensity: 0, roughness: .3 }, extra || {})); emis.push(m); return m; }
    function cordTo(g, x, y0, y1) { var c = new THREE.Mesh(new THREE.CylinderGeometry(.016, .016, Math.abs(y1 - y0), 6), CORD); c.position.set(x, (y0 + y1) / 2, 0); g.add(c); }
    var B = {
      cylinder: function () { var g = new THREE.Group(), m = new THREE.MeshStandardMaterial({ map: MT, emissiveMap: MT, emissive: new THREE.Color(1, .62, .25), emissiveIntensity: 0, roughness: .42 }); emis.push(m);
        g.add(new THREE.Mesh(new THREE.CylinderGeometry(.6, .6, 3, 56, 1, true), m));
        var bot = new THREE.Mesh(new THREE.CircleGeometry(.56, 40), new THREE.MeshBasicMaterial({ color: 0xffd9a0, transparent: true })); bot.rotation.x = Math.PI / 2; bot.position.y = -1.5; g.add(bot); bulbs.push(bot);
        var rim = new THREE.Mesh(new THREE.TorusGeometry(.6, .025, 8, 56), COPPER); rim.rotation.x = Math.PI / 2; rim.position.y = -1.5; g.add(rim);
        var cap = new THREE.Mesh(new THREE.CylinderGeometry(.16, .2, .3, 24), COPPER); cap.position.y = 1.65; g.add(cap); cordTo(g, 0, 1.8, 8); g.position.y = -.1; return g; },
      bar: function () { var g = new THREE.Group(), bar = new THREE.Mesh(new THREE.BoxGeometry(4, .08, .14), COPPER); bar.position.y = 1.2; g.add(bar);
        for (var i = 0; i < 13; i++) { var x = -1.8 + i * .3, side = i % 2 ? 1 : -1, rod = new THREE.Mesh(new THREE.CylinderGeometry(.05, .05, 1.5, 14), eMat(0xf4efe4, { roughness: .2 })); rod.position.set(x, .45, side * .08); rod.rotation.x = side * .16; g.add(rod); }
        cordTo(g, -1.4, 1.25, 8); cordTo(g, 1.4, 1.25, 8); g.position.y = -.2; return g; },
      globes: function () { var g = new THREE.Group(); [[-1.15, -.6, .62], [0, .5, .52], [1.15, -.2, .46]].forEach(function (s) { var sp = new THREE.Mesh(new THREE.SphereGeometry(s[2], 48, 32), eMat(0xf1e9dc, { roughness: .18 })); sp.position.set(s[0], s[1], 0); g.add(sp); var cap = new THREE.Mesh(new THREE.CylinderGeometry(.08, .1, .18, 16), COPPER); cap.position.set(s[0], s[1] + s[2] + .09, 0); g.add(cap); cordTo(g, s[0], s[1] + s[2] + .18, 8); }); g.position.y = -.4; return g; },
      ring: function () { var g = new THREE.Group(), ring = new THREE.Mesh(new THREE.TorusGeometry(1.5, .045, 12, 80), COPPER); ring.rotation.x = Math.PI / 2; g.add(ring);
        for (var i = 0; i < 9; i++) { var a = i / 9 * 6.2832, b = new THREE.Mesh(new THREE.SphereGeometry(.17, 24, 16), eMat(0xfff0d6, { roughness: .15 })); b.position.set(Math.cos(a) * 1.5, .2, Math.sin(a) * 1.5); g.add(b); }
        [0, 2.094, 4.189].forEach(function (a) { var A = new THREE.Vector3(Math.cos(a) * 1.5, 0, Math.sin(a) * 1.5), Bp = new THREE.Vector3(0, 3.1, 0), d = Bp.clone().sub(A), c = new THREE.Mesh(new THREE.CylinderGeometry(.012, .012, d.length(), 6), CORD); c.position.copy(A).add(Bp).multiplyScalar(.5); c.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize()); g.add(c); });
        cordTo(g, 0, 3.1, 8); g.rotation.x = .28; g.position.y = -.5; return g; }
    };
    var cur = null, swap = 1, target = 1, lev = 0, tk = 3000, spin = .003, vel = 0, drag = false, lx = 0, vis = true;
    function setModel(k) { if (cur) { rootG.remove(cur); cur.traverse(function (o) { if (o.geometry) o.geometry.dispose(); }); } emis.length = 0; bulbs.length = 0; cur = (B[k] || B.cylinder)(); rootG.add(cur); swap = 0; }
    var btns = [].slice.call(root.querySelectorAll('.at3-mdl')), nameEl = root.querySelector('[data-at-name]'), priceEl = root.querySelector('[data-at-price]'), linkEl = root.querySelector('[data-at-link]');
    function info(b) { nameEl.textContent = b.dataset.name; priceEl.textContent = b.dataset.price || ''; if (b.dataset.url) { linkEl.href = b.dataset.url; linkEl.hidden = false; } else linkEl.hidden = true; }
    btns.forEach(function (b) { b.addEventListener('click', function () { btns.forEach(function (x) { x.classList.remove('on'); x.setAttribute('aria-selected', 'false'); }); b.classList.add('on'); b.setAttribute('aria-selected', 'true'); info(b); setModel(b.dataset.model); vel = .05; }); });
    setModel(btns[0] ? btns[0].dataset.model : 'cylinder'); if (btns[0]) info(btns[0]);
    var sw = root.querySelector('[data-at-sw]'), kel = root.querySelector('[data-at-k]'), ko = root.querySelector('[data-at-ko]');
    sw.addEventListener('click', function () { var on = sw.getAttribute('aria-checked') !== 'true'; sw.setAttribute('aria-checked', String(on)); sw.querySelector('span').textContent = on ? 'Allumée' : 'Éteinte'; target = on ? 1 : 0; });
    kel.addEventListener('input', function () { tk = +kel.value; ko.textContent = tk + ' K'; });
    cv.addEventListener('pointerdown', function (e) { drag = true; lx = e.clientX; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove', function (e) { if (!drag) return; vel = (e.clientX - lx) * .008; lx = e.clientX; rootG.rotation.y += vel; });
    ['pointerup', 'pointercancel'].forEach(function (n) { cv.addEventListener(n, function () { drag = false; }); });
    function fit() { var w = cv.clientWidth, h = cv.clientHeight; if (!w || !h) return false; if (cv.__w !== w || cv.__h !== h) { cv.__w = w; cv.__h = h; r.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); } return true; }
    var running = false; function loop() { if (!running) { running = true; requestAnimationFrame(frame); } }
    function frame() {
      running = false; if (!vis) return; if (!fit()) { loop(); return; }
      lev += (target - lev) * .07; swap = Math.min(1, swap + .045); var c = kcol(tk), e = sm(swap); cur.scale.setScalar(.7 + .3 * e);
      if (!drag) { rootG.rotation.y += vel * .9 + (reduce ? 0 : spin); vel *= .94; }
      var I = lev * (.25 + .75 * e);
      emis.forEach(function (m) { m.emissive.copy(c); m.emissiveIntensity = .03 + I * .62; });
      bulbs.forEach(function (b) { b.material.color.copy(c).lerp(new THREE.Color(1, 1, 1), .4); b.material.opacity = .15 + .85 * I; });
      pl.color.copy(c); pl.intensity = I * 3.2; pl.position.set(0, 0, 2.2); floor.material.color.copy(c); floor.material.opacity = I * .45;
      r.render(scene, cam); loop();
    }
    if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { vis = es[0].isIntersecting; if (vis) loop(); }, { rootMargin: '80px' }).observe(cv);
    loop();
  }
  function boot() {
    document.querySelectorAll('[data-atelier]').forEach(function (root) {
      if (root.__at) return; root.__at = true;
      var go = function () { loadThree().then(function () { build(root); }).catch(function () { root.querySelector('.at3-stage').style.display = 'none'; }); };
      if ('IntersectionObserver' in window) { var io = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { io.disconnect(); go(); } }, { rootMargin: '300px' }); io.observe(root); } else go();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  document.addEventListener('shopify:section:load', boot);
})();
