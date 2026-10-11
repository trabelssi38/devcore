// Execute the shipped browser script with DOM and HTTP doubles, without live data.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../Dashboard/project_tasks.js'), 'utf8');

class Element {
  constructor() { this.children = []; this.events = {}; this.value = ''; this.textContent = ''; }
  append(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  setAttribute(name, value) { this[name] = value; }
  addEventListener(name, fn) { this.events[name] = fn; }
  emit(name) { if (!this.disabled) this.events[name]?.({preventDefault() {}}); }
  set innerHTML(value) { throw new Error('Private data must use textContent, never innerHTML'); }
}
const tick = () => new Promise(resolve => setImmediate(resolve));
const example = overrides => ({project: 'alpha', id: 'T-01', title: 'Alpha task', status: 'in_progress', version: 1, ...overrides});
const exampleContext = overrides => ({
  project: 'alpha', schema_version: 1, card: '# Projet alpha\nDéploiement local.',
  measurement: {unit: 'utf8_bytes', scope: 'complete_json_line', model_tokens_measured: false, budget: 12000, used: 0},
  provenance: {card_sha256: 'b'.repeat(64), manifest_sha256: 'c'.repeat(64), reviewed_at: '2026-10-03', source_contents_verified: false},
  warnings: [], excluded_superseded: ['cloud'], omitted: [{id: 'worker', reason: 'not_relevant'}],
  decisions: [{id: 'local', status: 'effective', required: true, date: '2026-10-03', decision: 'Déployer localement.',
    rationale: 'Décision utilisateur', validation: 'Plan accepté', sources: ['plan.md']}], ...overrides
});
function contextLine(value) {
  const data = JSON.parse(JSON.stringify(value));
  for (let i = 0; data.measurement && i < 8; i++) {
    const length = Buffer.byteLength(JSON.stringify(data) + '\n', 'utf8');
    if (data.measurement.used === length) break;
    data.measurement.used = length;
  }
  return JSON.stringify(data) + '\n';
}
function harness({actions = ['task.read', 'task.mutate'], tasks = [example()], authenticated = true, context = exampleContext()} = {}) {
  const elements = {}, calls = [];
  const state = {actions, tasks, authenticated, context, project: 'alpha', user: 'alice', handler: null, confirm: true};
  const csrf = 'a'.repeat(64);
  const fetch = async (url, options) => {
    const call = {url, options}; calls.push(call);
    let result = state.handler && await state.handler(call);
    if (!result) {
      if (url === '/api/auth/session' && !options.method) result = state.authenticated ? {
        status: 200, data: {project: state.project, user_id: state.user, csrf_token: csrf, actions: state.actions}
      } : {status: 401};
      else if (url.startsWith('/api/dashboard/tasks?')) result = {status: 200, data: state.tasks};
      else if (url.startsWith('/api/project/context?')) result = {status: 200, data: state.context};
      else result = {status: 200, data: {status: 'success'}};
    }
    return {ok: result.status >= 200 && result.status < 300, status: result.status,
      body: result.body, json: async () => result.data, text: async () => result.raw ?? contextLine(result.data)};
  };
  vm.runInNewContext(source, {
    document: {getElementById: id => elements[id] ||= new Element(), createElement: () => new Element()},
    window: {confirm: message => {state.confirmMessage = message; return state.confirm;}}, fetch, TextEncoder, TextDecoder, AbortController,
    // Access to storage or shared token globals would throw in this fixture.
  });
  const mutations = () => calls.filter(call => ['/api/done', '/api/delete', '/api/pause', '/api/resume'].includes(call.url));
  const buttons = () => elements.tasks.children.flatMap(row => row.children[2].children);
  return {elements, calls, state, csrf, mutations, buttons};
}

test('reload recovers session and uses only its project; task text stays inert', async () => {
  const h = harness({tasks: [example({title: '<img src=x onerror=alert(1)>'})]}); await tick();
  assert.equal(h.elements.workspace.hidden, false);
  assert.equal(h.elements.login.hidden, true);
  assert.equal(h.elements['project-title'].textContent, 'Projet alpha');
  assert.equal(h.elements.tasks.children[0].children[0].textContent, 'T-01 · <img src=x onerror=alert(1)>');
  assert.equal(h.calls[1].url, '/api/dashboard/tasks?project=alpha&limit=20&offset=0');
  for (const call of h.calls) {
    assert.equal(call.options.credentials, 'same-origin');
    assert.equal(call.options.cache, 'no-store');
    assert.equal(call.options.headers?.Authorization, undefined);
  }
});

const withContext = ['task.read', 'task.mutate', 'context.read'];
const contextCalls = h => h.calls.filter(call => call.url.startsWith('/api/project/context?'));
test('context is loaded automatically with cookie only and rendered as inert text', async () => {
  const data = exampleContext({card: '<img src=x onerror=alert(1)> Fiche privée'});
  data.decisions[0].sources = ['javascript:alert(1)'];
  const h = harness({actions: withContext, context: data}); await tick();
  assert.equal(contextCalls(h).length, 1);
  const call = contextCalls(h)[0];
  assert.equal(call.url, '/api/project/context?project=alpha');
  assert.equal(call.options.credentials, 'same-origin'); assert.equal(call.options.cache, 'no-store');
  assert.equal(call.options.headers?.Authorization, undefined);
  assert.equal(h.elements['context-card'].textContent, data.card);
  assert.match(h.elements['context-decisions'].children[0].children[0].textContent, /En vigueur/);
  assert.match(h.elements['context-decisions'].children[0].children[4].textContent, /javascript:alert/);
  assert.equal(h.elements['context-decisions'].children[0].children[5].textContent, 'Date : 2026-10-03');
  assert.match(h.elements['context-provenance'].textContent, /octets UTF-8/);
  assert.ok(!h.elements['context-provenance'].textContent.includes('tokens'));
  assert.match(h.elements['context-omissions'].textContent, /cloud/);
});

test('old task-only sessions never request context and still operate on tasks', async () => {
  const h = harness(); await tick();
  assert.equal(contextCalls(h).length, 0);
  assert.equal(h.elements['context-card'].textContent, '');
  assert.equal(h.elements['context-search'].disabled, true);
  assert.match(h.elements['context-status'].textContent, /n’autorise pas/);
  assert.equal(h.buttons()[0].disabled, false);
});

test('slow context leaves task controls available and a task refresh discards its old response', async () => {
  const h = harness({actions: withContext}); await tick();
  let release;
  h.state.handler = call => call.url.startsWith('/api/project/context?') ? new Promise(resolve => { release = resolve; }) : undefined;
  h.elements.refresh.emit('click'); await tick();
  assert.equal(h.elements.refresh.disabled, false); assert.equal(h.elements.logout.disabled, false);
  assert.equal(h.buttons()[0].disabled, false); assert.equal(h.elements['context-search'].disabled, true);
  assert.equal(h.elements['context-card'].textContent, '');
  const oldCall = contextCalls(h).at(-1), oldRelease = release;
  h.state.handler = null;
  h.elements.refresh.emit('click'); await tick();
  assert.equal(oldCall.options.signal.aborted, true);
  oldRelease({status: 200, data: exampleContext({card: 'Obsolete private result'})}); await tick();
  assert.ok(!h.elements['context-card'].textContent.includes('Obsolete'));
});

test('targeted deepening shows proposed status and warns about freshness and omissions', async () => {
  const h = harness({actions: withContext}); await tick();
  const data = exampleContext({warnings: ['card_changed_since_review', 'context_review_expired'],
    omitted: [{id: 'other', reason: 'budget'}]});
  data.decisions.push({id: 'worker', status: 'proposed', required: false, decision: 'Proposer un worker',
    rationale: 'À évaluer', validation: 'Non qualifié', sources: ['candidate.md']});
  h.state.context = data; h.elements['context-query'].value = 'worker & reprise';
  h.elements['context-form'].emit('submit'); await tick();
  assert.equal(contextCalls(h).at(-1).url, '/api/project/context?project=alpha&query=worker%20%26%20reprise');
  assert.match(h.elements['context-decisions'].children[1].children[0].textContent, /Proposée/);
  assert.match(h.elements['context-warnings'].textContent, /ancienne/);
  assert.match(h.elements['context-warnings'].textContent, /a changé/);
  assert.match(h.elements['context-omissions'].textContent, /hors budget/);
});

test('budget or source errors erase prior context without hiding authorized tasks', async () => {
  for (const status of [413, 422, 503]) {
    const h = harness({actions: withContext}); await tick();
    h.state.handler = call => call.url.startsWith('/api/project/context?') ? {status} : undefined;
    h.elements['context-form'].emit('submit'); await tick();
    assert.equal(h.elements['context-card'].textContent, '');
    assert.equal(h.elements['context-decisions'].children.length, 0);
    assert.equal(h.elements.login.hidden, true); assert.equal(h.buttons()[0].disabled, false);
    assert.match(h.elements['context-status'].textContent, status === 413 ? /Aucun contexte partiel/ : /n’est pas disponible/);
  }
});

test('foreign, superseded or invalid measured contexts never reach the private display', async () => {
  const foreign = exampleContext({project: 'beta', card: 'Foreign beta private content'});
  const old = exampleContext(); old.decisions[0].status = 'superseded';
  const proposedRequired = exampleContext(); proposedRequired.decisions[0].status = 'proposed';
  const wrongBytes = contextLine(exampleContext()).replace('Déploiement local', 'Extra unmeasured content');
  const tooLarge = exampleContext(); tooLarge.measurement.budget = 256;
  const badProvenance = exampleContext(); badProvenance.provenance.card_sha256 = ['b'.repeat(64)];
  for (const result of [{data: foreign}, {data: old}, {data: proposedRequired}, {raw: wrongBytes}, {data: tooLarge}, {data: badProvenance}]) {
    const h = harness({actions: withContext}); await tick();
    h.state.handler = call => call.url.startsWith('/api/project/context?') ? {status: 200, ...result} : undefined;
    h.elements['context-form'].emit('submit'); await tick();
    assert.equal(h.elements['context-card'].textContent, '');
    assert.equal(h.elements['context-decisions'].children.length, 0);
    assert.match(h.elements['context-status'].textContent, /n’est pas disponible/);
  }
});

test('context authentication failure erases all private display', async () => {
  for (const status of [401, 403]) {
    const h = harness({actions: withContext}); await tick();
    h.state.handler = call => call.url.startsWith('/api/project/context?') ? {status} : undefined;
    h.elements['context-form'].emit('submit'); await tick();
    assert.equal(h.elements.login.hidden, false); assert.equal(h.elements.tasks.children.length, 0);
    assert.equal(h.elements['context-card'].textContent, ''); assert.equal(h.elements['context-query'].value, '');
  }
});

test('logout and new identity cannot be repopulated by an old inflight context response', async () => {
  const h = harness({actions: withContext}); await tick();
  let release;
  h.state.handler = call => call.url.startsWith('/api/project/context?') ? new Promise(resolve => { release = resolve; }) : undefined;
  h.elements['context-query'].value = 'Private alpha query';
  h.elements['context-form'].emit('submit'); await tick();
  const oldCall = contextCalls(h).at(-1);
  h.elements.logout.emit('click'); await tick();
  assert.equal(oldCall.options.signal.aborted, true);
  assert.equal(h.elements['context-query'].value, ''); assert.equal(h.elements['context-card'].textContent, '');
  h.state.project = 'beta'; h.state.user = 'bob'; h.state.tasks = [example({project: 'beta'})];
  h.state.context = exampleContext({project: 'beta', card: 'Beta current card'}); h.state.handler = null;
  h.elements['project-input'].value = 'beta'; h.elements['user-input'].value = 'bob'; h.elements['password-input'].value = 'fixture password';
  h.elements.login.emit('submit'); await tick();
  release({status: 200, data: exampleContext({card: 'Old alpha private card'})}); await tick();
  assert.equal(h.elements['project-title'].textContent, 'Projet beta');
  assert.equal(h.elements['context-card'].textContent, 'Beta current card');
});

test('reader has no mutation controls; unavailable or unsafe versions disable writes', async () => {
  const reader = harness({actions: ['task.read']}); await tick();
  assert.equal(reader.buttons().length, 0);
  assert.match(reader.elements.rights.textContent, /uniquement/);
  const old = harness({tasks: [example({version: null}), example({version: Number.MAX_SAFE_INTEGER + 1})]}); await tick();
  assert.equal(old.buttons().length, 6);
  assert.ok(old.buttons().every(button => button.disabled));
  old.buttons()[0].emit('click'); await tick(); assert.equal(old.mutations().length, 0);
});

test('password login erases input immediately, preserves spaces and sends no bearer', async () => {
  const h = harness({authenticated: false}); await tick();
  h.elements['project-input'].value = 'alpha'; h.elements['user-input'].value = 'alice';
  h.elements['password-input'].value = '  fixture password with spaces  ';
  h.state.handler = call => {
    if (call.url === '/api/auth/session' && call.options.method === 'POST') {
      h.state.authenticated = true; return {status: 200, data: {}};
    }
  };
  h.elements.login.emit('submit');
  assert.equal(h.elements['password-input'].value, ''); await tick();
  const exchange = h.calls.find(call => call.options.method === 'POST');
  assert.equal(exchange.options.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(exchange.options.body), {project: 'alpha', user_id: 'alice', password: '  fixture password with spaces  '});
  assert.equal(h.elements.login.hidden, true);
  assert.equal(h.calls.filter(call => call.options.headers?.Authorization).length, 0);
});

test('stale version reloads without replaying the mutation', async () => {
  const h = harness(); await tick();
  h.state.handler = call => {
    if (call.url === '/api/done') {
      h.state.tasks = [example({version: 2, title: 'Concurrent change'})]; return {status: 409};
    }
  };
  h.buttons()[0].emit('click'); await tick();
  assert.equal(h.mutations().length, 1);
  assert.deepEqual(JSON.parse(h.mutations()[0].options.body), {project: 'alpha', id: 'T-01', expected_version: 1});
  assert.equal(h.mutations()[0].options.headers['X-CSRF-Token'], h.csrf);
  assert.match(h.elements.message.textContent, /a changé/);
  assert.match(h.elements.tasks.children[0].children[0].textContent, /Concurrent change/);
});

test('delete requires confirmation and sends the displayed version with csrf', async () => {
  const h = harness(); await tick(); h.state.confirm = false;
  h.buttons()[1].emit('click'); await tick(); assert.equal(h.mutations().length, 0);
  assert.equal(h.elements.message.textContent, 'Action annulée.');
  h.state.confirm = true; h.buttons()[1].emit('click'); await tick();
  const call = h.mutations()[0];
  assert.equal(call.url, '/api/delete'); assert.equal(call.options.method, 'DELETE');
  assert.equal(call.options.headers['X-CSRF-Token'], h.csrf);
  assert.equal(JSON.parse(call.options.body).expected_version, 1);
  assert.equal(call.options.headers.Origin, undefined); // Browser supplies it.
});

test('downgraded rights remove write controls after refusal', async () => {
  const h = harness(); await tick();
  h.state.handler = call => {
    if (call.url === '/api/done') { h.state.actions = ['task.read']; return {status: 403}; }
  };
  h.buttons()[0].emit('click'); await tick();
  assert.equal(h.buttons().length, 0); assert.equal(h.mutations().length, 1);
  assert.match(h.elements.message.textContent, /droits/);
});

test('expired session clears private display and returns to login', async () => {
  const h = harness(); await tick(); h.state.handler = call => call.url === '/api/done' ? {status: 401} : undefined;
  h.buttons()[0].emit('click'); await tick();
  assert.equal(h.elements.login.hidden, false); assert.equal(h.elements.workspace.hidden, true);
  assert.equal(h.elements.tasks.children.length, 0); assert.equal(h.elements.identity.textContent, '');
  assert.match(h.elements.message.textContent, /expirée/);
});

test('inflight request blocks duplicate actions; next page uses bounded offset', async () => {
  const h = harness({tasks: Array.from({length: 20}, (_, i) => example({id: `T-${i}`}))}); await tick();
  h.elements.next.emit('click'); await tick();
  assert.ok(h.calls.some(call => call.url.endsWith('&offset=20')));
  assert.equal(h.elements.page.textContent, 'Page 2');
  let release;
  h.state.handler = call => call.url === '/api/done' ? new Promise(resolve => { release = resolve; }) : undefined;
  const button = h.buttons()[0]; button.emit('click'); button.emit('click'); await tick();
  assert.equal(h.mutations().length, 1); assert.equal(h.elements.refresh.disabled, true);
  release({status: 200, data: {}}); await tick(); assert.equal(h.elements.refresh.disabled, false);
});

test('logout uses session csrf and erases project display', async () => {
  const h = harness(); await tick(); h.elements.logout.emit('click'); await tick();
  const call = h.calls.find(call => call.url === '/api/auth/session' && call.options.method === 'DELETE');
  assert.equal(call.options.headers['X-CSRF-Token'], h.csrf);
  assert.equal(h.elements.tasks.children.length, 0); assert.equal(h.elements.login.hidden, false);
});

test('unexpected project in response is never rendered', async () => {
  const h = harness({tasks: [example({project: 'beta', title: 'Private beta'})]}); await tick();
  assert.equal(h.elements.tasks.children.length, 0);
  assert.ok(!h.elements.message.textContent.includes('Private beta'));
  assert.match(h.elements.message.textContent, /n’a pas abouti/);
});

test('failed and saturated login keep the password erased and allow a later attempt', async () => {
  for (const status of [401, 429]) {
    const h = harness({authenticated: false}); await tick();
    h.elements['project-input'].value = 'alpha'; h.elements['user-input'].value = 'alice';
    h.elements['password-input'].value = 'Secret de fixture jamais affiché';
    h.state.handler = call => call.options.method === 'POST' ? {status} : undefined;
    h.elements.login.emit('submit'); await tick();
    assert.equal(h.elements['password-input'].value, '');
    assert.equal(h.elements.connect.disabled, false);
    assert.equal(h.elements.login.hidden, false);
    assert.match(h.elements.message.textContent, status === 401 ? /Connexion refusée/ : /Connexions en cours/);
    assert.ok(!h.elements.message.textContent.includes('Secret de fixture'));
  }
});

const withAudit = ['task.read', 'task.mutate', 'task.audit.read'];
const auditCalls = h => h.calls.filter(call => call.url.startsWith('/api/project/task-audit?'));
const auditPage = overrides => ({success: true, project: 'alpha', supported_actions: ['task.complete', 'task.delete', 'task.pause', 'task.resume'],
  events: [{id: '00000000-0000-4000-8000-000000000001', project: 'alpha', task_id: 'T-01', actor: 'alice',
    action: 'task.delete', created_at: '2026-10-03 12:00:00', before: {status: 'done', version: 2}, after: {status: 'deleted', version: 3}}],
  has_more: false, next_before_id: null, ...overrides});

test('audit is on demand, hidden without permission and uses cookie only with inert text', async () => {
  const old = harness(); await tick();
  assert.equal(old.elements['audit-panel'].hidden, true);
  old.elements['audit-form'].emit('submit'); await tick(); assert.equal(auditCalls(old).length, 0);
  const h = harness({actions: withAudit}); await tick();
  assert.equal(h.elements['audit-panel'].hidden, false); assert.equal(auditCalls(h).length, 0);
  const data = auditPage(); data.events[0].actor = '<img src=x onerror=alert(1)>';
  data.events[0].session_id = 'PRIVATE SECRET';
  h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? {status: 200, data} : undefined;
  h.elements['audit-form'].emit('submit'); await tick();
  assert.equal(auditCalls(h)[0].url, '/api/project/task-audit?project=alpha&limit=20');
  assert.equal(auditCalls(h)[0].options.credentials, 'same-origin'); assert.equal(auditCalls(h)[0].options.headers?.Authorization, undefined);
  assert.equal(h.elements['audit-events'].children[0].children[2].textContent, data.events[0].actor);
  assert.match(h.elements['audit-events'].children[0].children[3].textContent, /v2.*v3/);
  assert.equal(h.elements['audit-events'].children[0].children.length, 4);
  assert.equal(h.elements['audit-next'].disabled, true);
});

test('audit pagination keeps its accepted task filter and restarting drops the cursor', async () => {
  const h = harness({actions: withAudit}); await tick();
  const data = auditPage({has_more: true, next_before_id: '00000000-0000-4000-8000-000000000001'});
  h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? {status: 200, data} : undefined;
  h.elements['audit-task'].value = 'T-01'; h.elements['audit-form'].emit('submit'); await tick();
  assert.equal(h.elements['audit-next'].disabled, false);
  h.elements['audit-task'].value = 'T-other';
  const older = auditPage(); older.events[0].id = '00000000-0000-4000-8000-000000000002';
  h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? {status: 200, data: older} : undefined;
  h.elements['audit-next'].emit('click'); await tick();
  assert.match(auditCalls(h).at(-1).url, /task_id=T-01&before_id=00000000-0000-4000-8000-000000000001$/);
  h.elements['audit-form'].emit('submit'); await tick();
  assert.equal(auditCalls(h).at(-1).url, '/api/project/task-audit?project=alpha&limit=20&task_id=T-other');
  assert.equal(h.elements['audit-events'].children.length, 0); // Wrong filter is never rendered.
});

test('slow audit leaves task controls available; refresh aborts and rejects an old response', async () => {
  const h = harness({actions: withAudit}); await tick(); let release;
  h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? new Promise(resolve => {release = resolve;}) : undefined;
  h.elements['audit-form'].emit('submit'); await tick();
  const pending = auditCalls(h).at(-1);
  assert.equal(h.elements.refresh.disabled, false); assert.equal(h.buttons()[0].disabled, false);
  assert.equal(h.elements['audit-search'].disabled, true);
  h.elements.refresh.emit('click'); await tick(); assert.equal(pending.options.signal.aborted, true);
  release({status: 200, data: auditPage()}); await tick();
  assert.equal(h.elements['audit-events'].children.length, 0);
});

test('audit failures erase previous history without blocking tasks; authentication erases all display', async () => {
  for (const status of [400, 503, 401, 403]) {
    const h = harness({actions: withAudit}); await tick();
    h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? {status: 200, data: auditPage()} : undefined;
    h.elements['audit-form'].emit('submit'); await tick(); assert.equal(h.elements['audit-events'].children.length, 1);
    h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? {status} : undefined;
    h.elements['audit-form'].emit('submit'); await tick(); assert.equal(h.elements['audit-events'].children.length, 0);
    if ([401, 403].includes(status)) {
      assert.equal(h.elements.login.hidden, false); assert.equal(h.elements.tasks.children.length, 0);
      assert.equal(h.elements['audit-task'].value, '');
    } else {
      assert.equal(h.elements.login.hidden, true); assert.equal(h.buttons()[0].disabled, false);
      assert.equal(h.elements['audit-next'].disabled, true);
    }
  }
});

test('malformed or oversized audit pages never partially render', async () => {
  const cases = [];
  const foreign = auditPage({project: 'beta'}); cases.push(foreign);
  const extraForeign = auditPage(); extraForeign.events.push({...extraForeign.events[0], project: 'beta'}); cases.push(extraForeign);
  const duplicate = auditPage(); duplicate.events.push({...duplicate.events[0]}); cases.push(duplicate);
  const unsafe = auditPage(); unsafe.events[0].after.version = Number.MAX_SAFE_INTEGER + 1; cases.push(unsafe);
  const version = auditPage(); version.events[0].after.version = 4; cases.push(version);
  const badDate = auditPage(); badDate.events[0].created_at = '2026-02-30 12:00:00'; cases.push(badDate);
  const actor = auditPage(); actor.events[0].actor = 'PRIVATE\nACTOR'; cases.push(actor);
  cases.push(auditPage({has_more: true, next_before_id: '00000000-0000-4000-8000-000000000009'}));
  cases.push(auditPage({has_more: true, events: [], next_before_id: '00000000-0000-4000-8000-000000000001'}));
  cases.push(auditPage({private: 'X'.repeat(65536)}));
  for (const data of cases) {
    const h = harness({actions: withAudit}); await tick();
    h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? {status: 200, data} : undefined;
    h.elements['audit-form'].emit('submit'); await tick();
    assert.equal(h.elements['audit-events'].children.length, 0); assert.equal(h.elements['audit-next'].disabled, true);
    assert.match(h.elements['audit-status'].textContent, /n’est pas disponible/);
  }
});

test('audit stream stops at byte bound and releases the reader', async () => {
  const h = harness({actions: withAudit}); await tick(); let reads = 0, cancelled = false, unlocked = false;
  const body = {getReader: () => ({read: async () => (++reads, {done: false, value: new Uint8Array(32769)}),
    cancel: async () => {cancelled = true;}, releaseLock: () => {unlocked = true;}})};
  h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? {status: 200, body} : undefined;
  h.elements['audit-form'].emit('submit'); await tick();
  assert.equal(reads, 2); assert.ok(cancelled && unlocked); assert.equal(h.elements['audit-events'].children.length, 0);
});

test('logout and role loss discard pending audit and clear its filter', async () => {
  const h = harness({actions: withAudit}); await tick(); let release;
  h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? new Promise(resolve => {release = resolve;}) : undefined;
  h.elements['audit-task'].value = 'T-01'; h.elements['audit-form'].emit('submit'); await tick();
  const pending = auditCalls(h).at(-1);
  h.elements.logout.emit('click'); await tick(); assert.equal(pending.options.signal.aborted, true);
  assert.equal(h.elements['audit-task'].value, '');
  h.state.actions = ['task.read']; h.state.handler = null;
  h.elements['project-input'].value = 'alpha'; h.elements['user-input'].value = 'alice'; h.elements['password-input'].value = 'fixture';
  h.elements.login.emit('submit'); await tick();
  release({status: 200, data: auditPage()}); await tick();
  assert.equal(h.elements['audit-panel'].hidden, true); assert.equal(h.elements['audit-events'].children.length, 0);
});

test('old alpha audit cannot replace history after login into beta', async () => {
  const h = harness({actions: withAudit}); await tick(); let release;
  h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? new Promise(resolve => {release = resolve;}) : undefined;
  h.elements['audit-form'].emit('submit'); await tick();
  h.elements.logout.emit('click'); await tick();
  h.state.project = 'beta'; h.state.user = 'bob'; h.state.tasks = [example({project: 'beta'})];
  const beta = auditPage({project: 'beta'}); beta.events[0].project = 'beta'; beta.events[0].actor = 'bob';
  h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? {status: 200, data: beta} : undefined;
  h.elements['project-input'].value = 'beta'; h.elements['user-input'].value = 'bob'; h.elements['password-input'].value = 'fixture';
  h.elements.login.emit('submit'); await tick(); h.elements['audit-form'].emit('submit'); await tick();
  release({status: 200, data: auditPage()}); await tick();
  assert.equal(h.elements['audit-events'].children[0].children[2].textContent, 'bob');
  assert.match(auditCalls(h).at(-1).url, /project=beta/);
});


test('pause and resume use displayed version and csrf, with status-specific buttons and no conflict replay', async () => {
  for (const [status, label, path] of [['in_progress', 'Pause', '/api/pause'], ['paused', 'Reprendre', '/api/resume']]) {
    const h = harness({tasks: [example({status, version: 7})]}); await tick();
    assert.ok(!h.buttons().some(b => b.textContent === (label === 'Pause' ? 'Reprendre' : 'Pause')));
    h.state.handler = call => call.url === path ? {status: 409} : undefined;
    h.buttons().find(b => b.textContent === label).emit('click'); await tick();
    assert.equal(h.mutations().length, 1);
    assert.equal(h.mutations()[0].url, path);
    assert.equal(h.state.confirmMessage, `${label === 'Pause' ? 'Mettre en pause' : label} T-01 dans alpha ?`);
    assert.deepEqual(JSON.parse(h.mutations()[0].options.body), {project: 'alpha', id: 'T-01', expected_version: 7});
    assert.equal(h.mutations()[0].options.headers['X-CSRF-Token'], h.csrf);
  }
});

test('audit pause/resume labels and transitions are validated', async () => {
  for (const [action, before, after, label] of [['task.pause', 'in_progress', 'paused', 'Pause'], ['task.resume', 'paused', 'in_progress', 'Reprise']]) {
    const h = harness({actions: ['task.read', 'task.audit.read']}); await tick();
    const value = auditPage(); value.events[0].action = action;
    value.events[0].before = {status: before, version: 1}; value.events[0].after = {status: after, version: 2};
    h.state.handler = call => call.url.startsWith('/api/project/task-audit?') ? {status: 200, data: value} : undefined;
    h.elements['audit-form'].emit('submit'); await tick();
    assert.equal(h.elements['audit-events'].children.length, 1);
    assert.match(h.elements['audit-events'].children[0].children[3].textContent, new RegExp(label));
    value.events[0].before.status = 'todo';
    h.elements['audit-form'].emit('submit'); await tick();
    assert.equal(h.elements['audit-events'].children.length, 0);
  }
});
