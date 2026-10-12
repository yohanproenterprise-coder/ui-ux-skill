/* Galerie Lumineuse — scène « lettres » : le mot est rempli par la photo, il s'allume lettre par lettre,
   on zoome dans une lettre jusqu'à la photo plein cadre, puis iris vers les photos suivantes. */
(function () {
  'use strict';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var clamp = function (v, a, b) { return Math.max(a, Math.min(b, v)); };
  var sm = function (t) { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };

  function splitWords(h) {
    var i = 0;
    function walk(n, out) {
      [].slice.call(n.childNodes).forEach(function (c) {
        if (c.nodeType === 3) {
          c.textContent.split(/(\s+)/).forEach(function (w) {
            if (!w.trim()) { if (w) out.appendChild(document.createTextNode(' ')); return; }
            var s = document.createElement('span'); s.className = 'w'; s.style.setProperty('--i', i++);
            var inner = document.createElement('span'); inner.textContent = w; s.appendChild(inner); out.appendChild(s);
          });
        } else if (c.nodeName === 'EM') { var e = document.createElement('em'); walk(c, e); out.appendChild(e); }
      });
    }
    var o = document.createElement('span'); walk(h, o);
    var label = h.textContent; h.textContent = ''; h.setAttribute('aria-label', label);
    while (o.firstChild) h.appendChild(o.firstChild);
  }

  function init(root) {
    if (root.__lt) return; root.__lt = true;
    var q = function (s) { return root.querySelector(s); };
    var stick = q('.lt-stick'), svg = q('.lt-svg'), ct = q('.lt-ct'), ot = q('.lt-ot'), cr = q('.lt-cr'), ia = q('.lt-ia'), ib = q('.lt-ib'),
        im1 = q('.lt-im1'), im2 = q('.lt-im2'), im3 = q('.lt-im3'), dust = q('.lt-dust'), cap = q('.lt-cap'), tag = q('.lt-tag'),
        shade = q('.lt-shade'), rail = q('.lt-rail i'), pv = q('.lt-pv'), tsp = [].slice.call(ot.querySelectorAll('tspan'));
    var says = [q('.lt-s1'), q('.lt-s2'), q('.lt-s3')];
    var dx = dust.getContext('2d');
    var hasImg = !!im1;
    root.querySelectorAll('[data-split]').forEach(splitWords);

    var word = ct.textContent.replace(/\s/g, ' ');
    var zi = word.search(/[Il]/); if (zi < 0) { zi = Math.floor(word.length / 2); while (zi > 0 && !word[zi].trim()) zi--; }
    var price = pv ? +pv.getAttribute('data-to') || 0 : 0;

    var W = 0, H = 0, fs = 0, tx = 0, ty = 0, gw = 0;
    function layout() {
      W = stick.clientWidth; H = stick.clientHeight; if (!W || !H) return;
      svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
      fs = Math.min(W * .31, H * .62);
      function put() { [ct, ot].forEach(function (t) { t.setAttribute('font-size', fs); t.setAttribute('x', W / 2); t.setAttribute('y', H / 2 + fs * .36); }); }
      put();
      try { var len = ct.getComputedTextLength(); if (len > W * .94) { fs *= W * .94 / len; put(); } } catch (e) {}
      [im1, im2, im3].forEach(function (im) { if (im) { im.setAttribute('width', W); im.setAttribute('height', H); } });
      try { var e = ct.getExtentOfChar(zi); tx = e.x + e.width / 2; ty = e.y + e.height / 2; gw = e.width; } catch (x) { tx = W / 2; ty = H / 2; gw = fs * .22; }
      stick.style.setProperty('--lt-fs', fs + 'px');
      dust.width = W; dust.height = H; kick();
    }
    var M = []; for (var i = 0; i < 120; i++) M.push({ x: Math.random(), y: Math.random(), s: .5 + Math.random() * 2, v: .00005 + Math.random() * .00016, p: Math.random() * 6.28, a: .25 + Math.random() * .75 });

    var p = 0, tgt = 0, t0 = performance.now(), last = t0, run = false, vis = true, counted = false, fired = false;
    function target() {
      if (reduce) return .92;
      var r = root.getBoundingClientRect(), tot = root.offsetHeight - H;
      return clamp(-r.top / Math.max(1, tot), 0, 1);
    }
    function kick() { if (!run && vis) { run = true; last = performance.now(); requestAnimationFrame(frame); } }
    function frame(now) {
      run = false; if (!W) return;
      var t = (now - t0) / 1000, dt = Math.min(.1, (now - last) / 1000); last = now;
      tgt = target(); p += (tgt - p) * (reduce ? 1 : 1 - Math.exp(-dt * 6.5)); if (Math.abs(tgt - p) < .0004) p = tgt;
      var auto = reduce ? 1 : clamp((t - .3) / 2.6, 0, 1);
      tsp.forEach(function (s, i) {
        var raw = clamp((t - .35 - i * .28) / .55, 0, 1), fl = raw > 0 && raw < .85 ? (.5 + .5 * Math.sin(t * 61 + i * 7) * Math.sin(t * 23 + i)) : 1;
        var a = reduce ? 1 : clamp(sm(raw) * fl, 0, 1) * (1 - clamp((p - .1) / .2, 0, 1));
        s.setAttribute('stroke', 'rgba(255,176,84,' + a.toFixed(3) + ')');
      });
      var z = sm(p / .3), S = 1 + z * (Math.max(W, H) / Math.max(8, gw) * 2.4 - 1), tf = 'translate(' + tx + ' ' + ty + ') scale(' + S.toFixed(3) + ') translate(' + (-tx) + ' ' + (-ty) + ')';
      ct.setAttribute('transform', tf); ot.setAttribute('transform', tf); ot.setAttribute('stroke-width', (1.6 / S).toFixed(4));
      cr.setAttribute('cx', tx); cr.setAttribute('cy', ty); cr.setAttribute('r', (sm((z - .45) / .55) * Math.hypot(W, H)).toFixed(1));
      var L = sm((p - .02) / .28), fl2 = L > 0 && L < .9 ? (.85 + .15 * Math.sin(p * 420) * Math.sin(p * 131)) : 1;
      var B = .22 + .14 * auto + .64 * clamp(L * fl2, 0, 1); root.style.setProperty('--lt-b', B.toFixed(3));
      var R = Math.hypot(W, H);
      ia.setAttribute('cx', W * .52); ia.setAttribute('cy', H * .42); ia.setAttribute('r', (sm((p - .55) / .1) * R).toFixed(1));
      ib.setAttribute('cx', W * .5); ib.setAttribute('cy', H * .6); ib.setAttribute('r', (sm((p - .79) / .09) * R).toFixed(1));
      says[0].classList.toggle('on', p > .36 && p < .55); says[1].classList.toggle('on', p > .64 && p < .78);
      var on3 = p > .9; says[2].classList.toggle('on', on3);
      if (pv) {
        if (on3 && !counted) { counted = true; var s0 = performance.now(); (function c(n) { var k = clamp((n - s0) / 900, 0, 1); pv.textContent = Math.round(price * sm(k)); if (k < 1) requestAnimationFrame(c); })(s0); }
        if (!on3 && counted && p < .85) { counted = false; pv.textContent = price; }
      }
      root.style.setProperty('--lt-sh', sm((p - .32) / .08).toFixed(3));
      cap.style.opacity = clamp(1 - p * 10, 0, 1); tag.style.setProperty('--lt-tg', clamp(1 - p * 6, 0, 1).toFixed(3)); rail.style.setProperty('--lt-rp', (p * 100).toFixed(1) + '%');
      window.dispatchEvent(new CustomEvent('lt:light', { detail: { level: clamp(L * fl2, 0, 1) } }));
      if (!fired && p > .03) { fired = true; window.dispatchEvent(new CustomEvent('lt:ignite')); } if (p < .01) fired = false;
      dx.clearRect(0, 0, W, H);
      var dl = clamp((t - 1.2) / 2, 0, 1) * .9 + .1 * L;
      M.forEach(function (m) { m.y -= m.v * 16; if (m.y < -.02) { m.y = 1.02; m.x = Math.random(); } dx.fillStyle = 'rgba(255,190,110,' + (m.a * dl * .7).toFixed(3) + ')'; dx.beginPath(); dx.arc((m.x + Math.sin(t * .5 + m.p) * .014) * W, m.y * H, m.s * (W / 1100 + .6), 0, 6.283); dx.fill(); });
      if (vis) { run = true; requestAnimationFrame(frame); }
    }
    if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { vis = es[0].isIntersecting; if (vis) kick(); }, { rootMargin: '120px' }).observe(root);
    addEventListener('scroll', kick, { passive: true }); addEventListener('resize', layout);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout);
    layout(); setTimeout(layout, 400);
    if ('ResizeObserver' in window) new ResizeObserver(layout).observe(stick);
    root.querySelectorAll('[data-go-buy]').forEach(function (a) { a.addEventListener('click', function (e) { var b = document.getElementById('buy'); if (b) { e.preventDefault(); b.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth' }); } }); });
  }
  function boot() { document.querySelectorAll('[data-letters]').forEach(init); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  document.addEventListener('shopify:section:load', boot);
})();
