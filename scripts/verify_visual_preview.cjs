const {chromium}=require('../.tools/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=path.resolve('artifacts/workcell-lighting');fs.mkdirSync(out,{recursive:true});
let browser;
const url=process.env.SCENE_URL||'http://127.0.0.1:5176/';
(async()=>{
  browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-webgl','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
  page.setDefaultTimeout(60000);
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('request',r=>requests.push({url:r.url(),method:r.method()}));
  const main=()=>page.locator('.pose-canvas'),preview=()=>page.locator('.pose-preview-card canvas');
  const read=()=>main().evaluate(el=>({observed:JSON.parse(el.dataset.observedTransform),estimate:JSON.parse(el.dataset.estimateTransform),
    render:JSON.parse(el.dataset.renderStats),stationary:JSON.parse(el.dataset.stationaryTransforms),geometry:JSON.parse(el.dataset.geometryProof),gizmo:el.dataset.gizmoVisible}));
  const sync=async()=>{
    const a=await main().getAttribute('data-estimate-transform'),b=await preview().getAttribute('data-estimate-transform');
    assert.equal(a,b,'Main and preview transforms disagree');
  };
  const seek=async value=>{
    await page.getByRole('slider',{name:'Correction preview position in seconds'}).evaluate((el,value)=>{
      const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
      setter.call(el,String(value));el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
    },value);
    await page.waitForTimeout(200);await sync();
  };
  await page.goto(url);
  await page.waitForFunction(()=>document.querySelector('.pose-canvas')?.dataset.robotAsset
    && document.querySelector('.pose-canvas')?.dataset.environmentAsset
    && Number(document.querySelector('.pose-preview-card canvas')?.dataset.frame)>0);
  await page.waitForTimeout(800);
  await page.screenshot({path:path.join(out,'initial.png')});
  await page.locator('.pose-preview-card').screenshot({path:path.join(out,'preview.png')});
  if(process.env.INITIAL_ONLY){await browser.close();return;}
  const initial=await read();assert.equal(initial.geometry.missingVertices,0);
  assert.equal(initial.geometry.solidVertices,initial.geometry.overlayVertices);
  assert.equal(initial.gizmo,'false');await sync();
  const essentialBounds=await page.getByRole('button',{name:'Export synthetic state',exact:true}).boundingBox();
  assert(essentialBounds.y+essentialBounds.height<900,'Essential actions not visible at 1440x900');
  const previewPixels=await preview().evaluate(c=>{
    const data=c.getContext('2d').getImageData(0,0,c.width,c.height).data,colors=new Set();
    for(let i=0;i<data.length;i+=16)colors.add(`${data[i]},${data[i+1]},${data[i+2]}`);
    return colors.size;
  });assert(previewPixels>100,'Thumbnail is empty');
  const frameBefore=(await read()).render.frame;await page.waitForTimeout(1000);
  assert.equal((await read()).render.frame,frameBefore,'Continuous idle rendering');
  // Both playback buttons act on the same state; seek intentionally pauses.
  await page.getByRole('button',{name:'Play preview',exact:true}).click();
  await page.waitForTimeout(700);await page.getByRole('button',{name:'Pause correction',exact:true}).click();
  const paused=await page.locator('.pose-preview-card').getAttribute('data-elapsed');
  await page.waitForTimeout(300);assert.equal(await page.locator('.pose-preview-card').getAttribute('data-elapsed'),paused);await sync();
  await seek(2.5);assert.equal(Number(await page.locator('.pose-preview-card').getAttribute('data-elapsed')),2.5);
  assert.equal(await page.locator('.pose-preview-card').getAttribute('data-running'),'false');
  await page.getByRole('button',{name:'Resume correction',exact:true}).click();
  await page.waitForTimeout(400);await page.getByRole('button',{name:'Pause preview',exact:true}).click();await sync();
  await seek(5);
  const aligned=await read();assert.equal(Math.max(...aligned.observed.map((v,i)=>Math.abs(v-aligned.estimate[i]))),0);
  assert.deepEqual(aligned.observed,initial.observed);assert.deepEqual(aligned.stationary,initial.stationary);
  await page.screenshot({path:path.join(out,'aligned.png')});
  await page.getByRole('button',{name:'Reset estimate',exact:true}).click();
  assert.deepEqual((await read()).estimate,initial.estimate);
  await page.getByRole('button',{name:'Estimated overlay',exact:true}).click();
  await page.getByRole('button',{name:'Reference overlay',exact:true}).click();
  await page.getByRole('button',{name:'Reference overlay',exact:true}).click();
  const canvas=main().locator('canvas'),bounds=await canvas.boundingBox();
  await page.mouse.move(bounds.x+bounds.width*.6,bounds.y+bounds.height*.46);
  await page.mouse.down({button:'right'});await page.mouse.move(bounds.x+bounds.width*.6-170,bounds.y+bounds.height*.46+45,{steps:15});await page.mouse.up({button:'right'});
  await page.mouse.wheel(0,-340);await page.waitForTimeout(900);
  await page.screenshot({path:path.join(out,'gripper-closeup.png')});
  await page.getByRole('button',{name:'Reset view',exact:true}).click();await page.waitForTimeout(250);
  const restored=await read();for(const key of ['cameraPosition','orbitTarget'])
    assert(restored.render[key].every((v,i)=>Math.abs(v-initial.render[key][i])<1e-8));
  await page.getByRole('button',{name:'Estimated overlay',exact:true}).click();
  await page.getByText('Perturb estimated overlay',{exact:true}).click();
  await page.getByRole('button',{name:'Gizmo',exact:true}).click();assert.equal((await read()).gizmo,'true');
  await page.getByText('Perturb estimated overlay',{exact:true}).click();assert.equal((await read()).gizmo,'false');
  // Uninterrupted full replay; count actual main and thumbnail draws.
  const renderer=await canvas.evaluate(c=>{const gl=c.getContext('webgl2'),ext=gl.getExtension('WEBGL_debug_renderer_info');return ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);});
  await page.evaluate(()=>{window.intervals=[];window.sampling=true;let last=performance.now();const sample=t=>{if(!window.sampling)return;window.intervals.push(t-last);last=t;requestAnimationFrame(sample);};requestAnimationFrame(sample);});
  const start=await main().evaluate(el=>({now:performance.now(),frame:JSON.parse(el.dataset.renderStats).frame,preview:Number(document.querySelector('.pose-preview-card canvas').dataset.frame)}));
  await page.getByRole('button',{name:'Replay',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.pose-preview-card').dataset.running==='true');
  await page.waitForFunction(()=>Number(document.querySelector('.pose-preview-card').dataset.elapsed)===5);
  const end=await main().evaluate(el=>{window.sampling=false;return{now:performance.now(),frame:JSON.parse(el.dataset.renderStats).frame,preview:Number(document.querySelector('.pose-preview-card canvas').dataset.frame)};});
  const intervals=(await page.evaluate(()=>window.intervals)).slice(2).sort((a,b)=>a-b);
  const performanceReport={mainFrames:end.frame-start.frame,previewFrames:end.preview-start.preview,
    seconds:(end.now-start.now)/1000,renderedFPS:(end.frame-start.frame)/((end.now-start.now)/1000),
    medianMs:intervals[Math.floor(intervals.length*.5)],p95Ms:intervals[Math.floor(intervals.length*.95)]};
  await sync();await page.getByRole('button',{name:'Reset estimate',exact:true}).click();
  await page.mouse.move(bounds.x+bounds.width*.48,bounds.y+bounds.height*.5);
  await page.mouse.down();await page.mouse.move(bounds.x+bounds.width*.48+180,bounds.y+bounds.height*.5-45,{steps:25});await page.mouse.up();
  await page.waitForTimeout(1000);await page.screenshot({path:path.join(out,'orbit.png')});
  await page.getByRole('button',{name:'Reset view',exact:true}).click();
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(800);
  await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.setViewportSize({width:1440,height:900});
  await page.getByRole('button',{name:'Recorded Benchmark',exact:true}).click();
  await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Download recorded evidence')&&!b.disabled));
  await page.getByRole('button',{name:/Benchmark ground truth/}).click();
  const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download recorded evidence',exact:true}).click()]);
  await download.saveAs(path.join(out,download.suggestedFilename()));
  const evidence=JSON.parse(fs.readFileSync(path.join(out,download.suggestedFilename()),'utf8'));assert(Object.keys(evidence).length>0);
  const methods=await page.locator('#recorded-method option').count();
  const cases=await page.locator('#recorded-case option').allTextContents();
  const comparisonCase=cases.findIndex(v=>/refinement|regression|better|worse/i.test(v));
  if(comparisonCase>=0){await page.locator('#recorded-case').selectOption({index:comparisonCase});await page.waitForTimeout(300);
    if(await page.locator('#recorded-method option').count()>1)await page.locator('#recorded-method').selectOption({index:1});}
  await page.getByRole('tab',{name:'Copilot',exact:true}).click();
  const ask=page.getByRole('button',{name:'Ask Nemotron · live inference',exact:true});await ask.waitFor();
  await page.waitForTimeout(600);assert(await ask.isDisabled(),'Missing-key state not preserved');
  const copilotText=await page.locator('.investigation-panel').innerText();
  await page.getByRole('tab',{name:'Results',exact:true}).click();
  await page.locator('.geometry-notice').waitFor({state:'hidden'});
  await page.screenshot({path:path.join(out,'benchmark.png')});
  const external=requests.filter(r=>!r.url.startsWith(new URL(url).origin)&&!r.url.startsWith('data:'));
  const inference=requests.filter(r=>r.method==='POST');assert.equal(inference.length,0);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const report={browser:browser.version(),renderer,viewport:'1440x900 DPR1',initial,aligned,performance:performanceReport,
    sharedGeometry:true,stationary:true,syncPlayPauseSeekReplay:true,reset:true,cameraReset:true,gizmoEditOnly:true,idleStopped:true,
    previewPixels,essentialActionsVisible:true,mobileOverflow:false,evidence:{filename:download.suggestedFilename(),validJSON:true},
    methods,cases,comparisonCase,copilotMissingKey:true,copilotText,errors,external,inference,requests};
  fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({browser:report.browser,renderer,performance:performanceReport,geometry:initial.geometry,errors,external},null,2));
  await browser.close();
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exitCode=1;});
