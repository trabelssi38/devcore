const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.attributes = {}; this.listeners = {}; this.style = {}; this.dataset = {};
    this.classes = new Set();
    this.classList = {
      add: value => this.classes.add(value),
      remove: value => this.classes.delete(value),
      contains: value => this.classes.has(value),
      toggle: (value, force) => force === undefined
        ? (this.classes.has(value) ? this.classes.delete(value) : this.classes.add(value))
        : (force ? this.classes.add(value) : this.classes.delete(value))
    };
  }
  append(...elements) { this.children.push(...elements); }
  replaceChildren() { this.children = []; }
  setAttribute(key, value) { this.attributes[key] = value; }
  getAttribute(key) { return this.attributes[key]; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  querySelectorAll(selector) {
    const matches = [];
    const visit = element => {
      for (const child of element.children) {
        if (selector.startsWith('.') ? child.className?.split(' ').includes(selector.slice(1)) : child.tagName === selector) matches.push(child);
        visit(child);
      }
    };
    visit(this);
    return matches;
  }
}
(async () => {
  const panel = new Element('nav');
  const calls = [];
  let destination;
  const context = {
    window: {}, URLSearchParams,
    document: {getElementById: id => id === 'team-projects' ? panel : null,
               querySelectorAll: () => [], createElement: tag => new Element(tag), createElementNS: (_ns, tag) => new Element(tag)},
    location: {pathname:'/cockpit/terminal', assign: value => destination = value},
    teamFetch: async (url, options) => {
      calls.push([url, options]);
      return {ok:true, json:async () => ({project:'alpha', csrf_token:'fixture-csrf', projects:[
        {id:'alpha',name:'Alpha',role:'owner',status:'active',tasks:275,completed_tasks:275,active_tasks:0,tokens:0,can_archive:true},
        {id:'old',name:'Old',role:'contributor',status:'archived',tasks:0,completed_tasks:0,active_tasks:0,tokens:0,can_archive:true},
        {id:'beta',name:'Beta <script>',role:'reader',status:'needs_review',tasks:2,completed_tasks:1,active_tasks:1,tokens:7,can_archive:false},
        {id:'contrib',name:'Contributor',role:'contributor',status:'active',tasks:5,completed_tasks:3,active_tasks:1,tokens:12,can_archive:true},
        {id:'extra',name:'Extra',role:'owner',status:'active',tasks:1,completed_tasks:0,active_tasks:1,tokens:0,can_archive:true}]})};
    }
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('DEV_CORE/API/devcore_api/team_cockpit_display.js', 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  let list = panel.children.find(child => child.className === 'team-project-list');
  let cards = list.children;
  assert.equal(cards.length, 4);
  assert.equal(cards[0].children[1].textContent, 'Actif · Aucune tâche active · 275 tâches');
  assert.equal(cards[0].children[2].children[0].style.width, '100%');
  assert.equal(cards[1].children[1].textContent, 'Archivé · Aucune tâche active · 0 tâches');
  assert.equal(cards[2].children[0].children[1].textContent, 'Beta <script>');
  let buttons = cards[2].children[4].querySelectorAll('button');
  assert.equal(buttons[1].getAttribute('aria-label'), 'Archiver Beta <script>');
  assert.equal(buttons[1].disabled, true);
  assert.equal(buttons[0].children[0].tagName, 'svg');
  const nextPage = panel.querySelectorAll('.team-project-next')[0];
  nextPage.listeners.click();
  assert.equal(list.children.length, 1);
  assert.equal(list.children[0].dataset.project, 'extra');
  assert.equal(panel.querySelectorAll('.team-project-page-label')[0].textContent, '2 / 2');
  panel.querySelectorAll('.team-project-previous')[0].listeners.click();
  cards = list.children;
  buttons = cards[2].children[4].querySelectorAll('button');
  await buttons[0].listeners.click();
  assert.equal(destination, '/cockpit/terminal?project=beta');
  assert.equal(calls[1][1].headers['X-CSRF-Token'], 'fixture-csrf');
  assert.deepEqual(JSON.parse(calls[1][1].body), {project:'beta',switch_project:true});
  assert.equal(panel.classList.contains('team-projects-switching'), true);
  assert.equal(panel.children.find(child => child.className === 'team-project-refresh').textContent,
    'Actualisation des données de Beta <script>…');
  await context.loadTeamProjects();
  list = panel.children.find(child => child.className === 'team-project-list');
  cards = list.children;
  buttons = cards[1].children[4].querySelectorAll('button');
  assert.equal(buttons[1].getAttribute('aria-label'), 'Désarchiver Old');
  await buttons[1].listeners.click();
  assert.deepEqual(JSON.parse(calls[3][1].body), {project:'old',archive_project:true,archived:false});
  cards = list.children;
  buttons = cards[3].children[4].querySelectorAll('button');
  await buttons[1].listeners.click();
  assert.deepEqual(JSON.parse(calls[5][1].body), {project:'contrib',archive_project:true,archived:true});
  console.log('Project navigation UI checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
