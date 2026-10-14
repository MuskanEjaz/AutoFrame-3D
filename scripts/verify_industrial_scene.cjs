// Workspace-local Playwright, installed Chrome; captures actual WebGL renders.
const { chromium } = require('../.tools/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const out = path.resolve('artifacts/industrial-scene');
fs.mkdirSync(out,{recursive:true});
let activeBrowser;
(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-webgl','--enable-unsafe-swiftshader']});
  activeBrowser=browser;
  const page=await browser.newPage({viewport:{width:1600,height:1000},deviceScaleFactor:1});
  page.setDefaultTimeout(60000);
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('request',r=>requests.push(r.url()));
  await page.goto(process.env.SCENE_URL || 'http://127.0.0.1:5174/');
  await page.waitForFunction(()=>document.querySelector('.pose-canvas')?.dataset.robotAsset,{timeout:60000});
  await page.waitForTimeout(1200);
  const renderer=await page.locator('.pose-canvas canvas').evaluate(canvas=>{
    const gl=canvas.getContext('webgl2');const ext=gl.getExtension('WEBGL_debug_renderer_info');
    return ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);
  });
  await page.screenshot({path:path.join(out,'initial.png')});
  const stats=await page.locator('.pose-canvas').evaluate(el=>({asset:JSON.parse(el.dataset.robotAsset),render:JSON.parse(el.dataset.renderStats),observed:JSON.parse(el.dataset.observedTransform),estimate:JSON.parse(el.dataset.estimateTransform)}));
  await page.waitForTimeout(1000);
  const idleFrame=await page.locator('.pose-canvas').evaluate(el=>JSON.parse(el.dataset.renderStats).frame);
  const idleRenderingStopped=idleFrame===stats.render.frame;
  if(!idleRenderingStopped)throw new Error('Idle renderer kept drawing');
  fs.writeFileSync(path.join(out,'initial-stats.json'),JSON.stringify({stats,errors,requests},null,2));
  if(process.env.INITIAL_ONLY) {await browser.close();return;}
  await page.getByRole('button',{name:'CAD overlay',exact:true}).click();
  const canvas=page.locator('.pose-canvas canvas');
  const bounds=await canvas.boundingBox();
  await page.mouse.move(bounds.x+bounds.width*.6,bounds.y+bounds.height*.43);
  await page.mouse.down({button:'right'});
  await page.mouse.move(bounds.x+bounds.width*.6-220,bounds.y+bounds.height*.43+75,{steps:15});
  await page.mouse.up({button:'right'});
  await page.mouse.wheel(0,-450);await page.waitForTimeout(1000);
  await page.screenshot({path:path.join(out,'gripper-closeup.png')});
  await page.getByRole('button',{name:'Reset view',exact:true}).click();
  await page.waitForTimeout(250);
  const restoredCamera=await page.locator('.pose-canvas').evaluate(el=>JSON.parse(el.dataset.renderStats));
  if(restoredCamera.cameraPosition.some((v,i)=>Math.abs(v-stats.render.cameraPosition[i])>1e-8)
    ||restoredCamera.orbitTarget.some((v,i)=>Math.abs(v-stats.render.orbitTarget[i])>1e-8))throw new Error('Camera reset failed');
  await page.getByRole('button',{name:'CAD overlay',exact:true}).click();
  await page.getByRole('button',{name:'Preview correction · 5 sec',exact:true}).click();
  await page.waitForTimeout(2500);await page.screenshot({path:path.join(out,'playback.png')});
  await page.getByRole('status').filter({hasText:'Aligned to synthetic reference'}).waitFor({timeout:30000});
  await page.waitForTimeout(300);
  await page.screenshot({path:path.join(out,'aligned.png')});
  const aligned=await page.locator('.pose-canvas').evaluate(el=>({observed:JSON.parse(el.dataset.observedTransform),estimate:JSON.parse(el.dataset.estimateTransform),render:JSON.parse(el.dataset.renderStats)}));
  const maxError=Math.max(...aligned.observed.map((v,i)=>Math.abs(v-aligned.estimate[i])));
  if(maxError>1e-10)throw new Error(`Transform mismatch ${maxError}`);
  if(JSON.stringify(stats.observed)!==JSON.stringify(aligned.observed))throw new Error('Observed moved');
  // Separate uninterrupted replay measurement; screenshots otherwise stall software WebGL.
  await page.evaluate(()=>{
    window.sceneFrames=[]; window.sceneSampling=true; let last=performance.now();
    const sample=now=>{if(!window.sceneSampling)return;window.sceneFrames.push(now-last);last=now;requestAnimationFrame(sample);};
    requestAnimationFrame(sample);
  });
  const perfStart=await page.locator('.pose-canvas').evaluate(el=>({now:performance.now(),frame:JSON.parse(el.dataset.renderStats).frame}));
  await page.getByRole('button',{name:'Replay',exact:true}).click();
  await page.getByRole('status').filter({hasText:'Wrong pose · reference known'}).waitFor();
  await page.getByRole('status').filter({hasText:'Aligned to synthetic reference'}).waitFor({timeout:30000});
  const perfEnd=await page.locator('.pose-canvas').evaluate(el=>{window.sceneSampling=false;return {now:performance.now(),frame:JSON.parse(el.dataset.renderStats).frame};});
  const frameTimes=await page.evaluate(()=>window.sceneFrames);
  const sorted=frameTimes.slice(2).sort((a,b)=>a-b);
  const perf={samples:sorted.length,medianFrameMs:sorted[Math.floor(sorted.length*.5)],p95FrameMs:sorted[Math.floor(sorted.length*.95)],meanFrameMs:sorted.reduce((a,b)=>a+b,0)/sorted.length,
    renderedFrames:perfEnd.frame-perfStart.frame,wallSeconds:(perfEnd.now-perfStart.now)/1000,
    renderedFramesPerSecond:(perfEnd.frame-perfStart.frame)/((perfEnd.now-perfStart.now)/1000)};
  await page.getByRole('button',{name:'Reset estimate',exact:true}).click();
  const reset=await page.locator('.pose-canvas').evaluate(el=>JSON.parse(el.dataset.estimateTransform));
  if(reset.some((v,i)=>Math.abs(v-stats.estimate[i])>1e-10))throw new Error('Reset did not restore estimate');
  await page.mouse.move(bounds.x+bounds.width*.55,bounds.y+bounds.height*.5);
  const orbitStart=await page.locator('.pose-canvas').evaluate(el=>({now:performance.now(),frame:JSON.parse(el.dataset.renderStats).frame}));
  await page.mouse.down();await page.mouse.move(bounds.x+bounds.width*.55+240,bounds.y+bounds.height*.5-70,{steps:30});await page.mouse.up();
  await page.waitForTimeout(1000);await page.screenshot({path:path.join(out,'orbit.png')});
  const orbitEnd=await page.locator('.pose-canvas').evaluate(el=>({now:performance.now(),frame:JSON.parse(el.dataset.renderStats).frame}));
  const interaction={renderedFrames:orbitEnd.frame-orbitStart.frame,wallSeconds:(orbitEnd.now-orbitStart.now)/1000};
  await page.getByRole('button',{name:'Reset view',exact:true}).click();
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(1000);
  await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  const mobileOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  await page.setViewportSize({width:1600,height:1000});
  await page.getByRole('button',{name:'Recorded Benchmark',exact:true}).click();
  await page.getByRole('button',{name:'Download recorded evidence',exact:true}).waitFor();
  await page.waitForTimeout(1500);
  let evidence={};
  try {
    await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>
      b.textContent.includes('Download recorded evidence')&&!b.disabled));
    const [download]=await Promise.all([
      page.waitForEvent('download',{timeout:60000}),
      page.getByRole('button',{name:'Download recorded evidence',exact:true}).click(),
    ]);
    await download.saveAs(path.join(out,download.suggestedFilename()));
    evidence={filename:download.suggestedFilename(),downloaded:true};
  }catch(e){evidence={downloaded:false,error:String(e)};}
  await page.screenshot({path:path.join(out,'benchmark.png')});
  const origin=new URL(process.env.SCENE_URL || 'http://127.0.0.1:5174/').origin;
  const externalRequests=requests.filter(u=>!u.startsWith(origin)&&!u.startsWith('data:'));
  const report={browser:browser.version(),renderer,initial:stats,aligned,maxTransformError:maxError,resetVerified:true,cameraResetVerified:true,observedStationary:true,idleRenderingStopped,perf,interaction,mobileOverflow,evidence,errors,externalRequests,requests};
  fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({browser:report.browser,maxError,perf,mobileOverflow,evidence,errors,externalRequests},null,2));
  await browser.close();
})().catch(async e=>{console.error(e);if(activeBrowser)await activeBrowser.close();process.exitCode=1;});
