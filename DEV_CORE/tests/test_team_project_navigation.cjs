const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag) { this.tagName = tag; this.children = []; this.attributes = {}; this.listeners = {}; }
  append(...elements) { this.children.push(...elements); }
  replaceChildren() { this.children = []; }
  setAttribute(key, value) { this.attributes[key] = value; }
  getAttribute(key) { return this.attributes[key]; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  querySelectorAll(tag) { return this.children.filter(child => child.tagName === tag); }
}
(async () => {
  const panel = new Element('nav');
  const calls = [];
  let destination;
  const context = {
    window: {}, URLSearchParams,
    document: {getElementById: id => id === 'team-projects' ? panel : null,
               querySelectorAll: () => [], createElement: tag => new Element(tag)},
    location: {pathname:'/cockpit/terminal', assign: value => destination = value},
    teamFetch: async (url, options) => {
      calls.push([url, options]);
      return {ok:true, json:async () => ({project:'alpha', csrf_token:'fixture-csrf', projects:[
        {id:'alpha',name:'Alpha',role:'owner'}, {id:'beta',name:'Beta <script>',role:'reader'}]})};
    }
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('DEV_CORE/API/devcore_api/team_cockpit_display.js', 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  let buttons = panel.querySelectorAll('button');
  assert.equal(buttons.length, 2);
  assert.equal(buttons[0].disabled, true);
  assert.equal(buttons[1].textContent, 'Beta <script>');
  await buttons[1].listeners.click();
  assert.equal(destination, '/cockpit/terminal?project=beta');
  assert.equal(calls[1][1].headers['X-CSRF-Token'], 'fixture-csrf');
  assert.deepEqual(JSON.parse(calls[1][1].body), {project:'beta',switch_project:true});
  await context.loadTeamProjects();
  context.teamFetch = async () => ({ok:false});
  buttons = panel.querySelectorAll('button');
  await buttons[1].listeners.click();
  assert.equal(buttons[0].disabled, true);
  assert.equal(buttons[1].disabled, false);
  assert.equal(panel.children.at(-1).textContent, 'Changement de projet refusé');
  console.log('Project navigation UI checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
