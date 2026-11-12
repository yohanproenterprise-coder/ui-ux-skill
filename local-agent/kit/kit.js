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
  root.querySelector(".st-top h2").firstChild.nextSibling.textContent = K.name.toUpperCase();

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
  gear.onclick = () => { dlg.hidden = false; loadGpu(); };
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
})();
