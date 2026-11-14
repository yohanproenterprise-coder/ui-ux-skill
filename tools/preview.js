// Aperçu hors ligne d'une page 3D / animée : les bibliothèques des CDN sont servies depuis vendor/ (utile quand
// les CDN sont inaccessibles, par exemple dans une session cloud). Usage : node tools/preview.js page.html [sortie]
// Produit <sortie>-bureau.png, <sortie>-telephone.png et affiche les erreurs de la page.
const path = require("path");
const { chromium, devices } = require("playwright");
const ROOT = path.resolve(__dirname, "..");
const MAP = [
  [/three@0\.147\.0\/build\/three(\.min)?\.js/, "vendor/three/three.min.js"],
  [/three@0\.147\.0\/examples\/js\/controls\/OrbitControls\.js/, "vendor/three/OrbitControls.js"],
  [/three@0\.147\.0\/examples\/js\/loaders\/GLTFLoader\.js/, "vendor/three/GLTFLoader.js"],
  [/gsap\/3\.12\.5\/gsap\.min\.js/, "vendor/gsap/gsap.min.js"],
  [/gsap\/3\.12\.5\/ScrollTrigger\.min\.js/, "vendor/gsap/ScrollTrigger.min.js"],
];
(async () => {
  const page = path.resolve(process.argv[2]);
  const out = process.argv[3] || page.replace(/\.html?$/, "");
  const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
  for (const [label, opts] of [["bureau", { viewport: { width: 1440, height: 900 } }], ["telephone", devices["iPhone 13"]]]) {
    const ctx = await browser.newContext(opts);
    await ctx.route("**/*", route => {
      const url = route.request().url();
      const hit = MAP.find(([re]) => re.test(url));
      if (hit) return route.fulfill({ path: path.join(ROOT, hit[1]), contentType: "application/javascript" });
      if (/^https?:/.test(url)) return route.abort();   // polices et autres ressources externes : ignorées
      return route.continue();
    });
    const p = await ctx.newPage();
    p.on("pageerror", e => console.log(`[${label}] erreur :`, e.message));
    p.on("console", m => m.type() === "error" && !/net::ERR_FAILED|ERR_BLOCKED/.test(m.text()) && console.log(`[${label}] console :`, m.text()));
    await p.goto("file://" + page);
    await p.waitForTimeout(3500);
    const wide = await p.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    if (wide) console.log(`[${label}] attention : la page déborde en largeur`);
    await p.screenshot({ path: `${out}-${label}.png` });
    await p.screenshot({ path: `${out}-${label}-complet.png`, fullPage: true });
    await ctx.close();
  }
  await browser.close();
  console.log("captures :", out + "-*.png");
})();
