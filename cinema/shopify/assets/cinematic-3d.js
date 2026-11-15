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

  function init(root, opts) {
    opts = opts || {};
    var canvas = root.querySelector('.c3d__canvas');
    var chapters = [].slice.call(root.querySelectorAll('.c3d__chapter'));
    var dots = [].slice.call(root.querySelectorAll('.c3d__dot'));
    var hint = root.querySelector('.c3d__hint');
    var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    var accent = new THREE.Color(opts.accent || '#ffb46b');

    /* titres mot par mot */
    [].forEach.call(root.querySelectorAll('.c3d__title'), function (t) {
      var words = t.textContent.trim().split(/\s+/); t.setAttribute('aria-label', t.textContent.trim()); t.innerHTML = '';
      words.forEach(function (w, i) { var s = document.createElement('span'); s.className = 'w'; s.setAttribute('aria-hidden', 'true'); s.style.transitionDelay = (i * 90) + 'ms'; s.textContent = w + ' '; t.appendChild(s); });
    });

    var renderer;
    try { renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false, powerPreference: 'high-performance' }); }
    catch (e) { root.classList.add('c3d--nogl'); chapters.forEach(function (c) { c.classList.add('is-active'); }); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    var scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07060a);
    scene.fog = new THREE.FogExp2(0x07060a, .045);
    var camera = new THREE.PerspectiveCamera(38, 1, .1, 80);

    /* environnement de studio (reflets) généré par code */
    (function () {
      var env = new THREE.Scene(); env.background = new THREE.Color(0x050407);
      function panel(w, h, col, i, x, y, z) { var m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(col).multiplyScalar(i), side: THREE.DoubleSide })); m.position.set(x, y, z); m.lookAt(0, 0, 0); env.add(m); }
      panel(8, 5, '#ffffff', 6, -6, 5, 4); panel(4, 8, '#9fb6ff', 3, 7, 3, -3); panel(10, 2, '#ffb46b', 4, 0, 1, -8); panel(6, 6, '#ffffff', 1.5, 0, 9, 0);
      var pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(env, .04).texture; pm.dispose();
    })();

    /* sol */
    var floor = new THREE.Mesh(new THREE.CircleGeometry(30, 64), new THREE.MeshStandardMaterial({ color: 0x0d0b10, roughness: .32, metalness: .2 }));
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
    var pool = new THREE.Mesh(new THREE.PlaneGeometry(9, 9), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(radial('rgba(255,200,130,.9)', 'rgba(0,0,0,0)')), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0 }));
    pool.rotation.x = -Math.PI / 2; pool.position.y = .01; scene.add(pool);

    /* ---------- le luminaire, 100 % procédural (dimensions en unités = 10 cm) ---------- */
    var lamp = new THREE.Group(); scene.add(lamp);
    var finish = null;
    var baseMat = new THREE.MeshStandardMaterial({ roughness: .8, metalness: 0 });
    function applyFinish(name) {
      var f = (FINISHES[name] || FINISHES.travertin)(); if (finish) { baseMat.map.dispose(); }
      var t = new THREE.CanvasTexture(f.map); t.encoding = THREE.sRGBEncoding; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4;
      baseMat.map = t; baseMat.bumpMap = t; baseMat.bumpScale = f.bump * .12; baseMat.roughness = f.rough; baseMat.metalness = f.metal; baseMat.needsUpdate = true; finish = name;
    }
    applyFinish('travertin');

    var baseProf = [new THREE.Vector2(.001, 0), new THREE.Vector2(1.1, 0), new THREE.Vector2(1.14, .06), new THREE.Vector2(1.08, .5), new THREE.Vector2(.95, .66), new THREE.Vector2(.22, .72), new THREE.Vector2(.001, .72)];
    var base = new THREE.Mesh(new THREE.LatheGeometry(baseProf, 96), baseMat); base.castShadow = base.receiveShadow = true; lamp.add(base);

    var brass = new THREE.MeshStandardMaterial({ color: 0xd9a35a, metalness: 1, roughness: .2 });
    var stem = new THREE.Group(); lamp.add(stem);
    var rod = new THREE.Mesh(new THREE.CylinderGeometry(.075, .075, 1.55, 32), brass); rod.position.y = .72 + .775; rod.castShadow = true; stem.add(rod);
    var collar = new THREE.Mesh(new THREE.TorusGeometry(.13, .035, 16, 48), brass); collar.rotation.x = Math.PI / 2; collar.position.y = .78; stem.add(collar);
    var socket = new THREE.Mesh(new THREE.CylinderGeometry(.16, .2, .26, 32), brass); socket.position.y = 2.38; stem.add(socket);

    var shadeG = new THREE.Group(); lamp.add(shadeG);
    var shadeProf = []; for (var j = 0; j <= 28; j++) { var u = j / 28; shadeProf.push(new THREE.Vector2(.42 + Math.pow(u, 1.35) * .95, 2.55 + u * 1.05)); }
    var shadeMat = new THREE.MeshStandardMaterial({ color: 0xf0e4d0, roughness: .65, metalness: 0, side: THREE.DoubleSide, emissive: 0xffa84d, emissiveIntensity: 0 });
    var shade = new THREE.Mesh(new THREE.LatheGeometry(shadeProf, 96, 0, Math.PI * 2), shadeMat); shade.castShadow = true; shadeG.add(shade);
    var rim = new THREE.Mesh(new THREE.TorusGeometry(1.37, .018, 12, 96), brass); rim.rotation.x = Math.PI / 2; rim.position.y = 3.6; shadeG.add(rim);

    var bulbMat = new THREE.MeshBasicMaterial({ color: 0x3a2c1c });
    var bulb = new THREE.Mesh(new THREE.SphereGeometry(.3, 32, 24), bulbMat); bulb.position.y = 2.95; lamp.add(bulb);
    var halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(radial('rgba(255,225,170,1)', 'rgba(0,0,0,0)')), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, opacity: 0 }));
    halo.position.y = 2.95; halo.scale.set(1, 1, 1); lamp.add(halo);

    var lightPt = new THREE.PointLight(0xffb46b, 0, 14, 1.6); lightPt.position.y = 2.95; lamp.add(lightPt);
    var spot = new THREE.SpotLight(0xffd9a8, 0, 18, .62, .8, 1.2); spot.position.set(0, 3.2, 0); spot.target.position.set(0, 0, 0);
    spot.castShadow = true; spot.shadow.mapSize.set(1024, 1024); spot.shadow.bias = -.0004; lamp.add(spot); lamp.add(spot.target);
    var rimL = new THREE.DirectionalLight(0x8fa8ff, .5); rimL.position.set(-6, 4, -5); scene.add(rimL);
    scene.add(new THREE.HemisphereLight(0x1b1a30, 0x050407, .35));

    /* particules de poussière */
    var N = 700, pPos = new Float32Array(N * 3), pSeed = [];
    for (var n = 0; n < N; n++) { pPos[n * 3] = (Math.random() - .5) * 22; pPos[n * 3 + 1] = Math.random() * 9; pPos[n * 3 + 2] = (Math.random() - .5) * 22; pSeed.push(Math.random() * 6.28); }
    var pGeo = new THREE.BufferGeometry(); pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    var dust = new THREE.Points(pGeo, new THREE.PointsMaterial({ size: .05, map: new THREE.CanvasTexture(radial('rgba(255,235,200,1)', 'rgba(0,0,0,0)')), color: 0xffd9a8, transparent: true, opacity: .75, blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true }));
    scene.add(dust);

    /* trajectoire caméra : 4 chapitres */
    var camPath = new THREE.CatmullRomCurve3([new THREE.Vector3(0, 2.2, 13), new THREE.Vector3(2, 2.6, 7.2), new THREE.Vector3(5.2, 3.6, 8.2), new THREE.Vector3(-4.2, 3.0, 7.4)], false, 'catmullrom', .5);
    var tgtPath = new THREE.CatmullRomCurve3([new THREE.Vector3(0, 1.6, 0), new THREE.Vector3(0, 2.2, 0), new THREE.Vector3(0, 2.6, 0), new THREE.Vector3(0, 1.9, 0)], false, 'catmullrom', .5);

    /* interaction */
    var target = 0, prog = 0, rotY = 0, rotTarget = 0, drag = false, lastX = 0, px = 0, py = 0, mx = 0, my = 0;
    function onScroll() { var r = root.getBoundingClientRect(), span = Math.max(1, r.height - innerHeight); target = reduced ? .3 : clamp(-r.top / span, 0, 1); }
    window.addEventListener('scroll', onScroll, { passive: true }); window.addEventListener('resize', onScroll);
    canvas.addEventListener('pointerdown', function (e) { drag = true; lastX = e.clientX; });
    window.addEventListener('pointerup', function () { drag = false; });
    window.addEventListener('pointermove', function (e) { if (drag) { rotTarget += (e.clientX - lastX) * .01; lastX = e.clientX; } mx = (e.clientX / innerWidth - .5); my = (e.clientY / innerHeight - .5); });
    [].forEach.call(root.querySelectorAll('[data-finish]'), function (b) { b.addEventListener('click', function () { applyFinish(b.dataset.finish); [].forEach.call(root.querySelectorAll('[data-finish]'), function (o) { o.setAttribute('aria-pressed', o === b); }); }); });
    [].forEach.call(root.querySelectorAll('[data-shade]'), function (b) { b.addEventListener('click', function () { shadeMat.color.set(b.dataset.shade); [].forEach.call(root.querySelectorAll('[data-shade]'), function (o) { o.setAttribute('aria-pressed', o === b); }); }); });

    function resize() { var w = canvas.clientWidth || root.clientWidth, h = canvas.clientHeight || innerHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.fov = w / h < .8 ? 52 : 38; camera.updateProjectionMatrix(); }
    window.addEventListener('resize', resize); resize(); onScroll(); if (reduced) prog = target;

    var visible = true, t0 = performance.now(), last = t0, activeIdx = -1;
    if ('IntersectionObserver' in window) new IntersectionObserver(function (e) { visible = e[0].isIntersecting; }).observe(root);

    function frame(now) {
      requestAnimationFrame(frame); if (!visible) return;
      var dt = Math.min(.05, (now - last) / 1000); last = now; var t = (now - t0) / 1000;
      prog += (target - prog) * (reduced ? 1 : 1 - Math.pow(.0009, dt));   // inertie cinématique
      rotY += (rotTarget - rotY) * (1 - Math.pow(.001, dt));

      var glow = smooth(.07, .26, prog) * (.94 + Math.sin(t * 7.3) * .02 + Math.sin(t * 2.1) * .02);
      var ex = smooth(.46, .6, prog) * (1 - smooth(.7, .82, prog));
      var rotAuto = reduced ? 0 : t * .12 + prog * 1.2;

      lamp.rotation.y = rotAuto + rotY;
      stem.position.y = ex * .9; shadeG.position.y = ex * 2.1; bulb.position.y = 2.95 + ex * 1.4; halo.position.y = bulb.position.y; lightPt.position.y = bulb.position.y; spot.position.y = bulb.position.y + .2;
      lamp.position.y = Math.sin(t * .8) * .03 * (1 - glow * .6) + smooth(0, .12, prog) * 0;

      bulbMat.color.setRGB(.23 + glow * .77, .17 + glow * .72, .11 + glow * .45);
      shadeMat.emissiveIntensity = glow * .85; shadeMat.emissive.copy(accent);
      lightPt.intensity = glow * 9; spot.intensity = glow * 26; lightPt.color.copy(accent); halo.material.opacity = glow * .95; halo.scale.setScalar(2.2 + glow * 3.2);
      pool.material.opacity = glow * .5; pool.scale.setScalar(.9 + glow * .5);
      renderer.toneMappingExposure = .9 + glow * .25;

      var k = prog * 3; var cp = camPath.getPoint(clamp(prog, 0, 1)), tp = tgtPath.getPoint(clamp(prog, 0, 1));
      camera.position.set(cp.x + mx * .6, cp.y - my * .4, cp.z); camera.lookAt(tp.x, tp.y, tp.z);

      var arr = pGeo.attributes.position.array; for (var i = 0; i < N; i++) { arr[i * 3 + 1] += dt * (.12 + Math.sin(pSeed[i]) * .05); arr[i * 3] += Math.sin(t * .3 + pSeed[i]) * dt * .06; if (arr[i * 3 + 1] > 9) arr[i * 3 + 1] = 0; } pGeo.attributes.position.needsUpdate = true;
      dust.material.opacity = .35 + glow * .5;

      var idx = clamp(Math.floor(prog * chapters.length * .9999), 0, chapters.length - 1);
      if (!reduced && idx !== activeIdx) { activeIdx = idx; chapters.forEach(function (c, i) { c.classList.toggle('is-active', i === idx); }); dots.forEach(function (d, i) { d.classList.toggle('is-active', i === idx); }); if (hint) hint.style.opacity = idx === 0 ? 1 : 0; }
      renderer.render(scene, camera);
    }
    requestAnimationFrame(frame);
    root.__c3d = { get progress() { return prog; }, set progress(v) { target = v; prog = v; } };
  }

  function boot() { [].forEach.call(document.querySelectorAll('.c3d'), function (el) { init(el, { accent: el.dataset.accent }); }); }
  if (document.readyState !== 'loading') boot(); else document.addEventListener('DOMContentLoaded', boot);
})();
