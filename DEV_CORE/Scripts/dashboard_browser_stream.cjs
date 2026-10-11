// Local-only real-browser transport fixture. No active API, data or browser profile.
const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const [browser, root, fixturePath] = process.argv.slice(2);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let child, socket, server;
const streams = new Set();
let failedSnapshots=0;
let generation=1, snapshotReads=0, lastEventId=null, streamConnections=0;
const cursorA='snapshot:'+'a'.repeat(32), cursorB='snapshot:'+'b'.repeat(32);

(async()=>{
 const {html,fail_snapshot_once:failSnapshotOnce} = JSON.parse(await fs.readFile(fixturePath,'utf8'));
 server=http.createServer((request,response)=>{
  if(request.url==='/api/dashboard'){
   snapshotReads++;
   if(failSnapshotOnce && snapshotReads===2){
    failedSnapshots++;
    response.writeHead(503,{'Content-Type':'application/json'});response.end('{"error":"fixture unavailable"}');return;
   }
   response.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});
   response.end(JSON.stringify({schema_version:1,
    sections:{project_cards:'<p>project alpha</p>',tasks_pipeline:'<p>version'+generation+' équipe</p>'},
    cache:{snapshot_cursor:generation===1?cursorA:cursorB},
    task_details:{alpha_T1:'version'+generation},
    task_interactions:{alpha_T1:{project:'alpha',task_id:'T1',title:'version'+generation}},token_metrics:{}}));
   return;
  }
  if(request.url==='/api/dashboard/stream'){
   streamConnections++;
   response.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-cache'});
   streams.add(response);response.on('close',()=>streams.delete(response));
   if(streamConnections===1){
    response.write('id: '+cursorA+'\r\nevent: message\r\ndata: Connected\r\n\r\n');
    setTimeout(()=>{generation=2;response.end();},100);
   }else{
    lastEventId=request.headers['last-event-id']||null;
    response.write('event: message\r\ndata: Connected\r\n\r\n');
    response.write('id: '+cursorB+'\r\nevent: dashboard.delta\r\ndata: {"snapshot_required":true,"has_changes":true}\r\n\r\n');
   }
   return;
  }
  response.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});response.end(html);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 const profile=path.join(root,'browser-profile');
 child=spawn(browser,['--headless=new','--no-first-run','--disable-background-networking',
  '--disable-extensions','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],
  {windowsHide:true,stdio:'ignore'});
 let port;
 for(let i=0;i<150;i++){
  try{port=Number((await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);break;}catch{}
  await delay(100);
 }
 if(!port)throw new Error('Browser debug endpoint did not start');
 const targets=await (await fetch('http://127.0.0.1:'+port+'/json/list')).json();
 const target=targets.find(item=>item.type==='page');
 if(!target)throw new Error('Browser page unavailable');
 socket=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
 let nextId=0;const pending=new Map();
 socket.addEventListener('message',event=>{
  const message=JSON.parse(event.data);if(!message.id)return;
  const callback=pending.get(message.id);if(!callback)return;pending.delete(message.id);
  if(message.error)callback.reject(new Error(JSON.stringify(message.error)));else callback.resolve(message.result);
 });
 const call=(method,params={})=>new Promise((resolve,reject)=>{
  const id=++nextId;
  const deadline=setTimeout(()=>{pending.delete(id);reject(new Error('Browser command deadline: '+method));},20000);
  pending.set(id,{resolve(value){clearTimeout(deadline);resolve(value);},reject(error){clearTimeout(deadline);reject(error);}});
  socket.send(JSON.stringify({id,method,params}));
 });
 const version=await call('Browser.getVersion');
 await call('Page.enable');await call('Page.navigate',{url});
 let dom;
 for(let i=0;i<180;i++){
  const result=await call('Runtime.evaluate',{expression:`(()=>{
   const tasks=document.getElementById('tasks-pipeline');
   if(!tasks || !tasks.textContent.includes('version2'))return null;
   return {tasks:tasks.textContent,details:JSON.parse(document.getElementById('task-details-data').textContent),
    interactions:JSON.parse(document.getElementById('task-interactions-data').textContent),errors:window.fixtureErrors};
  })()`,returnByValue:true});
  if(result.exceptionDetails)throw new Error('Browser evaluation failed');
  if(result.result.value){dom=result.result.value;break;}
  await delay(100);
 }
 if(!dom)throw new Error('Browser did not apply snapshot after SSE reconnection');
 process.stdout.write(JSON.stringify({browser:version.product,last_event_id:lastEventId,snapshot_reads:snapshotReads,failed_snapshots:failedSnapshots,dom}));
})().catch(error=>{process.stderr.write(String(error.stack));process.exitCode=1;}).finally(async()=>{
 if(socket)socket.close();
 for(const stream of streams)stream.destroy();
 if(server){server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
 if(child && child.pid){
  try{execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore',timeout:5000});}catch{child.kill();}
 }
});
