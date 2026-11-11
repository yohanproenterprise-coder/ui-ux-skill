const { chromium } = require('/tmp/claude-0/-home-user-ui-ux-skill/1baeb026-5382-5cbe-a469-5017e54efb4d/scratchpad/t/node_modules/playwright-core');
const W='/tmp/claude-0/-home-user-ui-ux-skill/1baeb026-5382-5cbe-a469-5017e54efb4d/scratchpad/film/';
const FPS=30,D=16,only=process.argv[2]?process.argv[2].split(',').map(Number):null;
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args:['--no-sandbox']});
const p=await b.newPage({viewport:{width:1080,height:1920}});const errs=[];p.on('pageerror',e=>errs.push(e.message));
await p.goto('file://'+W+'film.html');await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(800);
const frames=only?only.map(s=>Math.round(s*FPS)):Array.from({length:FPS*D},(_,i)=>i);
for(const f of frames){await p.evaluate(t=>seek(t),f/FPS);await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
 await p.screenshot({path:W+(only?'stills2/':'frames/')+String(f).padStart(5,'0')+'.jpg',type:'jpeg',quality:92})}
console.log('done',frames.length,errs);await b.close()})();
