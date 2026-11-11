/* La Galerie Lumineuse — motion & 3D pour sections Shopify
   Pas de dépendance au thème. Three.js n'est chargé que si un hero 3D est présent. */
(function () {
  'use strict';
  if (window.__GL) return;
  window.__GL = true;

  var THREE_URL = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var root = document.documentElement;
  var scripts = {};
  var tempListeners = [];
  var mouse = { x: 0, y: 0 };

  function loadScript(src) {
    return scripts[src] || (scripts[src] = new Promise(function (ok, ko) {
      var s = document.createElement('script');
      s.src = src; s.async = true; s.onload = ok; s.onerror = ko;
      document.head.appendChild(s);
    }));
  }

  /* ---------- Température de couleur (Kelvin → RGB) ---------- */
  function kelvin(k) {
    var t = k / 100, r, g, b;
    r = t <= 66 ? 255 : 329.698727446 * Math.pow(t - 60, -0.1332047592);
    g = t <= 66 ? 99.4708025861 * Math.log(t) - 161.1195681661 : 288.1221695283 * Math.pow(t - 60, -0.0755148492);
    b = t >= 66 ? 255 : (t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307);
    var c = function (v) { return Math.max(0, Math.min(255, Math.round(v))); };
    return { r: c(r), g: c(g), b: c(b) };
  }
  function setTemp(k) {
    var c = kelvin(k);
    var hex = '#' + [c.r, c.g, c.b].map(function (v) { return v.toString(16).padStart(2, '0'); }).join('');
    root.style.setProperty('--gl-glow', hex);
    root.style.setProperty('--gl-glow-soft', 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',.18)');
    tempListeners.forEach(function (f) { f(c); });
  }

  addEventListener('pointermove', function (e) {
    mouse.x = e.clientX / innerWidth * 2 - 1;
    mouse.y = e.clientY / innerHeight * 2 - 1;
  }, { passive: true });

  /* ---------- Révélation au scroll ---------- */
  var io = 'IntersectionObserver' in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -10% 0px', threshold: 0.05 }) : null;

  function reveal(scope) {
    scope.querySelectorAll('.gl-rv').forEach(function (el) {
      if (io) io.observe(el); else el.classList.add('is-in');
    });
  }

  /* ---------- Compteurs ---------- */
  function counters(scope) {
    scope.querySelectorAll('[data-gl-counter]').forEach(function (b) {
      var n = parseFloat(b.dataset.n) || 0, s = b.dataset.s || '';
      if (reduce || !io) { b.textContent = n + s; return; }
      var cio = new IntersectionObserver(function (en) {
        if (!en[0].isIntersecting) return;
        cio.disconnect();
        var t0 = performance.now(), d = 1800;
        (function tick(t) {
          var p = Math.min(1, (t - t0) / d), e = 1 - Math.pow(1 - p, 3);
          b.textContent = Math.round(n * e) + s;
          if (p < 1) requestAnimationFrame(tick);
        })(t0);
      }, { threshold: 0.6 });
      cio.observe(b);
    });
  }

  /* ---------- Manifeste : mots allumés au scroll ---------- */
  var manifestos = [];
  function manifesto(scope) {
    scope.querySelectorAll('[data-gl-manifesto]').forEach(function (el) {
      if (el.dataset.ready) return;
      el.dataset.ready = '1';
      el.setAttribute('aria-label', el.textContent.trim());
      el.innerHTML = el.textContent.trim().split(/\s+/).map(function (w) {
        return '<span class="gl-w" aria-hidden="true">' + w + '</span>';
      }).join(' ');
      manifestos.push(el);
    });
    updateScroll();
  }

  /* ---------- Parallaxe + manifeste (un seul listener scroll) ---------- */
  var heroes = [], ticking = false;
  function updateScroll() {
    ticking = false;
    manifestos = manifestos.filter(function (m) { return document.contains(m); });
    manifestos.forEach(function (el) {
      var words = el.querySelectorAll('.gl-w'), r = el.getBoundingClientRect(), vh = innerHeight;
      var p = Math.min(1, Math.max(0, (vh * .85 - r.top) / (r.height + vh * .35)));
      var n = Math.round(p * words.length);
      words.forEach(function (w, i) { w.classList.toggle('lit', i < n); });
    });
    if (!reduce) {
      document.querySelectorAll('.gl-room img').forEach(function (img) {
        var r = img.parentNode.getBoundingClientRect();
        if (r.bottom < 0 || r.top > innerHeight) return;
        var p = (r.top + r.height / 2 - innerHeight / 2) / innerHeight;
        img.style.transform = 'translate3d(0,' + (p * -40).toFixed(1) + 'px,0)';
      });
    }
    heroes = heroes.filter(function (h) { return document.contains(h.el); });
    heroes.forEach(function (h) {
      h.scrollP = Math.min(1, Math.max(0, -h.el.getBoundingClientRect().top / (h.el.offsetHeight * .9)));
      h.wrap.style.opacity = 1 - Math.min(1, h.scrollP * 1.25);
    });
  }
  addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(updateScroll); }
  }, { passive: true });
  addEventListener('resize', updateScroll);

  /* ---------- Collection : filtres + inclinaison 3D ---------- */
  function collections(scope) {
    scope.querySelectorAll('[data-gl-grid]').forEach(function (sec) {
      if (sec.dataset.ready) return;
      sec.dataset.ready = '1';
      var grid = sec.querySelector('.gl-grid'), chips = sec.querySelectorAll('.gl-chip');

      chips.forEach(function (chip) {
        chip.addEventListener('click', function () {
          chips.forEach(function (c) { c.classList.toggle('on', c === chip); c.setAttribute('aria-selected', c === chip); });
          var type = chip.dataset.type, i = 0;
          grid.querySelectorAll('.gl-card').forEach(function (card) {
            var show = !type || card.dataset.type === type;
            card.hidden = !show;
            if (show && !reduce) {
              card.animate([{ opacity: 0, transform: 'translateY(30px)' }, { opacity: 1, transform: 'none' }],
                { duration: 700, delay: (i++) * 50, easing: 'cubic-bezier(.22,1,.36,1)', fill: 'backwards' });
            }
          });
        });
      });

      if (matchMedia('(hover:hover)').matches && !reduce) {
        grid.addEventListener('mousemove', function (e) {
          var c = e.target.closest('.gl-card'); if (!c) return;
          var r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
          c.style.setProperty('--mx', x * 100 + '%'); c.style.setProperty('--my', y * 100 + '%');
          c.style.transform = 'perspective(900px) rotateY(' + ((x - .5) * 10) + 'deg) rotateX(' + ((.5 - y) * 10) + 'deg) translateY(-4px)';
        });
        grid.addEventListener('mouseout', function (e) {
          var c = e.target.closest('.gl-card');
          if (c && !c.contains(e.relatedTarget)) c.style.transform = '';
        });
      }
    });
  }

  /* ---------- Hero 3D ---------- */
  function haloTexture(THREE) {
    var c = document.createElement('canvas'); c.width = c.height = 256;
    var g = c.getContext('2d'), gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(.18, 'rgba(255,255,255,.55)');
    gr.addColorStop(.5, 'rgba(255,255,255,.12)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    return new THREE.CanvasTexture(c);
  }

  function scene3d(hero, state) {
    var THREE = window.THREE, canvas = hero.querySelector('.gl-canvas');
    var gl; try { gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl'); } catch (e) {}
    if (!THREE || !gl) { canvas.style.display = 'none'; return; }

    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    var scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x080605, .045);
    var camera = new THREE.PerspectiveCamera(42, 1, .1, 100);
    camera.position.set(0, 0, 12);
    scene.add(new THREE.AmbientLight(0xffffff, .12));

    var HT = haloTexture(THREE), group = new THREE.Group(), lamps = [];
    scene.add(group);
    [[-3.2, -.4, .9, 0], [0, -1.6, 1.25, 1.6], [3.2, .3, .75, 3.1], [1.7, 2.1, .45, 4.4], [-1.7, 1.6, .55, 5.2]].forEach(function (d) {
      var piv = new THREE.Group(); piv.position.set(d[0], 9, 0); group.add(piv);
      var len = 9 - d[1];
      var cable = new THREE.Mesh(new THREE.CylinderGeometry(.012, .012, len, 6), new THREE.MeshBasicMaterial({ color: 0x2a2520 }));
      cable.position.y = -len / 2; piv.add(cable);
      var cap = new THREE.Mesh(new THREE.CylinderGeometry(d[2] * .22, d[2] * .28, d[2] * .35, 24), new THREE.MeshStandardMaterial({ color: 0x16130f, metalness: .9, roughness: .3 }));
      cap.position.y = -len + d[2] * .95; piv.add(cap);
      var mat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffb55c, emissiveIntensity: 1.6, roughness: .35 });
      var bulb = new THREE.Mesh(new THREE.SphereGeometry(d[2], 48, 48), mat);
      bulb.position.y = -len; piv.add(bulb);
      var light = new THREE.PointLight(0xffb55c, 2.2, 16, 1.6);
      light.position.copy(bulb.position); piv.add(light);
      var sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: HT, color: 0xffb55c, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: .85 }));
      sp.scale.setScalar(d[2] * 7); sp.position.copy(bulb.position); piv.add(sp);
      lamps.push({ piv: piv, mat: mat, light: light, sp: sp, ph: d[3], base: d[2] });
    });

    var N = 380, pos = new Float32Array(N * 3), spd = [];
    for (var i = 0; i < N; i++) {
      pos[i * 3] = (Math.random() - .5) * 16; pos[i * 3 + 1] = (Math.random() - .5) * 10; pos[i * 3 + 2] = (Math.random() - .5) * 8;
      spd.push(.1 + Math.random() * .3);
    }
    var pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    var pm = new THREE.PointsMaterial({ color: 0xffb55c, size: .035, transparent: true, opacity: .65, blending: THREE.AdditiveBlending, depthWrite: false });
    scene.add(new THREE.Points(pg, pm));

    tempListeners.push(function (c) {
      var col = new THREE.Color(c.r / 255, c.g / 255, c.b / 255);
      lamps.forEach(function (l) { l.mat.emissive.copy(col); l.light.color.copy(col); l.sp.material.color.copy(col); });
      pm.color.copy(col);
    });
    setTemp(state.k);

    function resize() {
      var w = hero.clientWidth, h = hero.clientHeight, m = w < 860;
      renderer.setSize(w, h, false);
      camera.aspect = w / h; camera.fov = m ? 58 : 42;
      group.position.set(m ? 0 : 2.2, m ? -3.2 : 0, 0); group.scale.setScalar(m ? .75 : 1);
      camera.updateProjectionMatrix();
    }
    addEventListener('resize', resize); resize();

    var vis = true, sm = { x: 0, y: 0 }, clock = new THREE.Clock();
    if ('IntersectionObserver' in window) new IntersectionObserver(function (e) { vis = e[0].isIntersecting; }).observe(hero);

    (function loop() {
      if (!document.contains(hero)) { renderer.dispose(); removeEventListener('resize', resize); return; }
      requestAnimationFrame(loop);
      if (!vis) return;
      var t = reduce ? 0 : clock.getElapsedTime(), sp = state.scrollP || 0;
      sm.x += (mouse.x - sm.x) * .05; sm.y += (mouse.y - sm.y) * .05;
      lamps.forEach(function (l) {
        l.piv.rotation.z = Math.sin(t * .6 + l.ph) * .045 + sm.x * .03;
        l.piv.rotation.x = Math.cos(t * .5 + l.ph) * .02;
        var pulse = 1 + Math.sin(t * 1.3 + l.ph) * .04;
        l.light.intensity = 2.2 * pulse * (1 - sp * .7);
        l.sp.scale.setScalar(l.base * 7 * pulse);
        l.sp.material.opacity = .85 * (1 - sp);
      });
      group.rotation.y = sm.x * .25; group.rotation.x = -sm.y * .1;
      var a = pg.attributes.position.array;
      for (var i = 0; i < N; i++) { a[i * 3 + 1] += spd[i] * .004; if (a[i * 3 + 1] > 5) a[i * 3 + 1] = -5; a[i * 3] += Math.sin(t + i) * .0008; }
      pg.attributes.position.needsUpdate = true;
      camera.position.z = 12 + sp * 4;
      renderer.render(scene, camera);
    })();
  }

  function heroes3d(scope) {
    scope.querySelectorAll('[data-gl-hero]').forEach(function (hero) {
      if (hero.dataset.ready) return;
      hero.dataset.ready = '1';
      var state = { k: +hero.dataset.kelvin || 3000, scrollP: 0 };
      var wrap = hero.querySelector('.gl-wrap');
      heroes.push({ el: hero, wrap: wrap, get scrollP() { return state.scrollP; }, set scrollP(v) { state.scrollP = v; } });
      requestAnimationFrame(function () { hero.classList.add('is-in'); });

      var range = hero.querySelector('.gl-temp input'), out = hero.querySelector('.gl-temp output');
      function sync(k) { state.k = k; if (out) out.textContent = k + ' K'; setTemp(k); }
      if (range) range.addEventListener('input', function () { sync(+range.value); });
      sync(state.k);

      if (hero.dataset.halo === 'true' && matchMedia('(hover:hover)').matches) {
        var h = document.createElement('div'); h.className = 'gl-halo'; hero.appendChild(h);
        addEventListener('pointermove', function (e) {
          h.classList.add('on'); h.style.transform = 'translate(' + e.clientX + 'px,' + e.clientY + 'px)';
        }, { passive: true });
      }

      if (hero.dataset.canvas === 'true') {
        loadScript(THREE_URL).then(function () { scene3d(hero, state); }).catch(function () {
          var c = hero.querySelector('.gl-canvas'); if (c) c.style.display = 'none';
        });
      }
    });
  }

  function init(scope) {
    scope = scope || document;
    heroes3d(scope); reveal(scope); counters(scope); manifesto(scope); collections(scope); updateScroll();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { init(); });
  else init();

  /* éditeur de thème : réinitialise la section modifiée */
  document.addEventListener('shopify:section:load', function (e) { init(e.target); });
})();
