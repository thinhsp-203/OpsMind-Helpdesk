const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/app.js', 'utf8');
function element() {
  return {children: [], listeners: {}, value: '', append(...items) {this.children.push(...items);},
    setAttribute() {}, addEventListener(event, callback) {this.listeners[event] = callback;}};
}
(async () => {
  const requests = [], alerts = [];
  let refreshes = 0;
  const context = {
    node: () => element(), document: {createElement: () => element()},
    state: {staff: []}, transitions: {in_progress: ['resolved']}, statusLabels: {}, roleLabels: {},
    window: {confirm: () => true, helpdeskI18n: {translate: value => value}},
    setWorkspaceView() {}, askKnowledge() {}, alertUser: message => alerts.push(message),
    refreshWorkspace: async () => {refreshes++;},
    api: async (...args) => {requests.push(args);},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('function createStaffActions('), source.indexOf('async function loadAudit(')), context);
  vm.runInContext(source.slice(source.indexOf('async function changeTicketStatus('), source.indexOf('async function uploadAttachment(')), context);
  const controls = context.createStaffActions({id: 23, status: 'in_progress', assignee: '', title: 'Sandbox'});
  controls.children[1].value = 'resolved';
  await controls.children[2].listeners.click();
  assert.deepEqual(JSON.parse(requests.at(-1)[1].body), {status: 'resolved', expected_status: 'in_progress'});
  await context.changeTicketStatus(23, 'closed', 'resolved');
  assert.deepEqual(JSON.parse(requests.at(-1)[1].body), {status: 'closed', expected_status: 'resolved'});
  context.api = async () => {throw new Error('409: stale state; refresh');};
  await context.changeTicketStatus(23, 'in_progress', 'resolved');
  assert.equal(refreshes, 2);
  assert.equal(alerts.at(-1), '409: stale state; refresh');
  // Requester callbacks must pass the status shown in the ticket card.
  assert.ok(source.includes('changeTicketStatus(ticket.id, "closed", ticket.status)'));
  assert.ok(source.includes('changeTicketStatus(ticket.id, "in_progress", ticket.status)'));
  console.log('AUD23 status controls send displayed expected_status and surface conflicts: PASS');
})().catch(error => {console.error(error); process.exitCode = 1;});
