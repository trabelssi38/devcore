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
  removeAttribute(key) { delete this.attributes[key]; }
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
  const taskPanel = new Element('section');
  taskPanel.innerHTML = 'Tasks alpha';
  const globalPanel = new Element('section');
  globalPanel.innerHTML = 'Global services';
  const profile = new Element('details');
  profile.contains = () => false;
  const profileProject = new Element('strong');
  const logout = new Element('a');
  const profileError = new Element('p');
  const calls = [];
  let destination;
  let logoutDestination;
  let currentProject = 'alpha';
  let pageReplacements = 0;
  let logoutDenied = true;
  const updatedSections = [];
  const context = {
    window: {}, console, URLSearchParams, AbortController, setTimeout, clearTimeout,
    history: {replaceState: (_state, _title, url) => destination = url},
    readDashboardJson: async response => response.json(),
    validateDashboardSnapshot: () => {},
    checkDashboardResponseAccess: () => {},
    updateContainerHTML: (id, html) => { updatedSections.push(id); taskPanel.innerHTML = html; },
    updateTokenReport: () => {}, updateRepowiseHealth: () => {},
    recordAppliedDashboardSnapshot: () => {},
    refreshDashboard: () => context.performDashboardRefresh(),
    document: {getElementById: id => ({'team-projects':panel,'tasks-pipeline':taskPanel,
      'global-only-panel':globalPanel,'team-profile':profile,'team-logout':logout,
      'team-profile-error':profileError})[id] || null,
               addEventListener: () => {},
               querySelector: selector => selector === '[data-team-profile-project]' ? profileProject : null,
               querySelectorAll: () => [],
               createElement: tag => new Element(tag), createElementNS: (_ns, tag) => new Element(tag)},
    location: {pathname:'/cockpit/terminal', search:'?project=alpha', assign: value => {
      pageReplacements++; logoutDestination = value;
    }},
    teamFetch: async (url, options) => {
      calls.push([url, options]);
      if (String(url).startsWith('/api/dashboard?')) {
        const project = new URLSearchParams(String(url).split('?')[1]).get('project');
        return {ok:true, json:async () => ({project, sections:{tasks_pipeline:`Tasks ${project}`},
          task_details:{},task_interactions:{},token_metrics:{},counts:{tasks:2},service_health:{}})};
      }
      if (options?.method === 'DELETE') return {ok:!logoutDenied};
      if (options?.method === 'POST' && JSON.parse(options.body).switch_project) currentProject = JSON.parse(options.body).project;
      return {ok:true, json:async () => ({project:currentProject, csrf_token:'fixture-csrf', projects:[
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
  assert.equal(panel.querySelectorAll('h3').length, 0);
  assert.equal(cards.length, 5);
  assert.equal(cards[0].getAttribute('aria-current'), 'page');
  assert.equal(cards[0].children[1].textContent, 'Aucune tâche active · 275 tâches');
  assert.equal(cards[0].children[2].children[0].style.width, '100%');
  assert.equal(cards[0].children[3].children[1].querySelectorAll('button').length, 2);
  assert.equal(cards[0].children[3].children[1].querySelectorAll('button')[0].disabled, true);
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
  const originalList = list;
  const originalCard = cards[1];
  buttons = cards[1].children[3].children[1].querySelectorAll('button');
  await buttons[0].listeners.click();
  assert.equal(destination, '/cockpit/terminal?project=beta');
  assert.equal(pageReplacements, 0);
  assert.equal(panel.children.find(child => child.className === 'team-project-list'), originalList);
  assert.equal(list.children[1], originalCard);
  assert.equal(originalCard.getAttribute('aria-current'), 'page');
  assert.equal(list.children[0].getAttribute('aria-current'), undefined);
  assert.equal(list.children[0].children[3].children[1].querySelectorAll('button')[0].disabled, false);
  assert.equal(originalCard.children[3].children[1].querySelectorAll('button')[0].disabled, true);
  assert.equal(list.children[2].children[3].children[1].querySelectorAll('button')[0].getAttribute('aria-label'), 'Ouvrir Contributor');
  assert.equal(list.children[2].children[3].children[1].querySelectorAll('button')[1].getAttribute('aria-label'), 'Archiver Contributor');
  assert.equal(list.children[2].children[3].children[1].querySelectorAll('button')[0].disabled, false);
  assert.equal(context.window.devcoreActiveProject, 'beta');
  assert.equal(profileProject.textContent, 'beta');
  assert.deepEqual(updatedSections, ['tasks-pipeline']);
  assert.equal(taskPanel.innerHTML, 'Tasks beta');
  assert.equal(globalPanel.innerHTML, 'Global services');
  assert.equal(calls[1][1].headers['X-CSRF-Token'], 'fixture-csrf');
  assert.deepEqual(JSON.parse(calls[1][1].body), {project:'beta',switch_project:true});
  assert.equal(panel.classList.contains('team-projects-switching'), false);
  assert.equal(panel.getAttribute('aria-busy'), 'false');
  await context.loadTeamProjects();
  assert.equal(panel.classList.contains('team-projects-switching'), false);
  list = panel.children.find(child => child.className === 'team-project-list');
  tabs = panel.querySelectorAll('.team-project-tab');
  tabs[1].listeners.click();
  cards = list.children;
  buttons = cards[0].children[3].children[1].querySelectorAll('button');
  assert.equal(buttons[1].getAttribute('aria-label'), 'Désarchiver Old');
  await buttons[1].listeners.click();
  assert.deepEqual(JSON.parse(calls.filter(call => call[1]?.method === 'POST')[1][1].body), {project:'old',archive_project:true,archived:false});
  list = panel.children.find(child => child.className === 'team-project-list');
  tabs = panel.querySelectorAll('.team-project-tab');
  tabs[0].listeners.click();
  cards = list.children;
  buttons = cards[2].children[3].children[1].querySelectorAll('button');
  await buttons[1].listeners.click();
  assert.deepEqual(JSON.parse(calls.filter(call => call[1]?.method === 'POST')[2][1].body), {project:'contrib',archive_project:true,archived:true});
  await logout.listeners.click({preventDefault() {}});
  assert.equal(pageReplacements, 0);
  assert.equal(profileError.textContent, 'Déconnexion impossible');
  assert.equal(logout.dataset.busy, 'false');
  logoutDenied = false;
  await logout.listeners.click({preventDefault() {}});
  const deletion = calls.find(call => call[1]?.method === 'DELETE');
  assert.equal(deletion[1].headers['X-CSRF-Token'], 'fixture-csrf');
  assert.equal(logoutDestination, '/login?project=beta');
  console.log('Project navigation UI checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
