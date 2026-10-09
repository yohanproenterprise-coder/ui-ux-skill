/* Galerie Lumineuse — « Lampe qui s'allume au scroll »
   Une scène 3D pilotée par la progression du défilement dans la section.
   0 % : pièce dans le noir · ~25 % : allumage (scintillement) · puis montée en chaleur et travelling. */
(function () {
  'use strict';
  var THREE_URL = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var clamp = function (v, a, b) { return Math.max(a, Math.min(b, v)); };
  var lerp = function (a, b, t) { return a + (b - a) * t; };
  var smooth = function (t) { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };

  function kelvin(k) {
    var t = k / 100, r, g, b;
    r = t <= 66 ? 255 : 329.698727446 * Math.pow(t - 60, -0.1332047592);
    g = t <= 66 ? 99.4708025861 * Math.log(t) - 161.1195681661 : 288.1221695283 * Math.pow(t - 60, -0.0755148492);
    b = t >= 66 ? 255 : (t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307);
    var c = function (v) { return clamp(Math.round(v), 0, 255); };
    return { r: c(r), g: c(g), b: c(b) };
  }

  var threePromise;
  function loadThree() {
    if (window.THREE) return Promise.resolve();
    return threePromise || (threePromise = new Promise(function (ok, ko) {
      var s = document.createElement('script');
      s.src = THREE_URL; s.async = true; s.onload = ok; s.onerror = ko;
      document.head.appendChild(s);
    }));
  }

  /* ------------------------------------------------------------
     Scène 3D
  ------------------------------------------------------------ */
  function buildScene(canvas, style) {
    var copper = style !== 'glass';
    var THREE = window.THREE;
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0x050403, 1);
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    var scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050403, .035);
    var camera = new THREE.PerspectiveCamera(40, 1, .1, 80);

    scene.add(new THREE.HemisphereLight(0x2a2018, 0x050403, .16));

    /* pièce : sol, mur, table, objets */
    var std = function (c, r, m) { return new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m || 0 }); };
    var floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), std(0x15100c, .8));
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
    var wall = new THREE.Mesh(new THREE.PlaneGeometry(40, 18), std(0x1f1812, .95));
    wall.position.set(0, 8, -3.6); wall.receiveShadow = true; scene.add(wall);

    var top = new THREE.Mesh(new THREE.CylinderGeometry(1.7, 1.7, .1, 64), std(0x4a3524, .4, .05));
    top.position.y = .95; top.castShadow = true; top.receiveShadow = true; scene.add(top);
    var leg = new THREE.Mesh(new THREE.CylinderGeometry(.14, .24, .9, 24), std(0x16110d, .5, .3));
    leg.position.y = .45; leg.castShadow = true; scene.add(leg);
    var foot = new THREE.Mesh(new THREE.CylinderGeometry(.7, .8, .06, 40), std(0x16110d, .5, .3));
    foot.position.y = .03; foot.receiveShadow = true; scene.add(foot);

    var vase = new THREE.Mesh(new THREE.CylinderGeometry(.17, .11, .62, 32), copper ? std(0xb87333, .35, .85) : std(0xcfc2b0, .25));
    vase.position.set(.62, 1.31, .1); vase.castShadow = true; vase.receiveShadow = true; scene.add(vase);
    var bowl = new THREE.Mesh(new THREE.SphereGeometry(.4, 40, 20, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), copper ? std(0x9c5a2c, .4, .8) : std(0x8a6a4a, .5));
    bowl.position.set(-.7, 1.1, .35); bowl.rotation.x = Math.PI; bowl.castShadow = true; bowl.receiveShadow = true; scene.add(bowl);
    [0, 1].forEach(function (i) {
      var bk = new THREE.Mesh(new THREE.BoxGeometry(.7 - i * .1, .08, .5), std(i ? 0x6a2f23 : 0x2f3a46, .6));
      bk.position.set(.15 + i * .04, 1.04 + i * .08, -.55); bk.rotation.y = .2 - i * .3; bk.castShadow = true; bk.receiveShadow = true; scene.add(bk);
    });

    /* halo / cône de lumière */
    function tex(w, h, draw) { var c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); return new THREE.CanvasTexture(c); }
    var HT = tex(256, 256, function (g) {
      var gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
      gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(.18, 'rgba(255,255,255,.55)');
      gr.addColorStop(.5, 'rgba(255,255,255,.12)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    });
    var CT = tex(8, 256, function (g, w, h) {
      var gr = g.createLinearGradient(0, 0, 0, h);
      gr.addColorStop(0, 'rgba(255,255,255,.9)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = gr; g.fillRect(0, 0, w, h);
    });

    /* luminaires : 4 modèles 3D inspirés de produits de la boutique
       dome = CUIVRE (cuivre & marbre) · tubes = LÉYA · glass = SOLIS (globes) · ring = ORION (couronne) */
    var lamps = [], lampGroup = new THREE.Group(); scene.add(lampGroup);
    var mount = function (m) { lampGroup.add(m); return m; };
    var blackMetal = std(0x16110d, .4, .8);
    function bulbMat() { return new THREE.MeshStandardMaterial({ color: 0x2a2018, emissive: 0xffb55c, emissiveIntensity: 0, roughness: .35 }); }
    function cableTo(x, y, z) { var len = 10 - y, m = new THREE.Mesh(new THREE.CylinderGeometry(.012, .012, len, 6), new THREE.MeshBasicMaterial({ color: 0x2a2520 })); m.position.set(x, y + len / 2, z || 0); mount(m); }
    /* un « bloc de lumière » : lumière ponctuelle + halo + cône, piloté par lv[i] */
    function light(i, mat, x, y, r, coneR, coneTop, gain, dome) {
      var pl = new THREE.PointLight(0xffb55c, 0, 16, 2); pl.position.set(x, y, 0); mount(pl);
      var sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: HT, color: 0xffb55c, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0 }));
      sp.scale.setScalar(r * 8); sp.position.set(x, y, 0); mount(sp);
      var ch = coneTop - .95, cone = new THREE.Mesh(new THREE.ConeGeometry(coneR, ch, 40, 1, true),
        new THREE.MeshBasicMaterial({ map: CT, color: 0xffb55c, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
      cone.position.set(x, coneTop - ch / 2, 0); mount(cone);
      lamps.push({ i: i, mat: mat, dome: dome || null, pl: pl, sp: sp, cone: cone, r: r, x: x, gain: gain });
    }

    var builders = {
      /* CUIVRE : dôme cuivre poli + sphère de marbre */
      dome: function () {
        [[-1.05, 3.3, .42], [.1, 2.55, .62], [1.2, 3.55, .34]].forEach(function (d, i) {
          var x = d[0], y = d[1], r = d[2], topY = y + r * 1.15 + r * .28;
          cableTo(x, topY);
          var mat = bulbMat(), bulb = new THREE.Mesh(new THREE.SphereGeometry(r * .52, 48, 48), mat); bulb.position.set(x, y - r * .08, 0); mount(bulb);
          var geo = new THREE.SphereGeometry(r * 1.15, 56, 32, 0, Math.PI * 2, 0, Math.PI * .58);
          var outer = new THREE.MeshStandardMaterial({ color: 0xc8601f, metalness: .45, roughness: .32, side: THREE.FrontSide });
          var inner = new THREE.MeshStandardMaterial({ color: 0xd9772f, metalness: .35, roughness: .4, side: THREE.BackSide });
          var dome = new THREE.Group(); dome.add(new THREE.Mesh(geo, outer)); dome.add(new THREE.Mesh(geo, inner));
          dome.position.set(x, y + r * .28, 0); dome.userData.outer = outer; dome.userData.inner = inner; mount(dome);
          var cap = new THREE.Mesh(new THREE.CylinderGeometry(r * .13, r * .2, r * .3, 24), std(0xa4521a, .3, .8)); cap.position.set(x, topY + r * .12, 0); mount(cap);
          light(i, mat, x, y - r * .08, r, r * 2.6, y - r * .2, 1.7, dome);
        });
        return 2.5;
      },
      /* LÉYA : barre horizontale et tubes lumineux de longueurs étagées (effet arête) */
      tubes: function () {
        var barY = 3.35, mats = [bulbMat(), bulbMat(), bulbMat()];
        var bar = new THREE.Mesh(new THREE.BoxGeometry(2.9, .07, .12), blackMetal); bar.position.set(.1, barY, 0); bar.castShadow = true; mount(bar);
        cableTo(-1.15, barY); cableTo(1.35, barY);
        for (var k = 0; k < 20; k++) {
          var x = -1.25 + k * .138, len = .5 + 1.35 * (1 - Math.min(1, Math.abs(x) / 1.4)), g = x < -.45 ? 0 : (x > .45 ? 2 : 1);
          var tube = new THREE.Mesh(new THREE.CylinderGeometry(.03, .03, len, 14), mats[g]);
          tube.position.set(x + .1, barY - len / 2 - .04, 0); mount(tube);
        }
        [[-.85, 0], [.1, 1], [1.05, 2]].forEach(function (d) { light(d[1], mats[d[1]], d[0] + .1, barY - 1.0, .55, 1.0, barY - .9, 1.9); });
        return 3.0;
      },
      /* SOLIS : trois globes opalins, calotte métal noir */
      glass: function () {
        [[-1.05, 3.3, .42], [.1, 2.55, .62], [1.2, 3.55, .34]].forEach(function (d, i) {
          var x = d[0], y = d[1], r = d[2];
          cableTo(x, y + r);
          var mat = bulbMat(), bulb = new THREE.Mesh(new THREE.SphereGeometry(r, 48, 48), mat); bulb.position.set(x, y, 0); mount(bulb);
          var cap = new THREE.Mesh(new THREE.CylinderGeometry(r * .22, r * .3, r * .4, 24), std(0x16130f, .3, .9)); cap.position.set(x, y + r * .95, 0); mount(cap);
          light(i, mat, x, y, r, r * 2.6, y - r * .2, 1.15);
        });
        return 2.5;
      },
      /* ORION : couronne métallique, neuf ampoules */
      ring: function () {
        var cy = 3.0, cx = .1, R = .98, mats = [bulbMat(), bulbMat(), bulbMat()];
        var ringM = new THREE.Mesh(new THREE.TorusGeometry(R, .05, 16, 72), blackMetal); ringM.rotation.x = Math.PI / 2; ringM.position.set(cx, cy, 0); ringM.castShadow = true; mount(ringM);
        [0, 2.094, 4.188].forEach(function (a) { cableTo(cx + Math.cos(a + .5) * R, cy, Math.sin(a + .5) * R * .6); });
        for (var k = 0; k < 9; k++) {
          var a = k / 9 * Math.PI * 2, bx = cx + Math.cos(a) * R, bz = Math.sin(a) * R, g = bx < cx - .3 ? 0 : (bx > cx + .3 ? 2 : 1);
          var b = new THREE.Mesh(new THREE.SphereGeometry(.14, 24, 24), mats[g]); b.position.set(bx, cy - .14, bz); mount(b);
          var socket = new THREE.Mesh(new THREE.CylinderGeometry(.05, .06, .12, 12), blackMetal); socket.position.set(bx, cy - .02, bz); mount(socket);
        }
        [[-.75, 0], [.1, 1], [.95, 2]].forEach(function (d) { light(d[1], mats[d[1]], d[0] + .1, cy - .2, .5, 1.0, cy - .3, 1.9); });
        return 2.8;
      }
    };

    function clearLamps() { while (lampGroup.children.length) lampGroup.remove(lampGroup.children[0]); lamps.length = 0; }
    function buildLamps(style) {
      clearLamps();
      var y = (builders[style] || builders.tubes)();
      spot.position.set(.1, y, 0);
    }

    /* projecteur principal : ombres sur la table */
    var spot = new THREE.SpotLight(0xffb55c, 0, 14, .78, .9, 1.2);
    spot.position.set(.1, 2.5, 0); spot.target.position.set(0, .95, 0);
    spot.castShadow = true; spot.shadow.mapSize.set(1024, 1024); spot.shadow.bias = -.0008; spot.shadow.radius = 4;
    scene.add(spot); scene.add(spot.target);
    buildLamps(style);

    /* poussière dans la lumière */
    var N = 320, pos = new Float32Array(N * 3), spd = [];
    for (var n = 0; n < N; n++) { pos[n * 3] = (Math.random() - .5) * 6; pos[n * 3 + 1] = .4 + Math.random() * 4; pos[n * 3 + 2] = (Math.random() - .5) * 4; spd.push(.05 + Math.random() * .2); }
    var pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    var pm = new THREE.PointsMaterial({ color: 0xffb55c, size: .03, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    scene.add(new THREE.Points(pg, pm));

    var mouse = { x: 0, y: 0 }, sm = { x: 0, y: 0 };
    addEventListener('pointermove', function (e) { mouse.x = e.clientX / innerWidth * 2 - 1; mouse.y = e.clientY / innerHeight * 2 - 1; }, { passive: true });

    return {
      resize: function () {
        var w = canvas.clientWidth, h = canvas.clientHeight; if (!w || !h) return;
        renderer.setSize(w, h, false); camera.aspect = w / h; camera.fov = w / h < .85 ? 58 : 40; camera.updateProjectionMatrix();
        this.portrait = w / h < .85;
      },
      portrait: false,
      render: function (p, lv, c, t, ignite) {
        var col = new THREE.Color(c.r / 255, c.g / 255, c.b / 255);
        sm.x += (mouse.x - sm.x) * .04; sm.y += (mouse.y - sm.y) * .04;
        lamps.forEach(function (L, i) {
          var l = lv[L.i];
          L.mat.emissive.copy(col); L.mat.emissiveIntensity = .02 + L.gain * l;
          if (L.dome) {
            var cu = new THREE.Color(0xb8581c);
            L.dome.userData.outer.emissive.copy(cu).multiplyScalar(.5 * l);
            L.dome.userData.inner.emissive.copy(col).multiplyScalar(.55 * l);
          }
          L.pl.color.copy(col); L.pl.intensity = 1.7 * l;
          L.sp.material.color.copy(col); L.sp.material.opacity = .5 * l; L.sp.scale.setScalar(L.r * (8 + 1.2 * Math.sin(t * 1.4 + i)));
          L.cone.material.color.copy(col); L.cone.material.opacity = .055 * l;
          L.pl.position.x = L.x + Math.sin(t * .6 + i) * .01;
        });
        spot.color.copy(col); spot.intensity = 4.2 * lv[1];
        pm.color.copy(col); pm.opacity = .65 * lv[1];
        /* travelling avant + léger roulis */
        var dolly = smooth(p);
        var portrait = this.portrait;
        /* bureau : scène décalée à droite ; mobile : scène descendue sous le texte */
        var shift = portrait ? 0 : -1.25, lift = portrait ? 3.1 : 0;
        camera.position.set(shift + sm.x * .35, lerp(1.7, 1.9, dolly) - sm.y * .1 + lift, lerp(portrait ? 11.5 : 8.6, portrait ? 8.6 : 6.1, dolly));
        camera.lookAt(shift, lerp(1.7, 1.85, dolly) + lift, 0);
        var a = pg.attributes.position.array;
        for (var n = 0; n < N; n++) { a[n * 3 + 1] += spd[n] * .004; if (a[n * 3 + 1] > 4.6) a[n * 3 + 1] = .4; a[n * 3] += Math.sin(t + n) * .0007; }
        pg.attributes.position.needsUpdate = true;
        renderer.toneMappingExposure = lerp(.9, 1.05, smooth((p - .3) / .5));
        renderer.render(scene, camera);
      },
      setStyle: function (st) { buildLamps(st); },
      dispose: function () { renderer.dispose(); }
    };
  }

  /* ------------------------------------------------------------
     Contrôleur de section
  ------------------------------------------------------------ */
  function init(sec) {
    if (sec.dataset.ready) return;
    sec.dataset.ready = '1';
    var kStart = +sec.dataset.kStart || 2200, kEnd = +sec.dataset.kEnd || 3200;
    sec.__setStyle = function (st) { sec.dataset.lampStyle = st; if (scene) scene.setStyle(st); kick(); };
    var canvas = sec.querySelector('.sl-canvas'), glow = sec.querySelector('.sl-glow');
    var photos = [].slice.call(sec.querySelectorAll('[data-photo]')), dust = sec.querySelector('[data-sl-dust]');
    var dctx = dust ? dust.getContext('2d') : null, motes = [], dW = 0, dH = 0;
    /* chaque photo devient : un fond prolongé et flouté + un cadre à 3 couches (sombre, allumée, halo) */
    photos.forEach(function (ph) {
      var base = ph.querySelector('img'); if (!base) return;
      var frame = document.createElement('div'); frame.className = 'frame';
      var bg = base.cloneNode(); bg.className = 'bgfill'; bg.alt = ''; bg.setAttribute('aria-hidden', 'true');
      base.className = 'lyr base'; frame.appendChild(base);
      ['hl', 'bloom'].forEach(function (k) { var im = base.cloneNode(); im.className = 'lyr ' + k; im.alt = ''; im.setAttribute('aria-hidden', 'true'); frame.appendChild(im); });
      ph.insertBefore(bg, ph.firstChild); ph.appendChild(frame);
    });
    var mx = 0, my = 0, px = 0, py = 0;
    addEventListener('pointermove', function (e) { mx = e.clientX / innerWidth * 2 - 1; my = e.clientY / innerHeight * 2 - 1; }, { passive: true });
    if (dust) for (var m = 0; m < 150; m++) motes.push({ x: Math.random(), y: Math.random(), s: .4 + Math.random() * 1.6, v: .00004 + Math.random() * .00012, a: .25 + Math.random() * .75, ph: Math.random() * 6.28 });
    function sizeDust() {
      if (!dust) return;
      var r = dust.getBoundingClientRect(), dpr = Math.min(devicePixelRatio, 2);
      dW = dust.width = Math.max(1, Math.round(r.width * dpr)); dH = dust.height = Math.max(1, Math.round(r.height * dpr));
    }
    function drawDust(L, c, t) {
      if (!dctx) return;
      dctx.clearRect(0, 0, dW, dH);
      if (L < .02) return;
      motes.forEach(function (o) {
        o.y -= o.v * 16; if (o.y < -.02) { o.y = 1.02; o.x = Math.random(); }
        var x = (o.x + Math.sin(t * .4 + o.ph) * .012) * dW, y = o.y * dH;
        dctx.fillStyle = 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + (o.a * L * .8).toFixed(3) + ')';
        dctx.beginPath(); dctx.arc(x, y, o.s * (dW / 1000 + .6), 0, 6.283); dctx.fill();
      });
    }
    var steps = [].slice.call(sec.querySelectorAll('[data-step]'));
    var bar = sec.querySelector('[data-sl-bar]'), kOut = null;
    var target = reduce ? .85 : 0, p = target, scene = null, visible = false, raf = 0, clock0 = performance.now();

    function measure() {
      if (reduce) { target = .85; return; }
      var r = sec.getBoundingClientRect(), total = sec.offsetHeight - innerHeight;
      target = total > 0 ? clamp(-r.top / total, 0, 1) : .85;
    }
    addEventListener('scroll', measure, { passive: true });
    addEventListener('resize', function () { measure(); sizeDust(); if (scene) scene.resize(); });

    function levels(pp, t) {
      /* allumage échelonné de gauche à droite, avec scintillement avant stabilisation */
      return [0, 1, 2].map(function (i) {
        var raw = clamp((pp - (.22 + i * .045)) / .2, 0, 1), e = smooth(raw);
        var flick = raw > 0 && raw < .9 ? (.78 + .22 * Math.sin(pp * 420 + i * 5) * Math.sin(pp * 170 + i)) : 1;
        return clamp(e * flick, 0, 1);
      });
    }

    var last = performance.now();
    function frame(now) {
      raf = 0;
      var t = (now - clock0) / 1000, dt = Math.min(.1, Math.max(0, (now - last) / 1000)); last = now;
      p += (target - p) * (reduce ? 1 : 1 - Math.exp(-dt * 9));
      if (Math.abs(target - p) < .0005) p = target;
      var lv = levels(p, t), kk = lerp(kStart, kEnd, smooth((p - .3) / .55)), c = kelvin(kk);
      steps.forEach(function (s) {
        var from = +s.dataset.from / 100, to = +s.dataset.to / 100;
        s.classList.toggle('on', p >= from && p <= to);
      });
      if (bar) bar.style.transform = 'scaleX(' + p.toFixed(3) + ')';
      if (kOut) kOut.textContent = Math.round(kk / 50) * 50 + ' K';
      if (glow) { glow.style.opacity = (lv[1] * (scene ? .14 : 1)).toFixed(3); glow.style.background = 'radial-gradient(ellipse 60% 55% at var(--sl-gx,62%) var(--sl-gy,38%), rgba(' + c.r + ',' + c.g + ',' + c.b + ',.55), transparent 70%)'; }
      if (photos.length) {
        /* le produit sort du noir : luminosité, léger travelling, bascule entre ses photos */
        var Lp = lv[1], n = photos.length;
        /* fondu enchaîné continu entre les photos : la suivante apparaît pendant que la précédente s'éteint doucement */
        var wts = photos.map(function (ph, i) {
          if (n < 2) return 1;
          var a = i === 0 ? 1 : smooth((p - (.5 + (i - 1) * .22)) / .08);
          var nxt = i === n - 1 ? 0 : smooth((p - (.5 + i * .22)) / .08);
          return nxt >= .995 ? 0 : a;
        });
        var Lh = Lp, spread = smooth((p - .2) / .55), La = smooth((p - .45) / .4);
        px += (-mx * 12 - px) * .06; py += (-my * 8 - py) * .06;
        sec.style.setProperty('--sl-hl', Lh.toFixed(3));
        sec.style.setProperty('--sl-r', (4 + 150 * spread).toFixed(1) + '%');
        sec.style.setProperty('--sl-b', (.035 + .06 * La).toFixed(3));
        sec.style.setProperty('--sl-bg', (.03 + .5 * smooth((p - .3) / .5)).toFixed(3));
        sec.style.setProperty('--sl-px', px.toFixed(1) + 'px');
        sec.style.setProperty('--sl-py', py.toFixed(1) + 'px');
        sec.style.setProperty('--sl-z', (1 + .035 * smooth(p)).toFixed(4));
        photos.forEach(function (ph, i) {
          var w = wts[i];
          ph.style.opacity = w.toFixed(3);
          ph.style.visibility = w > .003 ? '' : 'hidden';
          ph.classList.toggle('on', w > .003);
          if (ph.dataset.lx) {
            /* en portrait la photo carrée est recadrée au centre : on ramène le luminaire dans le cadre visible */
            var sr = sec.querySelector('.sl-stage').getBoundingClientRect(), vis = Math.min(1, sr.width / Math.max(1, sr.height));
            var lxv = 50 + (+ph.dataset.lx - 50) / vis;
            ph.style.setProperty('--sl-lx', lxv.toFixed(1) + '%'); ph.style.setProperty('--sl-ly', ph.dataset.ly + '%');
          }
          /* léger souffle de lumière et de zoom pendant le changement de photo */
          ph.style.setProperty('--sl-px', (px + (1 - w) * (i ? 22 : -22)).toFixed(1) + 'px');
          ph.style.setProperty('--sl-z', ((1 + .035 * smooth(p)) * (1 + (i ? (1 - w) * .07 : 0))).toFixed(4));
        });
        drawDust(Lp, c, t);
      }
      if (scene) scene.render(p, lv, c, t, lv[1]);
      if (visible && (Math.abs(target - p) > .0004 || scene || dust)) raf = requestAnimationFrame(frame);
    }
    function kick() { if (!raf && visible) raf = requestAnimationFrame(frame); }
    addEventListener('scroll', kick, { passive: true });

    function start() {
      if (scene || !canvas || sec.dataset.threeD === 'loading') return;
      sec.dataset.threeD = 'loading';
      var gl; try { gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl'); } catch (e) {}
      if (!gl) { canvas.style.display = 'none'; return; }
      loadThree().then(function () { scene = buildScene(canvas, sec.dataset.lampStyle || (sec.dataset.finish === 'glass' ? 'glass' : 'tubes')); scene.resize(); kick(); }).catch(function () { canvas.style.display = 'none'; });
    }

    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) {
        visible = es[0].isIntersecting;
        if (visible) { measure(); start(); kick(); }
      }, { rootMargin: '600px 0px' }).observe(sec);
    } else { visible = true; measure(); start(); kick(); }

    sizeDust(); measure(); frame(performance.now());
  }

  function boot(scope) { [].slice.call((scope || document).querySelectorAll('[data-scroll-lamp]')).forEach(init); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { boot(); }); else boot();
  document.addEventListener('shopify:section:load', function (e) { boot(e.target); });
})();
