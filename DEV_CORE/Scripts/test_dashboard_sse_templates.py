"""Run actual template stream handlers in Node with deterministic transports."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize('initial', ['success', 'http', 'schema', 'network'])
def test_standard_startup_waits_for_snapshot_and_recovers_gap(tmp_path, initial):
    node = shutil.which('node')
    assert node
    source = (Path(__file__).parents[1] / 'Dashboard' / 'template.html').read_text(encoding='utf-8')
    shared = source[source.index('let dashboardRefreshPromise = null;'):source.index('function checkPlugin(')]
    stream = source[source.index('function handleDashboardSseEvent('):source.index('setupRefresh(60000);')]
    harness = 'const initial=' + json.dumps(initial) + ';\n' + r"""
const assert=require('node:assert/strict');
const API_BASE='http://fixture',window={ReadableStream:function(){},activeFilteredProject:null};
const document={getElementById(){return null;}};
function updateTokenReport(){}function updateRepowiseHealth(){}
let dashboardStreamAbort=null,dashboardStreamRetryId=null,dashboardLastEventId=null;
let resolveFirst,rejectFirst,reads=0;const streamHeaders=[],timers=new Map();let nextId=0;
function setTimeout(callback,delay){timers.set(++nextId,{callback,delay});return nextId;}
function clearTimeout(id){timers.delete(id);}
const cursorA='snapshot:'+'a'.repeat(32),cursorB='snapshot:'+'b'.repeat(32);
const first=new Promise((resolve,reject)=>{resolveFirst=resolve;rejectFirst=reject;});
function payload(cursor){return new Response(JSON.stringify({schema_version:1,sections:{},cache:{snapshot_cursor:cursor}}));}
function fetch(url,options){
 if(url.endsWith('/stream')){
  streamHeaders.push(options.headers);
  return new Promise(()=>{}); // A live stream must not hold the bootstrap promise.
 }
 reads++;
 return reads===1?first:Promise.resolve(payload(cursorB));
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
""" + shared + stream + r"""
(async()=>{
 const started=startDashboardSynchronization();
 await tick();
 assert.equal(reads,1);
 assert.equal(streamHeaders.length,0); // JSON remains in flight.
 if(initial==='success')resolveFirst(payload(cursorA));
 else if(initial==='http')resolveFirst(new Response('{}',{status:503}));
 else if(initial==='schema')resolveFirst(new Response('{"schema_version":99,"sections":{}}'));
 else rejectFirst(new Error('fixture network failure'));
 await started;
 assert.equal(streamHeaders.length,1);
 assert.equal(streamHeaders[0]['Last-Event-ID'],initial==='success'?cursorA:undefined);
 assert.equal(dashboardAppliedSnapshotCursor,initial==='success'?cursorA:null);
 if(initial==='success'){
  assert.equal(dashboardSnapshotRetryId,null);
  // Server has published B between GET A and the stream handshake: its reset
  // must cause a fresh read, including when the first connection has no id.
  parseDashboardSseBlock('event: message\ndata: Connected');
  parseDashboardSseBlock('id: '+cursorB+'\nevent: dashboard.delta\ndata: {"snapshot_required":true}');
 }else{
  assert.notEqual(dashboardSnapshotRetryId,null);
  const retry=timers.get(dashboardSnapshotRetryId);
  assert.ok(retry.delay>=4000 && retry.delay<=5000);
  retry.callback(); // No new SSE event is required after initial GET failure.
 }
 await tick();
 assert.equal(reads,2);
 assert.equal(dashboardAppliedSnapshotCursor,cursorB);
 assert.equal(dashboardSnapshotRetryId,null);
 assert.equal(streamHeaders.length,1);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script = tmp_path / 'startup.cjs'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


def test_standard_reconnect_acks_applied_snapshot_not_received_delta(tmp_path):
    node=shutil.which('node')
    assert node
    source=(Path(__file__).parents[1]/'Dashboard'/'template.html').read_text(encoding='utf-8')
    shared=source[source.index('let dashboardRefreshPromise = null;'):source.index('function checkPlugin(')]
    stream=source[source.index('function handleDashboardSseEvent('):source.index('setupRefresh(60000);')]
    harness=r"""
const assert=require('node:assert/strict');
const API_BASE='http://fixture',window={ReadableStream:function(){},activeFilteredProject:null};
const document={getElementById(){return null;}};
function updateTokenReport(){}function updateRepowiseHealth(){}
let dashboardStreamAbort=null,dashboardStreamRetryId=null,dashboardLastEventId=null;
const timers=new Map();let nextId=0,mode='success';const headers=[];
function setTimeout(callback){timers.set(++nextId,callback);return nextId;}
function clearTimeout(id){timers.delete(id);}
const cursorA='snapshot:'+'a'.repeat(32),cursorB='snapshot:'+'b'.repeat(32);
function fetch(url,options){
 if(url.endsWith('/stream')){headers.push(options.headers);return Promise.reject(new Error('fixture disconnect'));}
 return Promise.resolve(mode==='success'?new Response(JSON.stringify({schema_version:1,sections:{},cache:{snapshot_cursor:cursorA}})):new Response('{}',{status:503}));
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
"""+shared+stream+r"""
(async()=>{
 await connectDashboardStream();
 assert.equal(headers[0]['Last-Event-ID'],undefined); // No applied snapshot yet.
 assert.equal(await refreshDashboard(),true);
 assert.equal(dashboardAppliedSnapshotCursor,cursorA);
 mode='failure';
 parseDashboardSseBlock('id: '+cursorB+'\nevent: dashboard.delta\ndata: {"snapshot_required":true}');
 await tick();
 assert.equal(dashboardLastEventId,cursorB); // Observed id differs from applied id.
 assert.equal(dashboardAppliedSnapshotCursor,cursorA);
 await connectDashboardStream();
 assert.equal(headers[1]['Last-Event-ID'],cursorA);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script=tmp_path/'applied-cursor.cjs'
    script.write_text(harness,encoding='utf-8')
    result=subprocess.run([node,str(script)],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('view', ['standard', 'terminal'])
@pytest.mark.parametrize('status', [401, 403])
def test_access_denied_stops_sse_recovery_until_snapshot_succeeds(tmp_path, view, status):
    node=shutil.which('node')
    assert node
    filename='template.html' if view=='standard' else 'template_terminal.html'
    source=(Path(__file__).parents[1]/'Dashboard'/filename).read_text(encoding='utf-8')
    end=source.index('function checkPlugin(') if view=='standard' else source.index('const REFRESH_RATE=')
    code=source[source.index('let dashboardRefreshPromise = null;'):end]
    harness='const deniedStatus='+json.dumps(status)+';\n'+r"""
const assert=require('node:assert/strict');
const API_BASE='http://fixture',window={activeFilteredProject:null};
const elements={'api-ok':{},'sys-status':{},'task-count':{}};
const document={getElementById(id){return elements[id]||null;}};
function updateContainerHTML(){}
function updateTokenReport(){}
function updateRepowiseHealth(){}
const timers=new Map();let nextId=0,calls=0,status=503;
function setTimeout(callback,delay){timers.set(++nextId,{callback,delay});return nextId;}
function clearTimeout(id){timers.delete(id);}
function fetch(){calls++;return Promise.resolve(new Response(status===200?JSON.stringify({schema_version:1,sections:{}}):'{"error":"fixture"}',{status}));}
"""+code+r"""
(async()=>{
 assert.equal(await refreshDashboardForSse(),false);
 assert.equal(calls,1);
 assert.equal(timers.size,1);
 status=deniedStatus;
 assert.equal(await refreshDashboard(),false); // Polling observes revoked access.
 assert.equal(calls,2);
 assert.equal(dashboardSnapshotRecoveryDenied,true);
 assert.equal(dashboardSnapshotRetryId,null);
 assert.equal(timers.size,0);
 await Promise.all(Array.from({length:20},()=>refreshDashboardForSse()));
 assert.equal(calls,2); // Neither a timer nor another SSE burst retries denial.
 assert.equal(timers.size,0);
 status=200;
 assert.equal(await refreshDashboard(),true); // A later periodic read observes restored access.
 assert.equal(dashboardSnapshotRecoveryDenied,false);
 status=503;
 assert.equal(await refreshDashboardForSse(),false);
 assert.equal(calls,4);
 assert.equal(timers.size,1);
 assert.ok([...timers.values()][0].delay>=4000 && [...timers.values()][0].delay<=5000);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script=tmp_path/'snapshot-access-denied.cjs'
    script.write_text(harness,encoding='utf-8')
    result=subprocess.run([node,str(script)],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('view', ['standard', 'terminal'])
@pytest.mark.parametrize('random_value', [0, 0.999999])
def test_snapshot_retry_backoff_caps_and_polling_cancels(tmp_path, view, random_value):
    node = shutil.which('node')
    assert node
    filename = 'template.html' if view == 'standard' else 'template_terminal.html'
    source = (Path(__file__).parents[1] / 'Dashboard' / filename).read_text(encoding='utf-8')
    end = source.index('function performDashboardRefresh()' if view == 'standard' else 'async function performDashboardRefresh()')
    code = source[source.index('let dashboardRefreshPromise = null;'):end]
    harness = 'Math.random=()=>'+json.dumps(random_value)+';\n'+r"""
const assert=require('node:assert/strict');
const timers=new Map(),delays=[];let nextId=0,succeed=false;
function setTimeout(callback,delay){delays.push(delay);timers.set(++nextId,callback);return nextId;}
function clearTimeout(id){timers.delete(id);}
function performDashboardRefresh(){return Promise.resolve(succeed);}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
"""+code+r"""
(async()=>{
 await refreshDashboardForSse();
 for(let attempt=0;attempt<12;attempt++){
  assert.equal(timers.size,1);
  const [id,callback]=[...timers.entries()][0];timers.delete(id);callback();await tick();
 }
 assert.equal(delays.length,13);
 const bases=[5000,10000,20000,40000,...Array(9).fill(60000)];
 for(let i=0;i<delays.length;i++){
  assert.ok(delays[i]>=0.8*bases[i] && delays[i]<=bases[i]);
  assert.ok(delays[i]<=60000);
 }
 assert.equal(dashboardSnapshotRetryDelay,60000);
 succeed=true;
 assert.equal(await refreshDashboard(),true); // Polling succeeds without another SSE event.
 assert.equal(timers.size,0);
 assert.equal(dashboardSnapshotRetryId,null);
 assert.equal(dashboardSnapshotRetryDelay,5000);
 succeed=false;
 await refreshDashboardForSse();
 assert.ok(delays.at(-1)>=4000 && delays.at(-1)<=5000);
 assert.equal(timers.size,1);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script=tmp_path/'snapshot-backoff.cjs'
    script.write_text(harness,encoding='utf-8')
    result=subprocess.run([node,str(script)],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('view', ['standard', 'terminal'])
@pytest.mark.parametrize('failure', ['false', 'rejection'])
def test_sse_snapshot_failure_retries_with_one_timer(tmp_path, view, failure):
    node = shutil.which('node')
    assert node
    filename = 'template.html' if view == 'standard' else 'template_terminal.html'
    source = (Path(__file__).parents[1] / 'Dashboard' / filename).read_text(encoding='utf-8')
    code = source[source.index('let dashboardSnapshotRetryId = null;'):source.index('function validateDashboardSnapshot(')]
    harness = 'const failure=' + json.dumps(failure) + ';\n' + r"""
const assert=require('node:assert/strict');
Math.random=()=>0;
const timers=new Map();const delays=[];let nextId=0,calls=0,succeed=false;
function setTimeout(callback,delay){assert.ok(delay>=4000 && delay<=60000);delays.push(delay);timers.set(++nextId,callback);return nextId;}
function clearTimeout(id){timers.delete(id);}
function refreshDashboard(){calls++;return succeed?Promise.resolve(true):failure==='rejection'?Promise.reject(new Error('fixture failure')):Promise.resolve(false);}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fire(){const [id,callback]=[...timers.entries()][0];timers.delete(id);callback();}
""" + code + r"""
(async()=>{
 await Promise.all(Array.from({length:20},()=>refreshDashboardForSse()));
 assert.equal(timers.size,1);
 assert.equal(calls,20);
 fire();await tick();
 assert.equal(calls,21);
 assert.equal(timers.size,1);
 assert.deepEqual(delays,[4000,8000]);
 succeed=true;
 await refreshDashboardForSse(); // Another event succeeds before the timer.
 assert.equal(timers.size,0);
 assert.equal(dashboardSnapshotRetryId,null);
 assert.equal(dashboardSnapshotRetryDelay,5000);
 succeed=false;
 await refreshDashboardForSse();
 assert.equal(timers.size,1);
 succeed=true;fire();await tick();
 assert.equal(timers.size,0);
 assert.equal(dashboardSnapshotRetryId,null);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script = tmp_path / 'snapshot-recovery.cjs'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('view', ['standard', 'terminal'])
@pytest.mark.parametrize('invalid', [
    'sections_array', 'sections_string', 'section_object', 'section_null',
    'details_array', 'metrics_string', 'interactions_null', 'cursor_invalid', 'cache_array',
])
def test_snapshot_validation_precedes_section_and_data_writes(tmp_path, view, invalid):
    node = shutil.which('node')
    assert node
    filename = 'template.html' if view == 'standard' else 'template_terminal.html'
    source = (Path(__file__).parents[1] / 'Dashboard' / filename).read_text(encoding='utf-8')
    end = source.index('function checkPlugin(') if view == 'standard' else source.index('const REFRESH_RATE=')
    code = source[source.index('let dashboardRefreshPromise = null;'):end]
    harness = 'const invalid=' + json.dumps(invalid) + ';\n' + r"""
const assert=require('node:assert/strict');
const API_BASE='http://fixture',window={activeFilteredProject:null};
const elements={};
for(const name of ['project-cards','tasks-pipeline','task-details-data','task-interactions-data',
 'token-metrics-data','api-ok','sys-status','task-count'])elements[name]={textContent:'old'};
const document={getElementById(id){return elements[id]||null;}};
let writes=0;
function updateContainerHTML(){writes++;}
function updateTokenReport(){}
function updateRepowiseHealth(){}
let timers=0;
function setTimeout(){timers++;return 1;}
function clearTimeout(){timers--;}
let payload={schema_version:1,sections:{project_cards:'new',tasks_pipeline:'new'}};
if(invalid==='sections_array')payload.sections=[];
if(invalid==='sections_string')payload.sections='new';
if(invalid==='section_object')payload.sections.automation_hooks={html:'bad'};
if(invalid==='section_null')payload.sections.automation_hooks=null;
if(invalid==='details_array')payload.task_details=[];
if(invalid==='metrics_string')payload.token_metrics='bad';
if(invalid==='interactions_null')payload.task_interactions=null;
if(invalid==='cursor_invalid')payload.cache={snapshot_cursor:'snapshot:invalid'};
if(invalid==='cache_array')payload.cache=[];
function fetch(){return Promise.resolve(new Response(JSON.stringify(payload)));}
""" + code + r"""
(async()=>{
 assert.equal(await refreshDashboard(),false);
 assert.equal(writes,0);
 for(const name of ['task-details-data','task-interactions-data','token-metrics-data'])assert.equal(elements[name].textContent,'old');
 assert.equal(timers,0);
 assert.equal(dashboardRefreshPromise,null);
 payload={schema_version:1,sections:{},task_details:{},task_interactions:{},token_metrics:{}};
 assert.equal(await refreshDashboard(),true);
 assert.equal(elements['task-interactions-data'].textContent,'{}');
 assert.equal(timers,0);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script = tmp_path / 'snapshot-validation.cjs'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('view', ['standard', 'terminal'])
@pytest.mark.parametrize('scenario', ['updated', 'missing', 'invalid'])
def test_refresh_replaces_interactions_from_current_snapshot(tmp_path, view, scenario):
    node = shutil.which('node')
    assert node
    filename = 'template.html' if view == 'standard' else 'template_terminal.html'
    source = (Path(__file__).parents[1] / 'Dashboard' / filename).read_text(encoding='utf-8')
    end = source.index('function checkPlugin(') if view == 'standard' else source.index('const REFRESH_RATE=')
    code = source[source.index('let dashboardRefreshPromise = null;'):end]
    harness = 'const scenario=' + json.dumps(scenario) + ';\n' + r"""
const assert=require('node:assert/strict');
const API_BASE='http://fixture',window={activeFilteredProject:null};
const elements={};
for(const name of ['task-details-data','task-interactions-data','token-metrics-data','api-ok','sys-status','task-count'])elements[name]={textContent:'old',innerHTML:'unchanged'};
const document={getElementById(id){return elements[id]||null;}};
let writes=0;
function updateContainerHTML(){writes++;}
function updateTokenReport(){}
function updateRepowiseHealth(){}
function setTimeout(){return 1;}
function clearTimeout(){}
let payload;
function fetch(){return Promise.resolve(new Response(JSON.stringify(payload)));}
""" + code + r"""
(async()=>{
 const first={alpha_T1:{project:'alpha',task_id:'T1',title:'first'}};
 payload={schema_version:1,sections:{},task_interactions:first};
 assert.equal(await refreshDashboard(),true);
 assert.deepEqual(JSON.parse(elements['task-interactions-data'].textContent),first);
 const second={beta_T2:{project:'beta',task_id:'T2',title:'<script>fixture</script>'}};
 payload={schema_version:1,sections:{},task_interactions:second};
 if(scenario==='missing')delete payload.task_interactions;
 if(scenario==='invalid')payload.task_interactions=[];
 const before=writes;
 assert.equal(await refreshDashboard(),scenario!=='invalid');
 assert.deepEqual(JSON.parse(elements['task-interactions-data'].textContent),scenario==='invalid'?first:scenario==='missing'?{}:second);
 assert.equal(elements['task-interactions-data'].innerHTML,'unchanged');
 if(scenario==='invalid')assert.equal(writes,before);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script = tmp_path / 'interactions-refresh.cjs'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('scenario', ['empty', 'missing', 'invalid'])
def test_terminal_replaces_stale_sections_and_task_details(tmp_path, scenario):
    node = shutil.which('node')
    assert node
    source = (Path(__file__).parents[1] / 'Dashboard' / 'template_terminal.html').read_text(encoding='utf-8')
    for identity in ['task-details-data', 'task-interactions-data', 'token-metrics-data']:
        assert source.count('id="' + identity + '"') == 1
    code = source[source.index('let dashboardRefreshPromise = null;'):source.index('const REFRESH_RATE=')]
    harness = 'const scenario=' + json.dumps(scenario) + ';\n' + r"""
const assert=require('node:assert/strict');
const API_BASE='http://fixture',window={activeFilteredProject:null};
const names=['project_cards','tasks_pipeline','services_monitoring','token_activity_report',
 'context_composition','metrics_service_summary','event_bus_recent','plugin_status',
 'knowledge_graph_summary','automation_hooks'];
const elements={};
for(const name of [...names.map(name=>name.replaceAll('_','-')),'api-ok','sys-status','task-count','task-details-data','token-metrics-data']){
 elements[name]={textContent:'old',html:'old',querySelector(){return null;}};
}
const document={getElementById(id){return elements[id]||null;}};
const localStorage={getItem(){return null;}};
let writes=0;
function updateContainerHTML(id,html){writes++;elements[id].html=html;}
function updateTokenReport(){}
function updateRepowiseHealth(){}
function setTimeout(){return 1;}
function clearTimeout(){}
let payload;
function fetch(){return Promise.resolve(new Response(JSON.stringify(payload)));}
""" + code + r"""
(async()=>{
 payload={schema_version:1,sections:Object.fromEntries(names.map(name=>[name,'<p>current</p>'])),task_details:{alpha_T1:'current'}};
 assert.equal(await refreshDashboard(),true);
 assert.equal(elements['tasks-pipeline'].html,'<p>current</p>');
 assert.deepEqual(JSON.parse(elements['task-details-data'].textContent),{alpha_T1:'current'});
 const before=writes;
 payload={schema_version:1,sections:scenario==='missing'?{}:Object.fromEntries(names.map(name=>[name,''])),task_details:{}};
 if(scenario==='invalid'){
  payload.sections.automation_hooks={bad:true};
  assert.equal(await refreshDashboard(),false);
  assert.equal(writes,before); // All known sections validated before any DOM writes.
  assert.equal(elements['tasks-pipeline'].html,'<p>current</p>');
 }else{
  assert.equal(await refreshDashboard(),true);
  for(const name of names){
   const html=elements[name.replaceAll('_','-')].html;
   if(name==='services_monitoring')assert.match(html,/Auto-refresh 60s/);
   else assert.equal(html,'');
  }
  assert.equal(elements['task-count'].textContent,0);
  assert.deepEqual(JSON.parse(elements['task-details-data'].textContent),{});
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script = tmp_path / 'terminal-empty.cjs'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


def test_two_templates_keep_identical_refresh_queue_and_reader():
    directory = Path(__file__).parents[1] / 'Dashboard'
    standard = (directory / 'template.html').read_text(encoding='utf-8')
    terminal = (directory / 'template_terminal.html').read_text(encoding='utf-8')
    expected = standard[standard.index('let dashboardRefreshPromise = null;'):standard.index('function performDashboardRefresh()')]
    actual = terminal[terminal.index('let dashboardRefreshPromise = null;'):terminal.index('async function performDashboardRefresh()')]
    assert actual == expected


@pytest.mark.parametrize('view', ['standard', 'terminal'])
@pytest.mark.parametrize('scenario', [
    'unicode', 'exact_limit', 'declared_limit', 'actual_limit',
    'invalid_utf8', 'invalid_json', 'read_error', 'no_body',
])
def test_actual_json_reader_bounds_bytes_and_releases(tmp_path, scenario, view):
    node = shutil.which('node')
    assert node
    filename = 'template.html' if view == 'standard' else 'template_terminal.html'
    source = (Path(__file__).parents[1] / 'Dashboard' / filename).read_text(encoding='utf-8')
    code = source[source.index('async function readDashboardJson('):source.index('function performDashboardRefresh()' if view == 'standard' else 'async function performDashboardRefresh()')]
    harness = 'const scenario=' + json.dumps(scenario) + ';\n' + r"""
const assert=require('node:assert/strict');
let reads=0,cancels=0,releases=0;
const limit=16*1024*1024;
let chunks=[...new TextEncoder().encode('{"label":"équipe"}')].map(byte=>Uint8Array.of(byte));
if(scenario==='exact_limit'){
 const bytes=new Uint8Array(limit).fill(32);bytes[0]=123;bytes[limit-1]=125;chunks=[bytes];
}
if(scenario==='actual_limit')chunks=[new Uint8Array(limit),Uint8Array.of(0)];
if(scenario==='invalid_utf8')chunks=[Uint8Array.of(0xff)];
if(scenario==='invalid_json')chunks=[new TextEncoder().encode('{')];
const response={
 headers:{get(){return scenario==='declared_limit'?String(limit+1):'1';}},
 body:{getReader(){return {
  async read(){reads++;if(scenario==='read_error')throw new Error('read failure');return chunks.length?{done:false,value:chunks.shift()}:{done:true};},
  async cancel(){cancels++;}, releaseLock(){releases++;}
 };}}
};
if(scenario==='no_body')response.body=null;
""" + code + r"""
(async()=>{
 if(scenario==='unicode')assert.deepEqual(await readDashboardJson(response),{label:'équipe'});
 else if(scenario==='exact_limit')assert.deepEqual(await readDashboardJson(response),{});
 else await assert.rejects(readDashboardJson(response));
 assert.equal(cancels,scenario==='no_body'?0:1);
 assert.equal(releases,scenario==='no_body'?0:1);
 if(scenario==='declared_limit')assert.equal(reads,0);
 if(scenario==='actual_limit')assert.equal(reads,2);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script = tmp_path / 'json-bound.cjs'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('view', ['standard', 'terminal'])
def test_actual_sse_handlers_resynchronize_and_preserve_cursor(tmp_path, view):
    node = shutil.which('node')
    assert node, 'Node is required for SSE template contract qualification'
    filename = 'template.html' if view == 'standard' else 'template_terminal.html'
    source = (Path(__file__).parents[1] / 'Dashboard' / filename).read_text(encoding='utf-8')
    if view == 'standard':
        code = source[source.index('let dashboardSnapshotRetryId = null;'):source.index('function validateDashboardSnapshot(')] + source[source.index('function handleDashboardSseEvent('):source.index('setupRefresh(60000);')]
        assert 'startDashboardSynchronization();' in source[source.index('setupRefresh(60000);'):]
        prelude = "let dashboardStreamAbort=null, dashboardStreamRetryId=null, dashboardLastEventId=null; const API_BASE='http://fixture'; let currentTab='settings';"
        test = r"""
const cursor = 'snapshot:' + 'a'.repeat(32);
parseDashboardSseBlock('id: ' + cursor + '\nevent: message\ndata: Connected');
assert.equal(refreshes, 0);
parseDashboardSseBlock('id: ' + cursor + '\nevent: dashboard.delta\ndata: {"snapshot_required":true}');
assert.equal(refreshes, 1); // Even while settings tab is active.
parseDashboardSseBlock('id: invalid\nevent: message\ndata: Connected');
assert.equal(dashboardLastEventId, cursor);
connectDashboardStream();
connectDashboardStream(); // No parallel stream.
await new Promise(resolve => setImmediate(resolve));
assert.equal(requests.length, 1);
assert.equal(requests[0].headers['Last-Event-ID'], cursor);
assert.equal(timers.length, 1);
timers.shift()();
await new Promise(resolve => setImmediate(resolve));
assert.equal(requests.length, 2);
assert.equal(requests[1].headers['Last-Event-ID'], cursor);
"""
    else:
        code = source[source.index('let dashboardSnapshotRetryId = null;'):source.index('function validateDashboardSnapshot(')] + source[source.index('function connectStream() {'):source.index('function showInteractions(')]
        prelude = ''
        test = r"""
connectStream();
assert.equal(instances.length, 1);
const stream = instances[0];
stream.handlers['dashboard.delta']({data:'{"snapshot_required":true}'});
assert.equal(refreshes, 1);
stream.onerror();
assert.equal(stream.closed, false);
assert.equal(timers.length, 0); // Native EventSource owns retry and its cursor.
stream.handlers['dashboard.delta']({data:'{"has_changes":true}'});
assert.equal(refreshes, 2);
"""
    harness = """
const assert = require('node:assert/strict');
let refreshes=0; const requests=[], timers=[], instances=[];
function refreshDashboard(){refreshes++;if(typeof dashboardLastEventId!=='undefined')dashboardAppliedSnapshotCursor=dashboardLastEventId;return Promise.resolve(true);}
const window={ReadableStream: function(){}};
function setTimeout(callback){timers.push(callback);return timers.length;}
function clearTimeout(){}
function fetch(url, options){requests.push(options);return Promise.reject(new Error('fixture disconnect'));}
class EventSource {
 constructor(url){this.handlers={};this.closed=false;instances.push(this);}
 addEventListener(name, callback){this.handlers[name]=callback;}
 close(){this.closed=true;}
}
""" + prelude + '\n' + code + '\n(async()=>{\n' + test + '\n})().catch(error=>{console.error(error);process.exitCode=1;});'
    script = tmp_path / 'sse-template.cjs'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('view', ['standard', 'terminal'])
@pytest.mark.parametrize('failure', ['none', 'http', 'schema', 'timeout'])
def test_actual_refresh_serializes_and_recovers(tmp_path, failure, view):
    node = shutil.which('node')
    assert node
    filename = 'template.html' if view == 'standard' else 'template_terminal.html'
    source = (Path(__file__).parents[1] / 'Dashboard' / filename).read_text(encoding='utf-8')
    code = source[source.index('let dashboardRefreshPromise = null;'):source.index('function checkPlugin(') if view == 'standard' else source.index('const REFRESH_RATE=')]
    harness = r"""
const assert=require('node:assert/strict');
const API_BASE='http://fixture', window={activeFilteredProject:null};
const elements={'api-ok':{},'sys-status':{},'task-count':{},'token-metrics-data':{}};
const document={getElementById(id){return elements[id] || null;}};
const timers=new Map(), requests=[], applied=[];
let nextTimer=0, active=0, maximum=0;
function setTimeout(callback,delay){assert.equal(delay,20000);timers.set(++nextTimer,callback);return nextTimer;}
function clearTimeout(id){timers.delete(id);}
function updateTokenReport(){applied.push(view==='standard'?window.taskDetailsMap.generation:JSON.parse(elements['token-metrics-data'].textContent).generation);}
function updateRepowiseHealth(){}
function updateContainerHTML(){}
function fetch(url,options){
 assert.equal(url,'http://fixture/api/dashboard');
 active++;maximum=Math.max(maximum,active);
 return new Promise((resolve,reject)=>{
  const request={resolve(response){active--;resolve(response);}, reject(error){active--;reject(error);}, signal:options.signal};
  options.signal.addEventListener('abort',()=>request.reject(new Error('deadline')),{once:true});
  requests.push(request);
 });
}
const valid=generation=>new Response(JSON.stringify({schema_version:1,sections:{},task_details:{generation},token_metrics:{generation}}));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
""" + '\nconst view=' + json.dumps(view) + '; const failure=' + json.dumps(failure) + ';\n' + code + r"""
(async()=>{
 const first=refreshDashboard();
 await tick();
 assert.equal(requests.length,1);
 for(let i=0;i<100;i++)assert.equal(refreshDashboard(),first);
 assert.equal(requests.length,1);
 if(failure==='http')requests[0].resolve({ok:false});
 else if(failure==='schema')requests[0].resolve(new Response('{"schema_version":999}'));
 else if(failure==='timeout'){
  [...timers.values()][0]();
  assert.equal(requests[0].signal.aborted,true);
 }else requests[0].resolve(valid(1));
 await tick();
 assert.equal(requests.length,2);
 assert.equal(timers.size,1);
 requests[1].resolve(valid(2));
 assert.equal(await first,true);
 assert.equal(maximum,1);
 assert.deepEqual(applied,failure==='none'?[1,2]:[2]);
 assert.equal(timers.size,0);
 assert.equal(dashboardRefreshPromise,null);
 const later=refreshDashboard();
 await tick();
 requests[2].resolve({ok:false});
 assert.equal(await later,false);
 assert.equal(timers.size,0);
 assert.equal(dashboardRefreshPromise,null);
 assert.equal(requests.length,3);
 if(view==='terminal'){
  elements['task-count'].textContent=99;
  const empty=refreshDashboard();
  await tick();
  requests[3].resolve(new Response(JSON.stringify({schema_version:1,sections:{},task_details:{},token_metrics:{generation:4}})));
  assert.equal(await empty,true);
  assert.equal(elements['task-count'].textContent,0);
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script = tmp_path / 'refresh-queue.cjs'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


def test_refresh_request_at_settlement_is_not_lost(tmp_path):
    node = shutil.which('node')
    assert node
    source = (Path(__file__).parents[1] / 'Dashboard' / 'template.html').read_text(encoding='utf-8')
    code = source[source.index('let dashboardRefreshPromise = null;'):source.index('function performDashboardRefresh()')]
    harness = r"""
const assert=require('node:assert/strict');
let calls=0;
function performDashboardRefresh(){
 calls++;
 if(calls===1){
  // Runs after the async loop exits, before its finally callback.
  queueMicrotask(()=>queueMicrotask(()=>refreshDashboard()));
 }
 return Promise.resolve(true);
}
""" + code + r"""
(async()=>{
 assert.equal(await refreshDashboard(),true);
 assert.equal(calls,2);
 assert.equal(dashboardRefreshPending,false);
 assert.equal(dashboardRefreshPromise,null);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script = tmp_path / 'refresh-settlement.cjs'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('ending', ['eof', 'read_error', 'cancel_error', 'oversize', 'abort'])
def test_actual_stream_fragmentation_and_reader_cleanup(tmp_path, ending):
    node = shutil.which('node')
    assert node, 'Node is required for SSE template contract qualification'
    source = (Path(__file__).parents[1] / 'Dashboard' / 'template.html').read_text(encoding='utf-8')
    code = source[source.index('let dashboardSnapshotRetryId = null;'):source.index('function validateDashboardSnapshot(')] + source[source.index('function handleDashboardSseEvent('):source.index('setupRefresh(60000);')]
    harness = r"""
const assert = require('node:assert/strict');
let dashboardStreamAbort=null, dashboardStreamRetryId=null, dashboardLastEventId=null;
const API_BASE='http://fixture', window={ReadableStream:function(){}};
let refreshes=0, cancels=0, releases=0, reads=0;
const timers=[], payloads=[];
function refreshDashboard(){refreshes++;if(typeof dashboardLastEventId!=='undefined')dashboardAppliedSnapshotCursor=dashboardLastEventId;return Promise.resolve(true);}
function setTimeout(callback){timers.push(callback);return timers.length;}
function clearTimeout(){}
const cursor='snapshot:'+'b'.repeat(32);
const bytes=new TextEncoder().encode('id: '+cursor+'\r\nevent: dashboard.delta\r\ndata: {"has_changes":true,\r\ndata: "label":"équipe"}\r\n\r\n');
const reader={
 async read(){
  if(reads<bytes.length) return {done:false,value:bytes.slice(reads,++reads)};
  reads++;
  if(ending==='read_error') throw new Error('read failure');
  if(ending==='abort'){dashboardStreamAbort.abort();throw new Error('aborted');}
  if(ending==='oversize' && reads===bytes.length+1) return {done:false,value:new Uint8Array(1048577).fill(120)};
  // An incomplete last event must never be dispatched on EOF.
  if(reads===bytes.length+1) return {done:false,value:new TextEncoder().encode('data: {"has_changes":true}')};
  return {done:true};
 },
 async cancel(){cancels++;if(ending==='cancel_error')throw new Error('cancel failure');},
 releaseLock(){releases++;}
};
function fetch(){return Promise.resolve({ok:true,body:{getReader(){return reader;}}});}
""" + '\nconst ending=' + json.dumps(ending) + ';\n' + code + r"""
const originalHandler=handleDashboardSseEvent;
handleDashboardSseEvent=(name,payload)=>{payloads.push(payload);originalHandler(name,payload);};
(async()=>{
 await connectDashboardStream();
 assert.equal(refreshes,1);
 assert.equal(payloads[0].label,"équipe");
 assert.equal(dashboardLastEventId,cursor);
 assert.equal(cancels,1);
 assert.equal(releases,1);
 assert.equal(dashboardStreamAbort,null);
 assert.equal(timers.length,ending==='abort'?0:1);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    script = tmp_path / 'sse-fragments.cjs'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
