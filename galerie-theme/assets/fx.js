/* Galerie Lumineuse — effets cinéma globaux : curseur, son, bandeau cinétique, aperçu des lignes géantes, braises, film, aimant. */
(function () {
  'use strict';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches, fine = matchMedia('(hover:hover)').matches;
  var clamp = function (v, a, b) { return Math.max(a, Math.min(b, v)); };
  var $$ = function (s, c) { return [].slice.call((c || document).querySelectorAll(s)); };

  /* curseur */
  var cur = document.querySelector('[data-fx-cur]'), cx = 0, cy = 0, tx = 0, ty = 0, cr = false, fl = null;
  function fl_el() { if (!fl) { fl = document.createElement('div'); fl.className = 'fx-fl'; fl.setAttribute('aria-hidden', 'true'); document.body.appendChild(fl); } return fl; }
  function cm() { cx += (tx - cx) * .25; cy += (ty - cy) * .25; if (cur) cur.style.transform = 'translate3d(' + cx.toFixed(1) + 'px,' + cy.toFixed(1) + 'px,0)'; if (fl) fl.style.transform = 'translate3d(' + (cx + 26).toFixed(1) + 'px,' + (cy - 100).toFixed(1) + 'px,0)'; if (Math.abs(tx - cx) + Math.abs(ty - cy) > .4) requestAnimationFrame(cm); else cr = false; }
  if (fine) {
    addEventListener('pointermove', function (e) { tx = e.clientX; ty = e.clientY; if (cur) cur.classList.add('on'); if (!cr) { cr = true; requestAnimationFrame(cm); } }, { passive: true });
    if (cur) {
      document.documentElement.classList.add('fx-hc');
      document.addEventListener('pointerover', function (e) { cur.classList.toggle('big', !!(e.target.closest && e.target.closest('a,button,label,[role=tab]'))); });
    }
  }
  /* aimant sur les boutons */
  function mag() { if (!fine || reduce) return; $$('[data-mag]').forEach(function (b) { if (b.__m) return; b.__m = 1; b.addEventListener('pointermove', function (e) { var r = b.getBoundingClientRect(); b.style.transform = 'translate(' + ((e.clientX - r.left - r.width / 2) * .25).toFixed(1) + 'px,' + ((e.clientY - r.top - r.height / 2) * .35).toFixed(1) + 'px)'; }); b.addEventListener('pointerleave', function () { b.style.transform = ''; }); }); }
  /* aperçu au survol des lignes géantes */
  function giant() {
    $$('[data-gr]').forEach(function (r) {
      if (r.__g) return; r.__g = 1;
      r.addEventListener('pointerenter', function () { if (!fine || !r.dataset.img) return; var f = fl_el(); f.innerHTML = '<img alt="" src="' + r.dataset.img + '"><b></b><span></span>'; f.querySelector('b').textContent = r.dataset.name; f.querySelector('span').textContent = r.dataset.price; f.classList.add('on'); if (!cr) { cr = true; requestAnimationFrame(cm); } });
      r.addEventListener('pointerleave', function () { if (fl) fl.classList.remove('on'); });
    });
  }
  /* bandeau cinétique : suit le défilement, s'incline avec la vitesse */
  var bands = [], lastY = scrollY, vel = 0;
  function bandInit() { bands = $$('[data-band]'); }
  function bandTick() {
    var y = scrollY; vel += ((y - lastY) - vel) * .3; lastY = y;
    bands.forEach(function (b) { var r = b.parentNode.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight) return; var x = -((y * .35) % Math.max(1, b.scrollWidth / 2)); b.style.transform = 'translateX(' + x.toFixed(1) + 'px) skewX(' + clamp(-vel * .12, -14, 14).toFixed(2) + 'deg)'; });
  }
  if (!reduce) addEventListener('scroll', bandTick, { passive: true });
  /* braises */
  function embers() {
    $$('[data-embers]').forEach(function (c) {
      if (c.__e) return; c.__e = 1; var x = c.getContext('2d'), W = 0, H = 0, E = [], on = false, run = false;
      for (var j = 0; j < 100; j++) E.push({ x: Math.random(), y: Math.random(), s: .6 + Math.random() * 2.4, v: .00006 + Math.random() * .0002, p: Math.random() * 6.28, a: .2 + Math.random() * .7 });
      function f(t) { if (!on) { run = false; return; } var w = c.clientWidth, h = c.clientHeight; if (w !== W || h !== H) { W = c.width = w; H = c.height = h; } x.clearRect(0, 0, W, H); E.forEach(function (m) { m.y -= m.v * 16; if (m.y < -.02) { m.y = 1.02; m.x = Math.random(); } x.fillStyle = 'rgba(255,181,92,' + (m.a * .75).toFixed(3) + ')'; x.beginPath(); x.arc((m.x + Math.sin(t / 1900 + m.p) * .012) * W, m.y * H, m.s * (W / 1000 + .7), 0, 6.283); x.fill(); }); requestAnimationFrame(f); }
      if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { on = es[0].isIntersecting; if (on && !run) { run = true; requestAnimationFrame(f); } }).observe(c);
    });
  }
  /* film vertical */
  function film() {
    $$('[data-phone]').forEach(function (ph) {
      if (ph.__f) return; ph.__f = 1; var v = ph.querySelector('video');
      if (v && 'IntersectionObserver' in window) new IntersectionObserver(function (es) { if (es[0].isIntersecting) { var p = v.play(); if (p && p.catch) p.catch(function () {}); } else v.pause(); }, { threshold: .25 }).observe(v);
      ph.addEventListener('pointermove', function (e) { if (!fine || reduce) return; var r = ph.getBoundingClientRect(); ph.style.setProperty('--ry', (((e.clientX - r.left) / r.width - .5) * 16).toFixed(1) + 'deg'); ph.style.setProperty('--rx', (-((e.clientY - r.top) / r.height - .5) * 12).toFixed(1) + 'deg'); });
      ph.addEventListener('pointerleave', function () { ph.style.setProperty('--ry', '0deg'); ph.style.setProperty('--rx', '0deg'); });
    });
  }
  /* ambiance de la galerie produit */
  function amb() {
    $$('[data-amb]').forEach(function (b) { if (b.__a) return; b.__a = 1; b.addEventListener('click', function () { var g = b.closest('.gal'); var dim = g.classList.toggle('dim'); b.setAttribute('aria-pressed', String(dim)); b.querySelector('span').textContent = dim ? 'Allumer' : 'Éteindre'; }); });
  }
  /* son : nappe chaude qui suit la lumière + clic d'interrupteur (uniquement après action de l'utilisateur) */
  var AC = null, padG = null, on = false, level = 0, btn = document.querySelector('[data-fx-snd]');
  function startSound() {
    try {
      AC = AC || new (window.AudioContext || window.webkitAudioContext)(); AC.resume();
      if (!padG) { padG = AC.createGain(); padG.gain.value = 0; var lp = AC.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 700; padG.connect(lp); lp.connect(AC.destination); [110, 164.8, 220.4, 277.2].forEach(function (f, i) { var o = AC.createOscillator(); o.type = i ? 'triangle' : 'sine'; o.frequency.value = f; var g = AC.createGain(); g.gain.value = [.5, .3, .2, .12][i]; o.connect(g); g.connect(padG); o.start(); }); }
      on = true;
    } catch (e) { on = false; }
  }
  function click() { if (!on || !AC) return; var t = AC.currentTime, o = AC.createOscillator(), g = AC.createGain(); o.type = 'sine'; o.frequency.setValueAtTime(1800, t); o.frequency.exponentialRampToValueAtTime(220, t + .15); g.gain.setValueAtTime(.25, t); g.gain.exponentialRampToValueAtTime(.001, t + .25); o.connect(g); g.connect(AC.destination); o.start(t); o.stop(t + .3); }
  if (btn) btn.addEventListener('click', function () { if (on) { on = false; if (padG) padG.gain.value = 0; btn.setAttribute('aria-pressed', 'false'); } else { startSound(); btn.setAttribute('aria-pressed', String(on)); } });
  window.addEventListener('lt:light', function (e) { level = e.detail.level; if (on && padG) padG.gain.value = .05 + .2 * level; });
  window.addEventListener('lt:ignite', click);

  function boot() { mag(); giant(); bandInit(); embers(); film(); amb(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  document.addEventListener('shopify:section:load', boot);
})();
