// Exercise the rendered controls and requests, not source regex assertions.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/app.js', 'utf8');
class Element {
  constructor(tag, text = '') { this.tag = tag; this.textContent = text; this.children = []; this.listeners = {}; this.dataset = {}; this.value = ''; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(key, value) { this[key] = value; }
  addEventListener(key, callback) { this.listeners[key] = callback; }
}
const find = (element, predicate) => predicate(element) ? element : element.children.map(child => find(child, predicate)).find(Boolean);
const flush = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  const calls = [], fields = {}, actions = [];
  let loseResponse = true;
  const ticket = {id: 47, title: 'Máy in Offline', category: 'hardware', priority: 'medium', status: 'new'};
  const context = {
    state: {token: 'synthetic', user: {role: 'user'}}, crypto: {randomUUID: () => 'fixed-request-key-0001'},
    node: (tag, cls, text) => new Element(tag, text),
    byId: id => fields[id] ||= {value: '', focus() {}},
    categoryLabels: {hardware: 'Phần cứng'}, priorityLabels: {medium: 'Thông thường'}, statusLabels: {new: 'Mới'},
    buildHandoffDescription: question => question,
    clearTicketFilters() { context.state.focusedTicketId = null; },
    setWorkspaceView() {}, async loadTickets() { actions.push(context.state.focusedTicketId); },
    async refreshWorkspace() {}, alertUser(message) { throw Error(message); },
    askKnowledge(_, options) { actions.push(options); },
    async api(url, options) {
      calls.push({url, options});
      if (url === '/tickets' && loseResponse) { loseResponse = false; throw Error('synthetic response lost'); }
      return {ticket};
    },
  };
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('function renderDiagnosticControls('), source.indexOf('function addTicketHandoff(')), context);
  const container = new Element('div'), button = new Element('button');
  await context.createAssistantTicket(container, button, 'Máy in Offline', ticket.title,
    {category: 'hardware', priority: 'medium'}, {handoff: {title: ticket.title, description: 'Dữ kiện và thông tin chưa xác minh'}}, 'Thông thường');
  assert.equal(calls.length, 0, 'Preview must not send a ticket');
  const description = find(container, e => e.tag === 'textarea');
  description.value = 'Tôi xác nhận đã kiểm tra nguồn; máy vẫn Offline.';
  find(container, e => e.textContent === 'Xác nhận gửi ticket').listeners.click();
  await flush();
  const sent = JSON.parse(calls[0].options.body);
  assert.equal(sent.description, description.value);
  assert.equal(sent.request_key, 'fixed-request-key-0001');
  find(container, e => e.textContent === 'Kiểm tra kết quả và thử lại').listeners.click();
  await flush();
  assert.equal(calls[1].url, '/ticket-requests/fixed-request-key-0001');
  assert.equal(calls.filter(c => c.url === '/tickets').length, 1, 'Recovered request must not POST again');
  await find(container, e => e.textContent === 'Ticket IT của tôi đến đâu?').listeners.click();
  assert.equal(actions.at(-1), 47, 'Follow exact ID regardless of title');
  const result = new Element('div');
  context.renderDiagnosticControls(result, {state: 'CHECK_RESULT', steps: [{id: 'observe'}], attempted_steps: [{id: 'observe', result: 'attempted_failure'}]});
  find(result, e => e.textContent === 'Xác nhận chức năng hiện đã hoạt động').listeners.click();
  assert.equal(actions.at(-1).action, 'confirm_resolved');
  assert.equal(actions.at(-1).stepResults.observe, 'attempted_failure');
  const previousActions = actions.length;
  context.state.diagnosticTurn = 2;
  find(result, e => e.textContent === 'Xác nhận chức năng hiện đã hoạt động').listeners.click();
  assert.equal(actions.length, previousActions, 'Stale result controls must not send an action');
  console.log('Assistant preview, lost response recovery, exact ticket and explicit outcome PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
