const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Execute the actual keyboard handler with IME, multiline, and busy scenarios.
const source = fs.readFileSync(path.join(__dirname, '../app/static/app.js'), 'utf8');
const handlerSource = source.slice(source.indexOf('byId("ragQuestion").addEventListener("keydown"'));
assert(handlerSource.startsWith('byId("ragQuestion")'));
let handler, submitted = 0, prevented = 0;
const state = {ragBusy: false};
vm.runInNewContext(handlerSource, {
  state,
  byId: id => id === 'ragQuestion'
    ? {addEventListener: (name, callback) => {assert.equal(name, 'keydown'); handler = callback;}}
    : {requestSubmit: () => submitted++},
});
const press = overrides => handler({key: 'Enter', shiftKey: false, isComposing: false,
  preventDefault: () => prevented++, ...overrides});
press({shiftKey: true});
press({isComposing: true});
press({keyCode: 229});
press({key: 'a'});
assert.equal(submitted, 0);
assert.equal(prevented, 0);
press({});
assert.equal(submitted, 1);
state.ragBusy = true;
press({});
assert.equal(submitted, 1);
assert.equal(prevented, 2);
console.log('Assistant keyboard: Enter, multiline, IME and duplicate submission guard PASS');
