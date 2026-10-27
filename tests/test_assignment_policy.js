const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/app.js', 'utf8');

function element() {
  return {children: [], listeners: {}, disabled: false, value: '',
    append(...items) {this.children.push(...items);},
    setAttribute() {}, addEventListener(name, callback) {this.listeners[name] = callback;}};
}

(async () => {
  for (const status of ['new', 'in_progress', 'pending_waiting_user', 'escalated', 'resolved', 'closed']) {
    const requests = [];
    const context = {
      node: () => element(), document: {createElement: () => element()},
      state: {staff: [{username: 'agent', role: 'agent'}, {username: 'admin', role: 'admin'}]},
      transitions: {new: ['in_progress'], in_progress: ['resolved'], pending_waiting_user: ['in_progress'], escalated: [], resolved: ['in_progress', 'closed'], closed: []},
      statusLabels: {}, roleLabels: {}, window: {helpdeskI18n: {translate: text => text}},
      setWorkspaceView() {}, askKnowledge() {}, alertUser() {}, refreshWorkspace: async () => {},
      api: async (...args) => {requests.push(args);},
    };
    vm.createContext(context);
    vm.runInContext(source.slice(source.indexOf('function createStaffActions('), source.indexOf('async function loadAudit(')), context);
    const actions = context.createStaffActions({id: 14, status, assignee: 'agent', title: 'Synthetic', description: 'AUD14'});
    const select = actions.children[3], button = actions.children[4];
    const frozen = ['resolved', 'closed'].includes(status);
    assert.equal(Boolean(select.disabled), frozen, status);
    select.value = 'admin';
    select.listeners.change();
    assert.equal(button.disabled, frozen, status);
    await button.listeners.click();
    assert.equal(requests.length, frozen ? 0 : 1, status);
    if (!frozen) assert.equal(JSON.parse(requests[0][1].body).assignee, 'admin');
  }
  console.log('Assignment controls: completed read-only; active assignment preserved: PASS');
})().catch(error => {console.error(error); process.exitCode = 1;});
