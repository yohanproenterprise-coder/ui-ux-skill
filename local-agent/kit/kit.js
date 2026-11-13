// Photo Studio IA : adapte le Studio de Jarvis en application autonome.
(() => {
  const K = window.KIT || { name: "Photo Studio IA", version: "" };
  const $ = s => document.querySelector(s);
  const root = $("#studio");

  // le Studio est l'application entière : toujours ouvert, pas de bouton « Fermer »
  window.openStudio();
  new MutationObserver(() => { if (!root.classList.contains("open")) root.classList.add("open"); })
    .observe(root, { attributes: true, attributeFilter: ["class"] });
  $("#st-close").remove();
  root.querySelector(".st-top h2").firstChild.nextSibling.textContent = K.name;

  // fonctions de Jarvis absentes du kit (restauration des visages : licence non commerciale ; idées : assistant)
  for (const sel of ["#st-faces", "#st-fstr", "#st-face-msg", "#sc-ideas"]) {
    const e = $(sel); if (!e) continue;
    (e.closest(".st-row") || e).style.display = "none";
  }
  const intro = $("#st-magic") && $("#st-magic").nextElementSibling;
  if (intro) intro.textContent = "Un clic, rien à régler : l'IA nettoie la compression et le bruit, restaure la netteté, " +
    "équilibre lumière et couleurs, et agrandit les petites photos. Maintiens « Avant / après » pour comparer.";
  const facesLabel = [...root.querySelectorAll(".st-label")].find(l => l.textContent.trim() === "Visages");
  if (facesLabel) facesLabel.style.display = "none";

  // signe de vie : l'application se ferme toute seule quand sa fenêtre est fermée
  setInterval(() => fetch("/ping").catch(() => {}), 20000);

  // ------------------------------------------------------- menu ⚙ du kit --
  const gear = document.createElement("button");
  gear.className = "pill"; gear.title = "Carte graphique, licences, à propos";
  gear.innerHTML = '⚙<span class="lbl">Options</span>';
  root.querySelector(".st-top").appendChild(gear);
  const dlg = document.createElement("div");
  dlg.className = "st-modal"; dlg.hidden = true;
  dlg.innerHTML = `<div class="st-modal-box">
    <div class="row" style="display:flex;justify-content:space-between;align-items:center">
      <strong class="title">${K.name} <small style="color:var(--muted)">${K.version}</small></strong>
      <button class="pill" id="kit-close">Fermer</button></div>
    <div class="st-label">Apparence</div>
    <div class="themes">
      <button class="theme-card" data-theme-pick="aurore"><i style="background:linear-gradient(135deg,#120f2e,#3b1d6e 45%,#a0306e 80%,#d9822b)"></i>Aurore<small>sombre, coloré</small></button>
      <button class="theme-card" data-theme-pick="pastel"><i style="background:linear-gradient(135deg,#fdf6ff,#e7dcff 40%,#ffd9e8 75%,#ffe9c7)"></i>Pastel<small>clair, doux</small></button>
      <button class="theme-card" data-theme-pick="epure"><i style="background:linear-gradient(135deg,#0c0d10 50%,#f6f6f8 50%)"></i>Épuré<small>sobre</small></button>
    </div>
    <div id="kit-lic-box" hidden>
      <div class="st-label">Licence</div>
      <div class="st-note" id="kit-lic-state" style="margin-top:0"></div>
      <div id="kit-lic-form" style="display:flex;gap:8px;margin-top:8px">
        <input type="text" id="kit-key" placeholder="Clé de licence reçue par e-mail" autocomplete="off" style="flex:1">
        <button class="st-btn primary" id="kit-activate">Activer</button>
      </div>
      <div class="st-msg" id="kit-lic-msg"></div>
      <a class="st-btn wide" id="kit-buy" target="_blank" rel="noopener" style="text-decoration:none">Acheter une licence</a>
      <button class="st-btn wide" id="kit-deact" hidden>Libérer la licence de ce PC</button>
    </div>
    <div class="st-label">Carte graphique</div>
    <p class="st-note" style="margin-top:0">Fait travailler la puce graphique du PC pour aller plus vite. L'application mesure la
      vitesse et ne l'utilise que si elle est vraiment plus rapide ; au moindre souci, elle revient au processeur.</p>
    <div class="st-note" id="kit-gpu">…</div>
    <div id="kit-gpu-btns" style="margin-top:8px"></div>
    <div class="st-label">Mes photos</div>
    <button class="st-btn wide" id="kit-folder">📂 Ouvrir le dossier des photos enregistrées</button>
    <div class="st-label">Licences</div>
    <p class="st-note" style="margin-top:0">Les intelligences artificielles utilisées sont open source et autorisées en usage commercial.</p>
    <button class="st-btn wide" id="kit-lic">Voir les licences et les auteurs</button>
    <pre id="kit-lic-text" class="st-note" hidden style="white-space:pre-wrap;max-height:30vh;overflow:auto"></pre>
  </div>`;
  root.appendChild(dlg);
  const markTheme = () => dlg.querySelectorAll("[data-theme-pick]").forEach(b =>
    b.classList.toggle("on", b.dataset.themePick === document.documentElement.dataset.theme));
  dlg.addEventListener("click", e => {
    const b = e.target.closest("[data-theme-pick]"); if (!b) return;
    window.applyTheme(b.dataset.themePick);
    try { localStorage.setItem("jarvis-theme", b.dataset.themePick); } catch (x) {}
    markTheme();
  });
  gear.onclick = () => { dlg.hidden = false; markTheme(); loadGpu(); };
  dlg.querySelector("#kit-close").onclick = () => { dlg.hidden = true; };
  dlg.querySelector("#kit-folder").onclick = () =>
    fetch("/open_folder", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  dlg.querySelector("#kit-lic").onclick = async () => {
    const pre = dlg.querySelector("#kit-lic-text");
    pre.textContent = await (await fetch("/licences")).text(); pre.hidden = !pre.hidden;
  };

  const TEXT = {
    unsupported: "Disponible uniquement sous Windows.",
    absent: "Non installée : l'application utilise le processeur.",
    installing: "Installation en cours…",
    restart: "Installée : redémarrage nécessaire.",
    testing: "Mesure de la vitesse en cours…",
    off: "Désactivée : l'application utilise le processeur.",
  };
  async function loadGpu() {
    let g; try { g = (await (await fetch("/ai_status")).json()).gpu; } catch (e) { return; }
    let t = TEXT[g.state] || "";
    if (g.state === "active") t = `⚡ Active : environ ${g.speedup}× plus rapide qu'avec le processeur.`;
    if (g.state === "slower") t = `Pas utilisée : ${g.reason || "pas plus rapide que le processeur"}.`;
    if (g.state === "error") t = "Échec de l'installation : " + (g.error || "");
    if (g.state === "installing" && g.step) t = g.step;
    $("#kit-gpu").textContent = t;
    const btn = (label, a) => `<button class="st-btn" data-a="${a}">${label}</button>`;
    $("#kit-gpu-btns").innerHTML = ["unsupported", "installing"].includes(g.state) ? "" :
      ["absent", "error"].includes(g.state) ? btn("⚡ Installer et activer (≈ 20 Mo)", "install") :
      ["off", "slower"].includes(g.state) ? btn("Réessayer la carte graphique", "on") :
      ["active", "testing"].includes(g.state) ? btn("Désactiver", "off") : "";
    if (["installing", "testing"].includes(g.state) && !dlg.hidden) setTimeout(loadGpu, 2000);
  }
  dlg.addEventListener("click", async e => {
    const a = e.target.dataset && e.target.dataset.a; if (!a) return;
    const r = await (await fetch("/gpu", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: a }) })).json();
    $("#kit-gpu").textContent = r.error || (r.restarting ? "Redémarrage de l'application…" : "C'est noté : appliqué à la fin du dossier en cours.");
    if (!r.restarting) return loadGpu();
    // l'application redémarre : on recharge la page dès qu'elle répond de nouveau
    let pid0 = null; try { pid0 = (await (await fetch("/ping")).json()).pid; } catch (x) {}
    for (let i = 0; i < 300; i++) {
      await new Promise(ok => setTimeout(ok, 1500));
      try { const v = await (await fetch("/ping")).json(); if (v.pid !== pid0) return location.reload(); } catch (x) {}
    }
  });
  // ------------------------------------------------------ licence (Lemon Squeezy) --
  const banner = document.createElement("div");
  banner.style.cssText = "display:none;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;padding:7px 16px;font-size:13px;" +
    "background:var(--grad-soft, var(--accent-soft));border-bottom:1px solid var(--line);color:var(--text)";
  root.insertBefore(banner, root.querySelector(".st-body"));
  const wall = document.createElement("div");
  wall.className = "st-modal"; wall.hidden = true; wall.style.zIndex = 9;
  wall.innerHTML = `<div class="st-modal-box" style="text-align:center">
    <strong class="title">L'essai gratuit est terminé</strong>
    <p class="st-note">Merci d'avoir essayé ${K.name}. Pour continuer à l'utiliser, active ta licence. Elle s'achète une seule fois,
      et les mises à jour sont incluses.</p>
    <div style="display:flex;gap:8px;margin-top:14px"><input type="text" id="wall-key" placeholder="Clé de licence" style="flex:1">
      <button class="st-btn primary" id="wall-activate">Activer</button></div>
    <div class="st-msg" id="wall-msg"></div>
    <a class="st-btn primary wide" id="wall-buy" target="_blank" rel="noopener" style="text-decoration:none">Acheter une licence</a></div>`;
  root.appendChild(wall);
  async function activateKey(key, msgBox) {
    msgBox.style.color = "var(--muted)"; msgBox.textContent = "Vérification de la clé…";
    try {
      const r = await (await fetch("/licence/activate", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }) })).json();
      if (r.error) throw new Error(r.error);
      msgBox.style.color = "var(--ok)"; msgBox.textContent = "Licence activée ✓ Merci pour ton achat !";
      refreshLicence();
    } catch (e) { msgBox.style.color = "var(--err)"; msgBox.textContent = e.message; }
  }
  async function refreshLicence() {
    let L; try { L = await (await fetch("/licence")).json(); } catch (e) { return; }
    $("#kit-lic-box").hidden = !L.enabled;
    if (!L.enabled) return;
    for (const a of [$("#kit-buy"), $("#wall-buy")]) { a.href = L.buy_url || "#"; a.hidden = !L.buy_url || L.licensed; }
    $("#kit-lic-form").style.display = L.licensed ? "none" : "flex";
    $("#kit-deact").hidden = !L.licensed;
    $("#kit-lic-state").textContent = L.licensed ? `Licence active sur ce PC (clé …${L.key_hint}).`
      : L.trial_left > 0 ? `Essai gratuit : encore ${L.trial_left} jour${L.trial_left > 1 ? "s" : ""}.` : "Essai gratuit terminé.";
    banner.style.display = !L.licensed && L.trial_left > 0 ? "flex" : "none";
    banner.innerHTML = `Essai gratuit : encore <strong>${L.trial_left} jour${L.trial_left > 1 ? "s" : ""}</strong>` +
      (L.buy_url ? ` · <a href="${L.buy_url}" target="_blank" rel="noopener" style="color:var(--accent);font-weight:600">Acheter (29 €)</a>` : "") +
      ` · <a href="#" id="banner-act" style="color:var(--accent)">J'ai une clé</a>`;
    const ba = banner.querySelector("#banner-act"); if (ba) ba.onclick = e => { e.preventDefault(); gear.click(); };
    wall.hidden = L.allowed;
  }
  $("#kit-activate").onclick = () => activateKey($("#kit-key").value, $("#kit-lic-msg"));
  $("#wall-activate").onclick = () => activateKey($("#wall-key").value, $("#wall-msg"));
  $("#kit-deact").onclick = async () => {
    await fetch("/licence/deactivate", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    $("#kit-lic-msg").textContent = "Licence libérée : tu peux l'activer sur un autre PC."; refreshLicence();
  };
  refreshLicence();

})();
