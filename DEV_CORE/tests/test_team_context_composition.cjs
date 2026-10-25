const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor() { this.children = []; this.textContent = ''; }
  replaceChildren() { this.children = []; this.textContent = ''; }
  append(...items) { this.children.push(...items); }
}

const settled = () => new Promise(resolve => setImmediate(resolve));
const response = project => ({ok:true, json:async () => ({
  project, card:`# Fiche ${project}\nContenu`,
  decisions:[{id:'D-002'}, {id:'D-006'}], warnings:['card_changed_since_review'], omitted:[],
  provenance:{reviewed_at:'2026-10-11'},
  measurement:{unit:'utf8_bytes', used:11901, budget:12000, model_tokens_measured:false}
})});

(async () => {
  const slot = new Element();
  const pending = [];
  const context = {
    window:{devcoreActiveProject:'devcore', devcoreTeamContextSources:{
      repowise:{available:true, indexed_commit:'ce4b464d6566', file_count:427}
    }}, console, URLSearchParams, AbortController,
    document:{
      getElementById:() => null, querySelectorAll:() => [],
      querySelector:selector => selector === '[data-team-context-document]' ? slot : null,
      createElement:() => new Element()
    },
    fetch:(url, options) => new Promise(resolve => pending.push({url, options, resolve}))
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('DEV_CORE/API/devcore_api/team_cockpit_display.js', 'utf8'), context);
  assert.equal(pending.length, 1);
  assert.match(pending[0].url, /project=devcore/);
  assert.equal(pending[0].options.credentials, 'same-origin');

  context.window.devcoreActiveProject = 'alpha';
  context.loadTeamContextComposition();
  assert.equal(pending.length, 2);
  assert.equal(pending[0].options.signal.aborted, true);
  pending[0].resolve(response('devcore'));
  await settled();
  assert.equal(slot.children.length, 0);
  pending[1].resolve(response('alpha'));
  await settled();
  const rows = slot.children.map(row => row.children.map(child => child.textContent).join(': '));
  assert.ok(rows.some(row => row.includes('Fiche alpha')));
  assert.ok(rows.some(row => row.includes('D-002, D-006')));
  assert.ok(rows.some(row => /11\s901 \/ 12\s000 octets UTF-8/.test(row)));
  assert.ok(rows.some(row => row.includes('fiche modifiée depuis sa revue')));
  assert.ok(rows.some(row => row.includes('ce4b464d6566') && row.includes('427 fichiers')));
  context.loadTeamContextComposition();
  assert.equal(pending.length, 2, 'fresh context is reused on a targeted refresh');
  console.log('Project context composition UI checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
