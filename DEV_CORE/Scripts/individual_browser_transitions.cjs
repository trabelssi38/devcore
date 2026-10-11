/* Real project shell, real HTTP API, two disposable Edge profiles. */
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const assert = require('node:assert/strict');
const {spawn, execFileSync} = require('node:child_process');
const [browser, root, fixturePath] = process.argv.slice(2);
const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
const owned = [];
const pages = [];
let phase = 'start';
let browserCommand;
let attackerServer, attackerOrigin;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitFor(check) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) { if (await check()) return; await delay(100); }
  throw new Error('Browser condition did not become true');
}
function cdp(ws) {
  let id = 0; const pending = new Map();
  ws.addEventListener('message', event => {
    const value = JSON.parse(event.data), call = pending.get(value.id);
    if (call) {pending.delete(value.id); clearTimeout(call.timer);
      value.error ? call.reject(new Error(value.error.message)) : call.resolve(value.result);}
  });
  return (method, params={}) => new Promise((resolve,reject) => {
    const current=++id;
    const timer=setTimeout(()=>{pending.delete(current);reject(new Error('CDP timeout: '+method));},20000);
    pending.set(current,{resolve,reject,timer}); ws.send(JSON.stringify({id:current,method,params}));
  });
}
async function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((resolve,reject) => {ws.onopen=resolve; ws.onerror=reject;});
  return {ws,command:cdp(ws)};
}
async function startBrowser() {
  const profile = path.join(root, 'edge-profile'); fs.mkdirSync(profile);
  const child = spawn(browser, ['--headless=new', '--no-first-run', '--disable-background-networking',
    '--disable-extensions', '--disable-renderer-backgrounding', '--disable-background-timer-throttling',
    '--remote-debugging-port=0', '--user-data-dir=' + profile, 'about:blank'],
    {windowsHide:true, stdio:'ignore'});
  owned.push({child});
  fs.writeFileSync(path.join(root, 'owned-pids.json'), JSON.stringify(owned.map(x => x.child.pid)));
  let port, browserPath;
  await waitFor(() => {
    try {
      const lines=fs.readFileSync(path.join(profile, 'DevToolsActivePort'), 'utf8').trim().split('\n');
      port=Number(lines[0]); browserPath=lines[1];
      return Number.isInteger(port) && port > 0 && port < 65536 && browserPath.startsWith('/devtools/browser/');
    } catch(error) {
      if (['ENOENT','EBUSY'].includes(error.code)) return false;
      throw error;
    }
  });
  const browserCdp=await connect('ws://127.0.0.1:'+port+browserPath);
  browserCommand=browserCdp.command;
  return {port,child};
}
async function startAttacker() {
  attackerServer=http.createServer((request,response)=>{
    response.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});
    if(new URL(request.url,'http://attacker.invalid').pathname==='/fetch') {
      response.end(`<!doctype html><meta charset="utf-8"><output id="result">pending</output><script>
        fetch(${JSON.stringify(fixture.origin+'/api/pause')},{method:'POST',credentials:'include',
          headers:{'Content-Type':'application/json','X-CSRF-Token':'forged'},
          body:JSON.stringify({project:'beta',id:'T-01',expected_version:1})})
          .then(()=>document.querySelector('#result').textContent='unexpected-success')
          .catch(()=>document.querySelector('#result').textContent='cors-blocked');
      </script>`);
      return;
    }
    response.end(`<!doctype html><meta charset="utf-8"><form id="attack" method="post" action="${fixture.origin}/api/pause">
      <input name="project" value="beta"><input name="id" value="T-01"><input name="expected_version" value="1"></form>
      <script>document.querySelector('#attack').requestSubmit()</script>`);
  });
  await new Promise(resolve=>attackerServer.listen(0,'::1',resolve));
  attackerOrigin='http://[::1]:'+attackerServer.address().port;
}
async function open(name, port) {
  const created=await browserCommand('Target.createBrowserContext',{disposeOnDetach:true});
  const contextId=created.browserContextId;
  const target=await browserCommand('Target.createTarget',{url:'about:blank',browserContextId:contextId});
  const targets = await (await fetch('http://127.0.0.1:' + port + '/json/list')).json();
  const ws = new WebSocket(targets.find(x => x.id === target.targetId).webSocketDebuggerUrl);
  await new Promise((resolve,reject) => {ws.onopen=resolve; ws.onerror=reject;});
  const entry = {ws,contextId,targetId:target.targetId}; pages.push(entry);
  const command=entry.command=cdp(ws), dialogs = [], loginRequests = [], responses=[], apiRequests=[], apiResponses=[];
  ws.addEventListener('message', event => {
    const value = JSON.parse(event.data);
    if (value.method === 'Page.loadEventFired' && entry.loaded) entry.loaded();
    if (value.method === 'Network.requestWillBeSent') {
      const request = value.params.request;
      if(request.url===fixture.origin+'/api/pause') apiRequests.push({method:request.method,requestId:value.params.requestId});
      if (request.url === fixture.origin+'/api/auth/session' && request.method === 'POST') {
        loginRequests.push({bearer:Object.keys(request.headers).some(x=>x.toLowerCase()==='authorization')});
      }
    }
    if (value.method === 'Network.responseReceived' && value.params.response.url === fixture.origin+'/api/pause') {
      responses.push(value.params.response.status);
      apiResponses.push({requestId:value.params.requestId,status:value.params.response.status});
    }
    if (value.method === 'Page.javascriptDialogOpening') {
      dialogs.push(value.params.message);
      void command('Page.handleJavaScriptDialog',{accept:true}).catch(()=>{});
    }
  });
  async function evaluate(expression, awaitPromise=false) {
    const result = await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise});
    if (result.exceptionDetails) throw new Error('Browser script failed: '+result.exceptionDetails.text);
    return result.result.value;
  }
  await command('Network.enable');
  await command('Page.enable');
  if(fixture.authentication==='cookie') {
    const cookie = await command('Network.setCookie',{name:'devcore_session',value:fixture.cookies[name],
      url:fixture.origin,httpOnly:true,sameSite:'Strict'});
    assert.equal(cookie.success,true);
  }
  async function navigate(method,params={}) {
    const loaded = new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('Project page did not load')),20000);
      entry.loaded=()=>{clearTimeout(timer);entry.loaded=null;resolve();};
    });
    await command(method,params); await loaded;
  }
  await navigate('Page.navigate',{url:fixture.origin+'/project'});
  if(fixture.authentication==='password') {
    await waitFor(()=>evaluate("document.querySelector('#connect') && !document.querySelector('#connect').disabled"));
    const erased = await evaluate(`(()=>{
      document.querySelector('#project-input').value=${JSON.stringify(name==='alice'?'alpha':'beta')};
      document.querySelector('#user-input').value=${JSON.stringify(name)};
      document.querySelector('#password-input').value=${JSON.stringify(fixture.password)};
      document.querySelector('#login').requestSubmit();
      return document.querySelector('#password-input').value==='';})()`);
    assert.equal(erased,true);
  }
  await waitFor(()=>evaluate("document.querySelectorAll('#tasks tr').length === 1"));
  if(fixture.authentication==='password') {
    assert.equal(loginRequests.length,1); assert.equal(loginRequests[0].bearer,false);
  }
  return {evaluate, dialogs, responses, apiRequests, apiResponses, reload:()=>navigate('Page.reload'), version:(await browserCommand('Browser.getVersion')).product,
    navigate,contextId,targetId:target.targetId,command,ws};
}
const rows = "Array.from(document.querySelectorAll('#tasks tr')).map(x=>x.textContent).join(' ')";
async function state(page, project) {
  return page.evaluate(`fetch('/api/dashboard/tasks?project=${project}').then(async r=>({status:r.status,tasks:await r.json()}))`,true);
}
async function click(page, label) {
  await page.evaluate(`Array.from(document.querySelectorAll('#tasks button')).find(x=>x.textContent===${JSON.stringify(label)}).click()`);
}
(async()=>{
  try {
    phase='start local attacker'; await startAttacker();
    phase='start Edge'; const {port,child}=await startBrowser();
    phase='open alice context'; const alice=await open('alice',port);
    phase='open bob context'; const bob=await open('bob',port);
    assert.notEqual(alice.contextId,bob.contextId);
    phase='initial rows';
    assert.match(await alice.evaluate(rows), /alpha/); assert.match(await bob.evaluate(rows), /beta/);
    let contextReloaded=false;
    if(fixture.authentication==='password') {
      const card="document.querySelector('#context-card').textContent";
      await waitFor(async()=> (await alice.evaluate(card)).includes('privées de alpha') &&
        (await bob.evaluate(card)).includes('privées de beta'));
      assert.ok(!(await alice.evaluate(card)).includes('privées de beta'));
      phase='reload context'; await alice.reload();
      await waitFor(async()=> (await alice.evaluate(card)).includes('privées de alpha') &&
        await alice.evaluate("Array.from(document.querySelectorAll('#tasks button')).some(x=>x.textContent==='Pause'&&!x.disabled)"));
      assert.ok((await alice.evaluate("document.querySelector('#context-decisions').textContent")).includes('Direction alpha local'));
      assert.ok(!(await alice.evaluate("document.querySelector('#context-decisions').textContent")).includes('Direction alpha old'));
      contextReloaded=true;
    }
    phase='pause'; await click(alice,'Pause');
    await waitFor(async()=> (await state(alice,'alpha')).tasks[0].status==='paused' &&
      await alice.evaluate("Array.from(document.querySelectorAll('#tasks button')).some(x=>x.textContent==='Reprendre'&&!x.disabled)"));
    assert.equal((await state(alice,'alpha')).tasks[0].version,2);
    assert.equal((await state(bob,'beta')).tasks[0].version,1);
    phase='resume'; await click(alice,'Reprendre');
    await waitFor(async()=> (await state(alice,'alpha')).tasks[0].version===3 &&
      await alice.evaluate("Array.from(document.querySelectorAll('#tasks button')).some(x=>x.textContent==='Pause'&&!x.disabled)"));
    assert.equal((await state(alice,'alpha')).tasks[0].status,'in_progress');
    assert.deepEqual(alice.dialogs,['Mettre en pause T-01 dans alpha ?', 'Reprendre T-01 dans alpha ?']);
    phase='audit'; await alice.evaluate("document.querySelector('#audit-form').requestSubmit()");
    await waitFor(()=>alice.evaluate("document.querySelectorAll('#audit-events tr').length===2"));
    const audit=await alice.evaluate("document.querySelector('#audit-events').textContent");
    assert.match(audit,/alice/); assert.match(audit,/Pause/); assert.match(audit,/Reprise/);
    phase='cross site'; await bob.navigate('Page.navigate',{url:attackerOrigin});
    await waitFor(()=>bob.evaluate("location.pathname==='/api/pause' && document.body.innerText.includes('individual_credential_required')"));
    const crossSite=await bob.evaluate("document.body.innerText");
    assert.match(crossSite,/individual_credential_required/);
    assert.equal(bob.responses.at(-1),401);
    await waitFor(()=>bob.apiRequests.some(item=>item.method==='POST'));
    phase='cross-origin preflight'; bob.apiRequests.length=0; bob.apiResponses.length=0;
    await bob.navigate('Page.navigate',{url:attackerOrigin+'/fetch'});
    await waitFor(()=>bob.evaluate("document.querySelector('#result')?.textContent==='cors-blocked'"));
    const preflightRequests=bob.apiRequests.map(item=>item.method);
    assert.ok(preflightRequests.includes('OPTIONS'),`expected CORS preflight, got ${preflightRequests.join(',')}`);
    const preflightRequest=bob.apiRequests.find(x=>x.method==='OPTIONS');
    const preflight=bob.apiResponses.find(item=>item.requestId===preflightRequest.requestId);
    assert.equal(preflight?.status,400,`unexpected CORS preflight response: ${JSON.stringify(preflight)}`);
    assert.ok(!bob.apiResponses.some(item=>item.requestId!==preflight.requestId),
      `unexpected API response after denied preflight: ${JSON.stringify(bob.apiResponses)}`);
    phase='logout'; await alice.evaluate("document.querySelector('#logout').click()");
    await waitFor(()=>alice.evaluate("document.querySelectorAll('#tasks tr').length===0"));
    assert.equal((await state(alice,'alpha')).status,401);
    phase='bob returns to project'; await bob.navigate('Page.navigate',{url:fixture.origin+'/project'});
    await waitFor(()=>bob.evaluate("document.querySelectorAll('#tasks tr').length===1"));
    const beta=await state(bob,'beta'); assert.equal(beta.status,200);
    assert.equal(beta.tasks[0].version,1); assert.equal(beta.tasks[0].status,'in_progress');
    console.log(JSON.stringify({browser:alice.version,browser_contexts:2,authentication:fixture.authentication,
      context_reloaded:contextReloaded,alpha_version:3,beta_version:1,
      audit_rows:2,cross_site:401,cors_preflight:preflight.status,cors_preflight_seen:true,
      logout:401,bob_status:beta.status}));
  } finally {
    if(attackerServer) {attackerServer.closeAllConnections(); await new Promise(resolve=>attackerServer.close(resolve));}
    for(const entry of pages) {
      if(entry.ws) entry.ws.close();
      if(entry.contextId && browserCommand) await browserCommand('Target.disposeBrowserContext',{browserContextId:entry.contextId}).catch(()=>{});
    }
    for (const entry of owned) {
      try {execFileSync('taskkill',['/PID',String(entry.child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore',timeout:5000});}
      catch {entry.child.kill();}
    }
    fs.unlinkSync(path.join(root,'owned-pids.json'));
  }
})().catch(error=>{console.error(phase+': '+error.message);process.exitCode=1;});
