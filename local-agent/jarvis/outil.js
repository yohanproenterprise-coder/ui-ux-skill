// Fenêtre d'un seul outil photo (Améliorer une photo, Améliorer un dossier, Gomme magique, Mise en scène).
// Réutilise le Studio : on n'affiche que les onglets utiles à l'outil.
(() => {
  const T = window.TOOL;
  const $ = s => document.querySelector(s);
  const root = $("#studio");
  document.title = T.title;

  window.openStudio();
  new MutationObserver(() => { if (!root.classList.contains("open")) root.classList.add("open"); })
    .observe(root, { attributes: true, attributeFilter: ["class"] });
  $("#st-close").remove();
  root.querySelector(".st-top h2").firstChild.nextSibling.textContent = T.title;
  setInterval(() => fetch("/ping").catch(() => {}), 30000);

  if (T.id === "dossier") {
    // fenêtre entièrement consacrée aux dossiers : la fenêtre de choix reste ouverte
    for (const id of ["#st-open", "#st-undo", "#st-redo", "#st-compare", "#st-reset"]) { const e = $(id); if (e) e.style.display = "none"; }
    root.querySelector(".st-body").style.visibility = "hidden";
    $("#st-batch-close").style.display = "none";
    $("#st-batch-open").click();
    return;
  }

  const tabs = [...root.querySelectorAll(".st-tabs button")];
  tabs.forEach(b => { if (!T.tabs.includes(b.dataset.tab)) b.style.display = "none"; });
  const go = t => root.querySelector(`.st-tabs [data-tab="${t}"]`).click();
  go(T.start);
  // si le Studio bascule vers un onglet absent de cet outil (ex. après « Valider la mise en scène »),
  // on va à l'étape suivante logique : l'export
  new MutationObserver(() => {
    const on = tabs.find(b => b.classList.contains("on"));
    if (on && !T.tabs.includes(on.dataset.tab)) go(T.tabs.includes("export") ? "export" : T.start);
  }).observe(root.querySelector(".st-tabs"), { attributes: true, subtree: true, attributeFilter: ["class"] });
})();
