/* Galerie Lumineuse — scène 3D du hero (Three.js chargé à la demande)
   Cinq suspensions lumineuses cliquables, cônes de lumière, poussière, parallaxe souris. */
(function () {
  'use strict';
  var THREE_URL = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  function loadThree() {
    if (window.THREE) return Promise.resolve();
    return new Promise(function (ok, ko) {
      var s = document.createElement('script');
      s.src = THREE_URL; s.async = true; s.onload = ok; s.onerror = ko;
      document.head.appendChild(s);
    });
  }

  function start(hero) {
    var THREE = window.THREE, canvas = hero.querySelector('[data-hero-canvas]');
    var gl; try { gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl'); } catch (e) {}
    if (!THREE || !gl) { canvas.style.display = 'none'; return; }

    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    var scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x080605, .045);
    var camera = new THREE.PerspectiveCamera(42, 1, .1, 100);
    camera.position.set(0, 0, 12);
    scene.add(new THREE.AmbientLight(0xffffff, .12));

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

    var group = new THREE.Group(); scene.add(group);
    var lamps = [], bulbs = [];
    [[-3.2, -.4, .9, 0], [0, -1.6, 1.25, 1.6], [3.2, .3, .75, 3.1], [1.7, 2.1, .45, 4.4], [-1.7, 1.6, .55, 5.2]].forEach(function (d) {
      var piv = new THREE.Group(); piv.position.set(d[0], 9, 0); group.add(piv);
      var len = 9 - d[1];
      var cable = new THREE.Mesh(new THREE.CylinderGeometry(.012, .012, len, 6), new THREE.MeshBasicMaterial({ color: 0x2a2520 }));
      cable.position.y = -len / 2; piv.add(cable);
      var cap = new THREE.Mesh(new THREE.CylinderGeometry(d[2] * .22, d[2] * .28, d[2] * .35, 24), new THREE.MeshStandardMaterial({ color: 0x16130f, metalness: .9, roughness: .3 }));
      cap.position.y = -len + d[2] * .95; piv.add(cap);
      var mat = new THREE.MeshStandardMaterial({ color: 0x2b2118, emissive: 0xffb55c, emissiveIntensity: 1.1, roughness: .4 });
      var bulb = new THREE.Mesh(new THREE.SphereGeometry(d[2], 48, 48), mat);
      bulb.position.y = -len; piv.add(bulb);
      var light = new THREE.PointLight(0xffb55c, 2.2, 16, 1.6); light.position.copy(bulb.position); piv.add(light);
      var sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: HT, color: 0xffb55c, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: .85 }));
      sp.scale.setScalar(d[2] * 7); sp.position.copy(bulb.position); piv.add(sp);
      var ch = d[2] * 9;
      var cone = new THREE.Mesh(new THREE.ConeGeometry(d[2] * 3.2, ch, 40, 1, true), new THREE.MeshBasicMaterial({ map: CT, color: 0xffb55c, transparent: true, opacity: .12, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
      cone.position.set(0, -len - ch / 2 + d[2] * .3, 0); piv.add(cone);
      var L = { piv: piv, mat: mat, light: light, sp: sp, cone: cone, ph: d[3], base: d[2], on: true, lvl: 1 };
      bulb.userData.lamp = L; bulbs.push(bulb); lamps.push(L);
    });

    var N = 380, pos = new Float32Array(N * 3), spd = [];
    for (var i = 0; i < N; i++) {
      pos[i * 3] = (Math.random() - .5) * 16; pos[i * 3 + 1] = (Math.random() - .5) * 10; pos[i * 3 + 2] = (Math.random() - .5) * 8;
      spd.push(.1 + Math.random() * .3);
    }
    var pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    var pm = new THREE.PointsMaterial({ color: 0xffb55c, size: .035, transparent: true, opacity: .65, blending: THREE.AdditiveBlending, depthWrite: false });
    scene.add(new THREE.Points(pg, pm));

    window.GL.onTemp(function (c) {
      var col = new THREE.Color(c.r / 255, c.g / 255, c.b / 255);
      lamps.forEach(function (l) { l.mat.emissive.copy(col); l.light.color.copy(col); l.sp.material.color.copy(col); l.cone.material.color.copy(col); });
      pm.color.copy(col);
    });
    window.GL.setTemp(+hero.dataset.kelvin || 3000);

    function resize() {
      var w = canvas.clientWidth, h = canvas.clientHeight, m = innerWidth < 980;
      if (!w || !h) return;
      renderer.setSize(w, h, false);
      camera.aspect = w / h; camera.fov = m ? 58 : 42;
      group.position.set(m ? 0 : 2.4, m ? -.8 : 0, 0); group.scale.setScalar(m ? .72 : 1);
      camera.updateProjectionMatrix();
    }
    addEventListener('resize', resize); resize();

    /* clic = allumer / éteindre */
    var ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
    function hit(e) {
      var r = canvas.getBoundingClientRect();
      ndc.set((e.clientX - r.left) / r.width * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(ndc, camera);
      return ray.intersectObjects(bulbs)[0];
    }
    canvas.addEventListener('pointerdown', function (e) { var h = hit(e); if (h) h.object.userData.lamp.on = !h.object.userData.lamp.on; });
    canvas.addEventListener('pointermove', function (e) { canvas.style.cursor = hit(e) ? 'pointer' : ''; });

    var mouse = { x: 0, y: 0 }, sm = { x: 0, y: 0 }, scrollP = 0, vis = true, clock = new THREE.Clock();
    addEventListener('pointermove', function (e) { mouse.x = e.clientX / innerWidth * 2 - 1; mouse.y = e.clientY / innerHeight * 2 - 1; }, { passive: true });
    addEventListener('scroll', function () { scrollP = Math.min(1, scrollY / (hero.offsetHeight * .9)); }, { passive: true });
    if ('IntersectionObserver' in window) new IntersectionObserver(function (e) { vis = e[0].isIntersecting; }).observe(hero);

    (function loop() {
      if (!document.contains(hero)) { renderer.dispose(); removeEventListener('resize', resize); return; }
      requestAnimationFrame(loop);
      if (!vis) return;
      var t = reduce ? 0 : clock.getElapsedTime();
      sm.x += (mouse.x - sm.x) * .05; sm.y += (mouse.y - sm.y) * .05;
      lamps.forEach(function (l) {
        l.lvl += ((l.on ? 1 : .03) - l.lvl) * .09;
        l.piv.rotation.z = Math.sin(t * .6 + l.ph) * .045 + sm.x * .03;
        l.piv.rotation.x = Math.cos(t * .5 + l.ph) * .02;
        var pulse = 1 + Math.sin(t * 1.3 + l.ph) * .04, k = l.lvl * (1 - scrollP * .7);
        l.mat.emissiveIntensity = .04 + 1.05 * l.lvl;
        l.light.intensity = 2.2 * pulse * k;
        l.sp.scale.setScalar(l.base * 7 * pulse);
        l.sp.material.opacity = .85 * k;
        l.cone.material.opacity = .12 * k;
      });
      group.rotation.y = sm.x * .25; group.rotation.x = -sm.y * .1;
      var a = pg.attributes.position.array;
      for (var i = 0; i < N; i++) { a[i * 3 + 1] += spd[i] * .004; if (a[i * 3 + 1] > 5) a[i * 3 + 1] = -5; a[i * 3] += Math.sin(t + i) * .0008; }
      pg.attributes.position.needsUpdate = true;
      camera.position.z = 12 + scrollP * 4;
      renderer.render(scene, camera);
    })();
  }

  function init(scope) {
    [].slice.call((scope || document).querySelectorAll('[data-hero][data-3d="true"]')).forEach(function (hero) {
      if (hero.dataset.sceneReady) return;
      hero.dataset.sceneReady = '1';
      loadThree().then(function () { start(hero); }).catch(function () {
        var c = hero.querySelector('[data-hero-canvas]'); if (c) c.style.display = 'none';
      });
    });
  }
  function boot() { init(); }
  if (document.readyState === 'complete') boot(); else addEventListener('DOMContentLoaded', boot);
  document.addEventListener('shopify:section:load', function (e) { init(e.target); });
})();
