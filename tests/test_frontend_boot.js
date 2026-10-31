// Load the exact classic-script graph from index.html in one browser-like global.
// Separate node --check calls cannot detect cross-script lexical redeclarations.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'app/static/index.html'), 'utf8');
assert.match(html, /<section id="adminNotificationsPanel"[^>]*>[\s\S]*?id="serviceStateLabel"[\s\S]*?<\/section>/,
  'Service health belongs in admin notifications');
assert.equal((html.match(/id="serviceStateLabel"/g) || []).length, 1);
const scripts = [...html.matchAll(/<script\b[^>]*src="([^"]+)"[^>]*>/g)]
  .map(match => path.join(root, 'app', match[1].split('?')[0]));

class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase();
    this.nodeType = 1;
    this.value = '';
    this.textContent = '';
    this.dataset = {};
    this.style = {};
    this.children = [];
    this.listeners = new Map();
    this.attributes = new Map();
    const classes = new Set(['hidden']);
    this.classList = {
      add: (...names) => names.forEach(name => classes.add(name)),
      remove: (...names) => names.forEach(name => classes.delete(name)),
      contains: name => classes.has(name),
      toggle(name, force = !classes.has(name)) {
        if (force) classes.add(name); else classes.delete(name);
        return force;
      },
    };
  }
  append(...children) { this.children.push(...children); }
  prepend(...children) { this.children.unshift(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, handler) { this.listeners.set(name, handler); }
  setAttribute(name, value) { this.attributes.set(name, value); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  hasAttribute(name) { return this.attributes.has(name); }
  removeAttribute(name) { this.attributes.delete(name); }
  querySelectorAll() { return []; }
  querySelector() { return new Element('button'); }
  focus() {}
  reset() {}
  scrollIntoView() {}
}

async function boot(role, restore) {
  const fields = new Map([...html.matchAll(/\bid="([^"]+)"/g)]
    .map(match => [match[1], new Element()]));
  const requests = [];
  const errors = [];
  const profile = {username: role, role, activity: {}};
  const storage = new Map();
  const token = `header.${Buffer.from(JSON.stringify({sub: role, role})).toString('base64url')}.signature`;
  if (restore) storage.set('helpdesk-token', token);
  const context = {
    Headers, FormData, URLSearchParams, Intl, atob,
    console: {error: (...args) => errors.push(args), log() {}},
    Node: {ELEMENT_NODE: 1, TEXT_NODE: 3},
    NodeFilter: {SHOW_TEXT: 4},
    MutationObserver: class { observe() {} },
    Event: class { constructor(type) { this.type = type; } },
    document: {
      body: new Element('body'), documentElement: {},
      getElementById: id => fields.get(id) || null,
      querySelectorAll: () => [], querySelector: () => null,
      createElement: tag => new Element(tag),
      createTextNode: text => ({nodeType: 3, textContent: text}),
      createDocumentFragment: () => new Element(),
      createTreeWalker: () => ({nextNode: () => null}),
      addEventListener() {},
    },
    localStorage: {
      getItem: key => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: key => storage.delete(key),
    },
    location: {hash: '', pathname: '/'}, history: {replaceState() {}},
    addEventListener() {}, dispatchEvent() {},
    setTimeout: () => 1, clearTimeout() {}, setInterval: () => 1,
    alert: message => errors.push(message), confirm: () => true,
    async fetch(url, options = {}) {
      requests.push({url, options});
      let data = [];
      if (url === '/config') data = {demo_mode: true};
      else if (url === '/health') data = {status: 'ok'};
      else if (url === '/auth/me') data = profile;
      else if (url === '/auth/login') data = {...profile, token, force_password_change: false};
      else if (url === '/analytics') data = {
        total_tickets: 0, status_breakdown: {}, category_breakdown: {},
        overdue_tickets: 0, average_resolution_hours: null, average_rating: null,
        rating_count: 0, daily_created: {}, agent_performance: [], recent_activity: [],
      };
      else if (url === '/analytics/agents/me') data = {category_breakdown: {}};
      else if (url === '/admin/notifications/status') data = {history: []};
      return {ok: true, status: 200, json: async () => data};
    },
  };
  // window must be the global object, as it is for real classic scripts.
  context.window = context;
  vm.createContext(context);
  for (const script of scripts) {
    vm.runInContext(fs.readFileSync(script, 'utf8'), context, {filename: script});
    // Allow immediate API responses between scripts, just like cached resources.
    await new Promise(resolve => setImmediate(resolve));
  }
  if (!restore) {
    fields.get('username').value = role;
    fields.get('password').value = 'synthetic-password';
    const submit = fields.get('loginForm').listeners.get('submit');
    assert.equal(typeof submit, 'function', 'Login handler must be registered');
    await submit({preventDefault() {}});
  }
  // Drain the finite startup fetch chain (refreshWorkspace is not awaited by UI).
  for (let n = 0; n < 8; n++) await new Promise(resolve => setImmediate(resolve));
  assert.equal(requests.some(r => r.url === '/health'), role === 'admin',
    'Only admin should poll service health');
  assert.equal(context.state.user?.role, role);
  assert.equal(fields.get('workspaceView').classList.contains('hidden'), false);
  assert(requests.some(r => r.url.startsWith('/tickets')));
  const markdown = context.renderRunbook('# Heading\n\n- Safe **text**');
  assert.equal(markdown.children.length, 2, 'Exported markdown renderer must execute');
  if (role !== 'user') {
    assert(requests.some(r => r.url === '/knowledge'), 'Staff KB must load on startup');
    await fields.get('openCreateKnowledgeBtn').listeners.get('click')();
    assert.equal(fields.get('knowledgeEditorModal').classList.contains('hidden'), false);
    assert(fields.get('editDocPreview').children.length > 0, 'Editor preview must render');
    await fields.get('editDocContent').listeners.get('input')();
    await fields.get('knowledgeEditorForm').listeners.get('submit')({preventDefault() {}});
    assert(requests.some(r => r.url === '/knowledge' && r.options.method === 'POST'),
      'Bound editor submit must delegate to the module');
  }
  if (role === 'admin') {
    assert(requests.some(r => r.url === '/admin/users'));
    assert(requests.some(r => r.url === '/admin/notifications/status'));
    await fields.get('refreshNotificationsBtn').listeners.get('click')();
  }
  assert.deepEqual(errors, [], 'Startup and module handlers must not swallow errors');
}

(async () => {
  for (const role of ['user', 'agent', 'admin']) {
    await boot(role, false);
    await boot(role, true);
  }
  console.log('Frontend boot passed: actual script order, login/session restore for 3 roles, markdown, KB editor and admin notifications.');
})().catch(error => { console.error(error); process.exitCode = 1; });
