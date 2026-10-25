const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function between(source, start, end) {
  const first = source.indexOf(start);
  const last = source.indexOf(end, first);
  assert.ok(first >= 0 && last > first, `Missing stream code: ${start}`);
  return source.slice(first, last);
}

async function main() {
  const terminal = fs.readFileSync('DEV_CORE/Dashboard/template_terminal.html', 'utf8');
  const connections = [];
  let terminalRefreshes = 0;
  class FakeEventSource {
    constructor(url) { this.url = url; connections.push(this); }
    addEventListener() {}
  }
  const terminalContext = {
    EventSource: FakeEventSource, console,
    window: {devcoreActiveProject: 'devcore'},
    refreshDashboardForSse: () => { terminalRefreshes++; }
  };
  vm.createContext(terminalContext);
  vm.runInContext(between(terminal, 'function connectStream() {', 'function showInteractions('), terminalContext);
  terminalContext.connectStream();
  assert.equal(connections[0].url, '/api/dashboard/stream?project=devcore');
  connections[0].onopen();
  assert.equal(terminalRefreshes, 0, 'Initial snapshot needs no duplicate fetch');
  connections[0].onerror();
  connections[0].onopen();
  assert.equal(terminalRefreshes, 1, 'Native SSE reconnect must refresh the selected project');

  const standard = fs.readFileSync('DEV_CORE/Dashboard/template.html', 'utf8');
  const urls = [];
  let standardRefreshes = 0;
  const standardContext = {
    API_BASE: '', AbortController, TextDecoder, console,
    window: {ReadableStream: true, devcoreActiveProject: 'devcore'},
    dashboardStreamAbort: null, dashboardStreamRetryId: null,
    dashboardLastEventId: null, dashboardAppliedSnapshotCursor: null,
    refreshDashboardForSse: () => { standardRefreshes++; },
    setTimeout, clearTimeout,
    fetch: async url => {
      urls.push(url);
      return {ok: true, body: {getReader: () => ({read: () => new Promise(() => {})})}};
    }
  };
  vm.createContext(standardContext);
  vm.runInContext(between(standard, 'let dashboardStreamConnected = false;', 'function startDashboardSynchronization()'), standardContext);
  standardContext.connectDashboardStream();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(standardRefreshes, 0);
  standardContext.dashboardStreamAbort = null; // Simulate the closed first stream.
  standardContext.connectDashboardStream();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(standardRefreshes, 1, 'Stream reconnect must refresh the selected project');
  assert.deepEqual(urls, [
    '/api/dashboard/stream?project=devcore',
    '/api/dashboard/stream?project=devcore'
  ]);
  console.log('Dashboard stream reconnect checks passed');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
