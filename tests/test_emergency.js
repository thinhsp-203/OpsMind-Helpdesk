const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/app.js', 'utf8');
const html = fs.readFileSync('app/static/index.html', 'utf8');

function harness() {
  const button = {disabled: false};
  const form = {dataset: {}, reset() {}, querySelector: () => button};
  const fields = new Map([
    ['emergencyTicketForm', form],
    ['emergencyTitleInput', {value: 'Synthetic security incident'}],
    ['emergencyDescriptionInput', {value: 'AUD12 synthetic suspicious login'}],
    ['emergencyModal', {classList: {add() {}, remove() {}}}],
  ]);
  const messages = [];
  const requests = [];
  const timers = [];
  const context = {
    byId: id => fields.get(id),
    window: {helpdeskI18n: {translate: value => value}},
    setMessage: (id, text, isError) => messages.push({text, isError}),
    setTimeout: callback => timers.push(callback),
    refreshWorkspace: async () => {},
    api: async (path, options) => {requests.push({path, payload: JSON.parse(options.body)}); return {ticket: {id: 42}};},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('function openEmergencyModal('), source.indexOf('async function refreshWorkspace(')), context);
  return {context, button, form, messages, requests, timers, fields,
    submit: () => context.handleEmergencyTicket({preventDefault() {}, currentTarget: form})};
}

(async () => {
  const normal = harness();
  await normal.submit();
  assert.ok(normal.messages.some(message => message.text.includes('HD-0042')), 'Use API result.ticket.id');
  assert.equal(normal.requests[0].payload.priority, 'urgent');
  assert.equal(normal.requests[0].payload.category, 'security');
  assert.ok(!normal.requests[0].payload.description.includes('SOC'));
  assert.ok(normal.messages.some(message => message.text.includes('Chưa có xác nhận gửi thông báo')));
  assert.ok(!normal.messages.some(message => /SOC đang tiếp nhận|Đã phát cảnh báo|HD-undefined/.test(message.text)));
  assert.equal(normal.timers.length, 0, 'Keep receipt visible until user closes modal');
  await normal.submit();
  assert.equal(normal.requests.length, 1, 'A displayed receipt must prevent accidental repeat submit');

  for (const response of [{}, {ticket: {}}, {ticket: {id: 'bad'}}, {ticket: {id: -1}}]) {
    const malformed = harness();
    malformed.context.api = async () => response;
    await malformed.submit();
    assert.ok(!malformed.messages.some(message => /HD-|Đã tạo ticket/.test(message.text)));
    assert.ok(malformed.messages.some(message => message.text.includes('Kiểm tra danh sách')));
  }

  // Channel state is absent from this API contract; do not infer a delivery receipt.
  for (const delivery of [undefined, {}, {telegram: false}, {discord: false}, {telegram: true}]) {
    const channel = harness();
    channel.context.api = async () => ({ticket: {id: 51}, delivery});
    await channel.submit();
    assert.ok(channel.messages.some(message => message.text.includes('HD-0051') && message.text.includes('Chưa có xác nhận')));
  }

  const failed = harness();
  failed.context.api = async () => {throw new Error('Synthetic API timeout');};
  await failed.submit();
  assert.ok(!failed.messages.some(message => message.text.includes('Đã tạo ticket')));
  assert.equal(failed.button.disabled, false);

  const refreshFailure = harness();
  refreshFailure.context.refreshWorkspace = async () => {throw new Error('Synthetic refresh failure');};
  await refreshFailure.submit();
  assert.ok(refreshFailure.messages.at(-1).text.includes('HD-0042'), 'Refresh error must preserve successful creation receipt');

  const concurrent = harness();
  let release;
  let calls = 0;
  concurrent.context.api = async () => {calls++; return new Promise(resolve => {release = resolve;});};
  const first = concurrent.submit();
  await concurrent.submit();
  assert.equal(calls, 1);
  release({ticket: {id: 73}});
  await first;

  assert.ok(!/SOC 24\/7|Active Directory|Cổng VPN|Phát cảnh báo P1 đến IT\/SOC/.test(html));
  console.log('Emergency receipt, errors, duplicates and unsupported integration claims: PASS');
})().catch(error => {console.error(error); process.exitCode = 1;});
