const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.attributes = {}; this.listeners = {}; this.style = {}; this.dataset = {};
    this.classes = new Set();
    this.classList = {
      add: (...values) => values.forEach(value => this.classes.add(value)),
      remove: (...values) => values.forEach(value => this.classes.delete(value)),
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
        {id:'extra',name:'Extra',role:'owner',status:'active',tasks:1,completed_tasks:0,active_tasks:1,tokens:0,can_archive:true},
        {id:'sixth',name:'Sixth',role:'owner',status:'active',tasks:1,completed_tasks:0,active_tasks:1,tokens:0,can_archive:true}]})};
    }
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('DEV_CORE/API/devcore_api/team_cockpit_display.js', 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  let list = panel.children.find(child => child.className === 'team-project-list');
  let cards = list.children;
  let tabs = panel.querySelectorAll('.team-project-tab');
  assert.equal(tabs.length, 2);
  assert.equal(tabs[0].textContent, 'Actifs (5)');
  assert.equal(tabs[1].textContent, 'Archivés (1)');
  assert.equal(tabs[0].getAttribute('aria-selected'), 'true');
  assert.equal(panel.querySelectorAll('.team-project-pagination').length, 0);
  assert.equal(panel.querySelectorAll('.team-project-refresh').length, 0);
  assert.equal(cards.length, 5);
  assert.equal(cards[0].getAttribute('aria-current'), 'page');
  assert.equal(cards[0].children[1].textContent, 'Aucune tâche active · 275 tâches');
  assert.equal(cards[0].children[2].children[0].style.width, '100%');
  assert.equal(cards[0].children[3].children[1].querySelectorAll('button').length, 1);
  assert.equal(cards[1].children[0].children[1].textContent, 'Beta <script>');
  let buttons = cards[1].children[3].children[1].querySelectorAll('button');
  assert.equal(buttons[1].getAttribute('aria-label'), 'Archiver Beta <script>');
  assert.equal(buttons[1].disabled, true);
  assert.equal(buttons[0].children[0].tagName, 'svg');
  tabs[1].listeners.click();
  assert.equal(list.children.length, 1);
  assert.equal(list.children[0].dataset.project, 'old');
  assert.equal(tabs[1].getAttribute('aria-selected'), 'true');
  tabs[0].listeners.click();
  cards = list.children;
  buttons = cards[1].children[3].children[1].querySelectorAll('button');
  await buttons[0].listeners.click();
  assert.equal(destination, '/cockpit/terminal?project=beta');
  assert.equal(calls[1][1].headers['X-CSRF-Token'], 'fixture-csrf');
  assert.deepEqual(JSON.parse(calls[1][1].body), {project:'beta',switch_project:true});
  assert.equal(panel.classList.contains('team-projects-switching'), true);
  assert.equal(cards[1].classList.contains('team-project-pending'), true);
  assert.equal(panel.getAttribute('aria-busy'), 'true');
  await context.loadTeamProjects();
  assert.equal(panel.classList.contains('team-projects-switching'), false);
  list = panel.children.find(child => child.className === 'team-project-list');
  tabs = panel.querySelectorAll('.team-project-tab');
  tabs[1].listeners.click();
  cards = list.children;
  buttons = cards[0].children[3].children[1].querySelectorAll('button');
  assert.equal(buttons[1].getAttribute('aria-label'), 'Désarchiver Old');
  await buttons[1].listeners.click();
  assert.deepEqual(JSON.parse(calls[3][1].body), {project:'old',archive_project:true,archived:false});
  list = panel.children.find(child => child.className === 'team-project-list');
  tabs = panel.querySelectorAll('.team-project-tab');
  tabs[0].listeners.click();
  cards = list.children;
  buttons = cards[2].children[3].children[1].querySelectorAll('button');
  await buttons[1].listeners.click();
  assert.deepEqual(JSON.parse(calls[5][1].body), {project:'contrib',archive_project:true,archived:true});
  console.log('Project navigation UI checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
