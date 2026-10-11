// Offline CDP smoke. Fixture responses are intercepted; never call a provider.
const fs=require('fs'),path=require('path');
const out=path.resolve(process.env.AUTOFRAME_BROWSER_OUTPUT||'artifacts/release_verification_20261011');fs.mkdirSync(out,{recursive:true});const delay=ms=>new Promise(r=>setTimeout(r,ms));
const assert=(value,message)=>{if(!value)throw Error(message)};
(async()=>{
 const target=await(await fetch((process.env.AUTOFRAME_BROWSER_CDP||'http://127.0.0.1:9224')+'/json/new?about:blank',{method:'PUT'})).json();
 const socket=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject});
 let id=0,mode='none',posts=0;const pending=new Map(),exceptions=[],errors=[],requests=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});socket.send(JSON.stringify({id:n,method,params}))});
 const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/investigation_browser.json'),'utf8'));
 const fulfill=(requestId,body,status=200)=>send('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify(body)).toString('base64')});
 socket.onmessage=event=>{
  const m=JSON.parse(event.data);
  if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}
  if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails.text);
  if(m.method==='Runtime.consoleAPICalled'&&m.params.type==='error')errors.push(m.params.args.map(a=>a.value||a.description));
  if(m.method==='Network.requestWillBeSent')requests.push({url:m.params.request.url,method:m.params.request.method});
  if(m.method==='Fetch.requestPaused'){
   const {requestId,request}=m.params;
   if(request.url.endsWith('/status'))fulfill(requestId,{available:true,message:'TEST FIXTURE availability; no live provider'});
   else{
    posts++;const q=JSON.parse(request.postData);
    const response={...fixture,question:q.question,selected_case_id:q.selected_case_id};
    if(mode==='timeout')Object.assign(response,{status:'incomplete',message:'TEST FIXTURE: Provider timeout; no fallback response was generated',findings:[],evidence:[]});
    if(mode==='provider-error')Object.assign(response,{status:'error',message:'TEST FIXTURE: Provider, tool arguments, evidence references, or response validation failed; no fallback was generated',findings:[],evidence:[]});
    setTimeout(()=>fulfill(requestId,mode==='http-error'?{detail:'TEST FIXTURE HTTP failure'}:response,mode==='http-error'?503:200),mode==='success'?1200:100);
   }
  }
 };
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value};
 const wait=async expr=>{for(let i=0;i<100;i++){if(await evaluate(expr))return;await delay(150)}throw Error('UI wait: '+expr)};
 const click=async text=>evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent.includes(${JSON.stringify(text)})).click()`);
 await send('Runtime.enable');await send('Page.enable');await send('Network.enable');
 const downloads=fs.mkdtempSync(path.join(require('os').tmpdir(),'autoframe-release-download-'));
 await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloads});
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:process.env.AUTOFRAME_BROWSER_URL||'http://127.0.0.1:5180/'});
 await wait("Boolean(document.querySelector('canvas')) && document.body.innerText.includes('Live analysis unavailable')");
 assert(await evaluate("document.querySelector('.investigation-panel .button-export').disabled"),'Missing credential must disable inference');
 assert(await evaluate("document.body.innerText.includes('1.4023')"),'Recorded A metadata');
 await click('Benchmark ground truth');
 assert(await evaluate("[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Benchmark ground truth')&&b.getAttribute('aria-pressed')==='true')"),'GT reveal');
 await evaluate("(()=>{const s=document.getElementById('recorded-case');s.value='control-regression';s.dispatchEvent(new Event('change',{bubbles:true}));})()");
 await wait("Boolean(document.querySelector('canvas'))&&document.body.innerText.includes('0.0853')");
 await evaluate("(()=>{const s=document.getElementById('recorded-method');s.value='reciprocal';s.dispatchEvent(new Event('change',{bubbles:true}));})()");
 await wait("Boolean(document.querySelector('canvas'))&&document.body.innerText.includes('0.1224')&&document.body.innerText.includes('3.73')");
 await click('Download recorded evidence');
 const download=path.join(downloads,'autoframe3d-control-regression-recorded-evidence.json');
 for(let i=0;i<40&&!fs.existsSync(download);i++)await delay(150);
 assert(fs.existsSync(download),'Evidence downloaded');
 assert(JSON.parse(fs.readFileSync(download)).cases[0].variants.length===2,'Nonempty valid comparison evidence');fs.copyFileSync(download,path.join(out,path.basename(download)));
 const productionErrors=[...errors],productionExceptions=[...exceptions];
 assert(!productionErrors.length&&!productionExceptions.length,'Production console clean');
 assert(!requests.some(r=>r.method==='POST'),'No production inference/registration requests');
 await send('Fetch.enable',{patterns:[{urlPattern:'*/api/investigation*',requestStage:'Request'}]});
 mode='success';await send('Page.reload');
 await wait("document.body.innerText.includes('TEST FIXTURE availability')&&Boolean(document.querySelector('canvas'))");
 assert(await evaluate("document.querySelectorAll('.investigation-examples button').length===4"),'Four example controls');
 for(let i=0;i<4;i++){
  await evaluate(`document.querySelectorAll('.investigation-examples button')[${i}].click()`);
  assert(await evaluate(`document.getElementById('investigation-question').value===document.querySelectorAll('.investigation-examples button')[${i}].textContent`),'Example question selection');
 }
 await click('Ask Nemotron');
 await wait("document.body.innerText.includes('Investigating recorded evidence…')");
 assert(await evaluate("document.querySelector('.investigation-panel .button-export').disabled&&document.getElementById('investigation-question').disabled&&[...document.querySelectorAll('.investigation-examples button')].every(b=>b.disabled)"),'Loading controls disabled');
 await click('Investigating recorded evidence');
 await wait("document.body.innerText.includes('MOCKED ANALYSIS · complete')");
 assert(posts===1,'Duplicate submission blocked');
 await click('View cited case');
 await wait("document.getElementById('recorded-case').value==='control-regression'&&document.getElementById('recorded-method').value==='reciprocal'&&Boolean(document.querySelector('canvas'))");
 assert(await evaluate("document.body.innerText.includes('case:tless')"),'Evidence reference displayed');
 for(const failure of ['timeout','provider-error','http-error']){
  mode=failure;await click('Ask Nemotron');
  await wait(failure==='http-error'?"Boolean(document.querySelector('[role=alert]'))":`document.body.innerText.includes(${JSON.stringify(failure==='timeout'?'TEST FIXTURE: Provider timeout':'TEST FIXTURE: Provider, tool arguments')})`);
  assert(await evaluate("!document.querySelector('.investigation-panel .button-export').disabled"),'Recovery control available');
 }
 mode='success';await click('Ask Nemotron');await wait("document.body.innerText.includes('MOCKED ANALYSIS · complete')");
 await evaluate("document.querySelector('.investigation-panel').scrollIntoView()");
 let shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,'copilot_desktop.png'),Buffer.from(shot.data,'base64'));
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await delay(300);
 const mobile=await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,buttons:[...document.querySelectorAll(".investigation-examples button")].map(b=>({width:b.getBoundingClientRect().width,height:b.getBoundingClientRect().height}))})');
 assert(mobile.scrollWidth<=390,'390 px overflow');
 for(let i=0;i<4;i++)await evaluate(`document.querySelectorAll('.investigation-examples button')[${i}].click()`);
 await click('Ask Nemotron');await wait("document.body.innerText.includes('MOCKED ANALYSIS · complete')");
 await evaluate("document.querySelector('.investigation-panel').scrollIntoView()");
 shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,'copilot_mobile.png'),Buffer.from(shot.data,'base64'));
 assert(!exceptions.length,'Browser exceptions');
 assert(!requests.some(r=>!r.url.startsWith('http://127.0.0.1:')&&!/^(data|blob):/.test(r.url)),'No remote browser requests');
 const result={production:{both_examples:true,gt_reveal:true,method_comparison:true,valid_evidence_download:true,missing_credentials:true,consoleErrors:productionErrors,exceptions:productionExceptions},
 fixtures:{label:'CDP-intercepted TEST FIXTURE; no live provider',all_four_questions:true,loading:true,duplicate_prevention:true,evidence_navigation:true,provider_timeout:true,provider_error:true,http_error:true,error_recovery:true,posts},mobile,exceptions,consoleErrors:errors,remote_requests:[],live_provider_requests:0};
 fs.writeFileSync(path.join(out,'browser_results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
 await send('Browser.close');socket.close();
})().catch(e=>{console.error(e);process.exit(1)});
