/* Galerie Lumineuse — JavaScript du thème
   Panier latéral (AJAX), fiche produit (variantes, galerie, barre collante),
   recherche prédictive, filtres, animations, température de lumière. */
(function () {
  'use strict';

  var T = window.theme || { routes: {}, currency: 'EUR', locale: 'fr' };
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return [].slice.call((r || document).querySelectorAll(s)); };
  var root = document.documentElement;

  /* ------------------------------------------------------------
     API publique (utilisée par la scène 3D)
  ------------------------------------------------------------ */
  var tempListeners = [];
  var GL = (window.GL = {
    onTemp: function (fn) { tempListeners.push(fn); },
    setTemp: setTemp
  });

  function kelvin(k) {
    var t = k / 100, r, g, b;
    r = t <= 66 ? 255 : 329.698727446 * Math.pow(t - 60, -0.1332047592);
    g = t <= 66 ? 99.4708025861 * Math.log(t) - 161.1195681661 : 288.1221695283 * Math.pow(t - 60, -0.0755148492);
    b = t >= 66 ? 255 : (t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307);
    var c = function (v) { return Math.max(0, Math.min(255, Math.round(v))); };
    return { r: c(r), g: c(g), b: c(b) };
  }

  var glideId;
  function setTemp(k) {
    k = Math.max(2200, Math.min(6500, k));
    var c = kelvin(k);
    var hex = '#' + [c.r, c.g, c.b].map(function (v) { return v.toString(16).padStart(2, '0'); }).join('');
    root.style.setProperty('--accent', hex);
    root.style.setProperty('--accent-soft', 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',.18)');
    $$('[data-k-range]').forEach(function (r) { r.value = k; });
    $$('[data-k-out]').forEach(function (o) { o.textContent = Math.round(k / 50) * 50 + ' K'; });
    $$('[data-set-kelvin]').forEach(function (t) { t.classList.toggle('on', Math.abs(+t.dataset.setKelvin - k) < 350); });
    tempListeners.forEach(function (f) { f(c); });
  }
  function glideTemp(to) {
    if (reduce) { setTemp(to); return; }
    cancelAnimationFrame(glideId);
    var r = $('[data-k-range]');
    var from = r ? +r.value : 3000, t0 = performance.now();
    (function step(t) {
      var p = Math.min(1, (t - t0) / 800), e = 1 - Math.pow(1 - p, 3);
      setTemp(from + (to - from) * e);
      if (p < 1) glideId = requestAnimationFrame(step);
    })(t0);
  }
  document.addEventListener('input', function (e) {
    if (e.target.matches('[data-k-range]')) { cancelAnimationFrame(glideId); setTemp(+e.target.value); }
  });

  /* ------------------------------------------------------------
     Utilitaires
  ------------------------------------------------------------ */
  function lock(on) { document.body.classList.toggle('lock', on); }
  function bump() {
    $$('[data-cart-count]').forEach(function (c) { c.classList.remove('bump'); void c.offsetWidth; c.classList.add('bump'); });
  }
  function json(url, opts) {
    return fetch(url, opts).then(function (r) {
      return r.json().then(function (d) { if (!r.ok) throw d; return d; });
    });
  }

  /* ------------------------------------------------------------
     Panier latéral
  ------------------------------------------------------------ */
  var lastFocus = null;
  function drawer() { return $('[data-drawer]'); }
  function openCart() {
    var d = drawer(); if (!d) return;
    lastFocus = document.activeElement;
    d.classList.add('open'); d.setAttribute('aria-hidden', 'false');
    $('[data-cart-ov]').classList.add('open'); lock(true);
    var c = $('[data-close-cart]', d); if (c) c.focus();
  }
  function closeAll() {
    var d = drawer();
    if (d) { d.classList.remove('open'); d.setAttribute('aria-hidden', 'true'); }
    $$('[data-ov]').forEach(function (o) { o.classList.remove('open'); });
    var m = $('[data-mmenu]'); if (m) { m.classList.remove('open'); m.setAttribute('aria-hidden', 'true'); }
    var s = $('[data-search]'); if (s) { s.classList.remove('open'); s.setAttribute('aria-hidden', 'true'); }
    lock(false);
    if (lastFocus) { try { lastFocus.focus(); } catch (e) {} lastFocus = null; }
  }
  addEventListener('keydown', function (e) { if (e.key === 'Escape') closeAll(); });

  function applyCart(sections) {
    var html = sections && sections['cart-drawer'];
    if (!html) return refreshCart();
    var doc = new DOMParser().parseFromString(html, 'text/html');
    var next = $('[data-drawer-inner]', doc), cur = $('[data-drawer-inner]');
    if (next && cur) cur.innerHTML = next.innerHTML;
    var q = $('[data-cart-qty]', doc);
    if (q) $$('[data-cart-count]').forEach(function (c) { c.textContent = q.textContent; });
  }
  function refreshCart() {
    return json(T.routes.cart + '?sections=cart-drawer').then(applyCart);
  }

  function addItems(items) {
    return json(T.routes.cartAdd, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ items: items, sections: 'cart-drawer' })
    }).then(function (res) { applyCart(res.sections); bump(); openCart(); return res; });
  }

  function changeLine(line, qty) {
    return json(T.routes.cartChange, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ line: line, quantity: qty, sections: 'cart-drawer' })
    }).then(function (res) { applyCart(res.sections); });
  }

  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t.closest('[data-open-cart]')) { e.preventDefault(); openCart(); return; }
    if (t.closest('[data-close-cart]') || t.closest('[data-cart-ov]')) { closeAll(); return; }

    var ch = t.closest('[data-change]');
    if (ch) { changeLine(+ch.dataset.line, +ch.dataset.qty); return; }

    var qa = t.closest('[data-quick-add]');
    if (qa) {
      e.preventDefault();
      var old = qa.textContent; qa.disabled = true; qa.textContent = '…';
      addItems([{ id: +qa.dataset.variantId, quantity: 1 }])
        .then(function () { qa.textContent = 'Ajouté ✓'; })
        .catch(function (err) { qa.textContent = (err && err.description) || 'Indisponible'; })
        .then(function () { setTimeout(function () { qa.disabled = false; qa.textContent = old; }, 1600); });
    }

    if (t.closest('[data-open-menu]')) { var m = $('[data-mmenu]'); m.classList.add('open'); m.setAttribute('aria-hidden', 'false'); lock(true); }
    if (t.closest('[data-close-menu]') || (t.closest('[data-mmenu] a'))) { closeAll(); }

    if (t.closest('[data-open-search]')) {
      var s = $('[data-search]'); s.classList.add('open'); s.setAttribute('aria-hidden', 'false'); lock(true);
      setTimeout(function () { var i = $('[data-search-input]'); if (i) i.focus(); }, 80);
    }
    if (t.closest('[data-close-search]')) closeAll();

    var k = t.closest('[data-set-kelvin]');
    if (k) glideTemp(+k.dataset.setKelvin);

    if (t.closest('[data-toggle-filters]')) { var f = $('[data-facets]'); if (f) f.classList.toggle('open'); }
  });

  /* ------------------------------------------------------------
     Recherche prédictive
  ------------------------------------------------------------ */
  var sTimer;
  document.addEventListener('input', function (e) {
    if (!e.target.matches('[data-search-input]') || !T.routes.predictive) return;
    var q = e.target.value.trim(), box = $('[data-search-results]');
    clearTimeout(sTimer);
    if (q.length < 2) { box.innerHTML = ''; return; }
    sTimer = setTimeout(function () {
      var url = T.routes.predictive + '.json?q=' + encodeURIComponent(q) + '&resources[type]=product&resources[limit]=6';
      json(url).then(function (d) {
        var list = (d.resources && d.resources.results && d.resources.results.products) || [];
        var fmt = function (p) { return p; };
        box.innerHTML = list.length ? list.map(function (p) {
          var img = p.featured_image && p.featured_image.url ? '<img src="' + p.featured_image.url + '&width=128" alt="" loading="lazy">' : '';
          var price = new Intl.NumberFormat(T.locale, { style: 'currency', currency: T.currency, maximumFractionDigits: 0 }).format(parseFloat(p.price));
          return '<a class="sres" href="' + p.url + '">' + img + '<div><b>' + fmt(p.title) + '</b><span>' + price + '</span></div></a>';
        }).join('') : '<p class="sub">Aucun résultat.</p>';
      }).catch(function () { box.innerHTML = ''; });
    }, 220);
  });

  /* ------------------------------------------------------------
     En-tête, annonces, halo
  ------------------------------------------------------------ */
  function initHeader() {
    var h = $('[data-header]');
    if (h && !h.dataset.ready) {
      h.dataset.ready = '1';
      var on = function () { h.classList.toggle('solid', scrollY > 40); };
      addEventListener('scroll', on, { passive: true }); on();
    }
    var a = $('[data-announce]');
    if (a && !a.dataset.ready) {
      a.dataset.ready = '1';
      var msgs = $$('.announce-msg', a), i = 0;
      if (msgs.length > 1 && !reduce) setInterval(function () {
        msgs[i].classList.remove('on'); i = (i + 1) % msgs.length; msgs[i].classList.add('on');
      }, 5000);
    }
  }
  var halo = $('[data-halo]');
  if (halo) addEventListener('pointermove', function (e) {
    halo.classList.add('on'); halo.style.transform = 'translate(' + e.clientX + 'px,' + e.clientY + 'px)';
  }, { passive: true });

  /* ------------------------------------------------------------
     Révélations + inclinaison 3D des cartes
  ------------------------------------------------------------ */
  var io = 'IntersectionObserver' in window ? new IntersectionObserver(function (es) {
    es.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 }) : null;
  function initReveal(scope) {
    $$('.rv', scope).forEach(function (el) { if (io) io.observe(el); else el.classList.add('in'); });
    var hero = $('[data-hero]', scope); if (hero) requestAnimationFrame(function () { hero.classList.add('in'); });
  }
  if (matchMedia('(hover:hover)').matches && !reduce) {
    document.addEventListener('mousemove', function (e) {
      var c = e.target.closest && e.target.closest('[data-tilt]'); if (!c) return;
      var r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      c.style.setProperty('--mx', x * 100 + '%'); c.style.setProperty('--my', y * 100 + '%');
      c.style.transform = 'perspective(900px) rotateY(' + ((x - .5) * 8) + 'deg) rotateX(' + ((.5 - y) * 8) + 'deg) translateY(-4px)';
    });
    document.addEventListener('mouseout', function (e) {
      var c = e.target.closest && e.target.closest('[data-tilt]');
      if (c && !c.contains(e.relatedTarget)) c.style.transform = '';
    });
  }

  /* ------------------------------------------------------------
     Filtres de collection (soumission automatique)
  ------------------------------------------------------------ */
  document.addEventListener('change', function (e) {
    if (e.target.matches('[data-auto-submit]')) { var f = e.target.closest('form'); if (f) f.submit(); }
  });

  /* ------------------------------------------------------------
     Fiche produit
  ------------------------------------------------------------ */
  function initProduct(sec) {
    if (sec.dataset.ready) return;
    sec.dataset.ready = '1';
    var dataEl = $('[data-product-json]', sec.parentNode) || $('[data-product-json]');
    if (!dataEl) return;
    var data = JSON.parse(dataEl.textContent), variants = data.variants;
    var form = $('[data-product-form]', sec), idInput = $('[data-variant-id]', sec);
    var priceEl = $('[data-price]', sec), cmpEl = $('[data-compare]', sec), saveEl = $('[data-save]', sec);
    var atc = $('[data-atc]', sec), atcLabel = $('[data-atc-label]', sec), err = $('[data-error]', sec);
    var sticky = $('[data-sticky-atc]'), stickyPrice = $('[data-sticky-price]'), stickyBtn = $('[data-sticky-btn]');
    var qty = $('[data-qty-input]', sec);

    function selected() {
      return $$('[data-option-index]', sec).map(function (fs) {
        var c = $('input:checked', fs); return c ? c.value : null;
      });
    }
    function find(opts) {
      return variants.filter(function (v) { return v.options.every(function (o, i) { return o === opts[i]; }); })[0];
    }
    function showMedia(id) {
      if (!id) return;
      $$('.slide', sec).forEach(function (s) { s.classList.toggle('on', +s.dataset.mediaId === id); });
      $$('[data-thumb]', sec).forEach(function (t) { t.classList.toggle('on', +t.dataset.thumb === id); });
    }
    function update() {
      var opts = selected(), v = find(opts);
      $$('[data-option-index]', sec).forEach(function (fs, i) {
        var lab = $('[data-option-label]', fs); if (lab) lab.textContent = opts[i];
        $$('.oc', fs).forEach(function (lbl) {
          var test = opts.slice(); test[i] = $('input', lbl).value;
          var ok = find(test);
          lbl.classList.toggle('dim', !ok || !ok.available);
        });
      });
      if (!v) {
        if (atc) { atc.disabled = true; atcLabel.textContent = 'Indisponible'; }
        return;
      }
      idInput.value = v.id;
      priceEl.textContent = v.price;
      if (cmpEl) { cmpEl.hidden = !v.compare; cmpEl.textContent = v.compare || ''; }
      if (saveEl) { saveEl.hidden = !v.compare; saveEl.textContent = v.compare ? '-' + v.save + ' %' : ''; }
      if (atc) { atc.disabled = !v.available; atcLabel.textContent = v.available ? 'Ajouter au panier' : 'Épuisé'; }
      if (stickyPrice) stickyPrice.textContent = v.price;
      if (stickyBtn) { stickyBtn.disabled = !v.available; stickyBtn.textContent = v.available ? 'Ajouter au panier' : 'Épuisé'; }
      var dyn = $('[data-dynamic]', sec); if (dyn) dyn.style.display = v.available ? '' : 'none';
      showMedia(v.media);
      var url = new URL(location.href); url.searchParams.set('variant', v.id);
      history.replaceState({}, '', url);
      /* option « température » → la lumière du site s'adapte */
      var fsList = $$('[data-option-index]', sec);
      fsList.forEach(function (fs, i) {
        var name = ($('legend', fs).firstChild.textContent || '').toLowerCase();
        if (/lumi|temp|ampoule/.test(name)) {
          var m = /(\d{4})\s?K/i.exec(opts[i]) || null, k = m ? +m[1] : (/chaud/i.test(opts[i]) ? 3000 : /naturel/i.test(opts[i]) ? 4000 : /froid/i.test(opts[i]) ? 6000 : 0);
          if (k) glideTemp(k);
        }
      });
    }
    sec.addEventListener('change', function (e) { if (e.target.closest('[data-option-index]')) update(); });

    /* galerie */
    sec.addEventListener('click', function (e) {
      var th = e.target.closest('[data-thumb]'); if (th) showMedia(+th.dataset.thumb);
      var st = e.target.closest('[data-qty-step]');
      if (st && qty) qty.value = Math.max(1, Math.min(20, (+qty.value || 1) + +st.dataset.qtyStep));
    });

    /* ajout au panier (AJAX) */
    if (form) form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (err) err.hidden = true;
      var btns = [atc, stickyBtn].filter(Boolean), labels = btns.map(function (b) { return b.textContent; });
      btns.forEach(function (b) { b.disabled = true; });
      if (atcLabel) atcLabel.textContent = 'Ajout…';
      addItems([{ id: +idInput.value, quantity: +(qty ? qty.value : 1) || 1 }])
        .then(function () { if (atcLabel) atcLabel.textContent = 'Ajouté ✓'; })
        .catch(function (er) {
          if (err) { err.textContent = (er && (er.description || er.message)) || 'Impossible d\'ajouter ce produit.'; err.hidden = false; }
        })
        .then(function () {
          setTimeout(function () { btns.forEach(function (b, i) { b.disabled = false; b.textContent = labels[i]; }); update(); }, 1400);
        });
    });

    /* barre « ajouter » collante */
    if (sticky && atc && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (es) {
        var en = es[0], show = !en.isIntersecting && en.boundingClientRect.top < 0;
        sticky.classList.toggle('show', show); sticky.setAttribute('aria-hidden', !show);
        if (stickyBtn) stickyBtn.tabIndex = show ? 0 : -1;
      }).observe(atc);
    }
    update();
  }

  /* produits recommandés (chargés à la demande) */
  function initRecs(el) {
    if (el.dataset.ready) return; el.dataset.ready = '1';
    var load = function () {
      fetch(el.dataset.url).then(function (r) { return r.text(); }).then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var next = $('[data-recs]', doc);
        if (next && next.innerHTML.trim()) { el.innerHTML = next.innerHTML; initReveal(el); }
      }).catch(function () {});
    };
    if ('IntersectionObserver' in window) {
      var o = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { o.disconnect(); load(); } }, { rootMargin: '300px' });
      o.observe(el);
    } else load();
  }

  /* ------------------------------------------------------------
     Initialisation (et éditeur de thème)
  ------------------------------------------------------------ */
  function init(scope) {
    scope = scope || document;
    initHeader(); initReveal(scope);
    $$('[data-product-section]', scope).forEach(initProduct);
    $$('[data-recs]', scope).forEach(initRecs);
    var hero = $('[data-hero]');
    if (hero) setTemp(+hero.dataset.kelvin || 3000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { init(); });
  else init();
  document.addEventListener('shopify:section:load', function (e) { init(e.target); });
  window.addEventListener('pageshow', function (e) { if (e.persisted) refreshCart(); });
})();
