const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/app.js', 'utf8');

function harness() {
  const state = {token: 'AUD15-synthetic-copied-token'}, messages = [], requests = [], timers = [];
  let cleared = 0;
  const context = {
    state, AbortController,
    signOut: () => {cleared++; state.token = '';},
    setMessage: (id, text, error) => messages.push({text, error}),
    setTimeout: callback => {timers.push(callback); return 1;}, clearTimeout() {},
    fetch: async (url, options) => {requests.push({url, options}); return {ok: true, status: 200, json: async () => ({revoked: true})};},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('async function logout('), source.indexOf('function signOut(')), context);
  return {context, state, messages, requests, timers, cleared: () => cleared};
}

(async () => {
  const good = harness();
  await good.context.logout();
  assert.equal(good.requests[0].url, '/auth/logout');
  assert.equal(good.requests[0].options.headers.Authorization, 'Bearer AUD15-synthetic-copied-token');
  assert.equal(good.state.token, '');
  assert.ok(good.messages.at(-1).text.includes('thu hồi các phiên'));
  assert.equal(good.cleared(), 1);
  for (const response of [{ok: false, status: 503}, {ok: true, status: 200, json: async () => ({})}]) {
    const failed = harness();
    failed.context.fetch = async () => response;
    await failed.context.logout();
    assert.equal(failed.state.token, '');
    assert.ok(failed.messages.at(-1).text.includes('chưa xác nhận'));
    assert.equal(failed.state.logoutBusy, false);
  }
  for (const response of [{status: 401}, {ok: true, status: 200, json: async () => ({revoked: false})}]) {
    const revoked = harness();
    revoked.context.fetch = async () => response;
    await revoked.context.logout();
    assert.ok(revoked.messages.at(-1).text.includes('không còn hiệu lực'));
  }
  const timeout = harness();
  timeout.context.fetch = (url, options) => new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new Error('synthetic timeout'))));
  const waiting = timeout.context.logout();
  timeout.timers[0]();
  await waiting;
  assert.ok(timeout.messages.at(-1).text.includes('chưa xác nhận'));

  const race = harness();
  let release, calls = 0;
  race.context.fetch = () => {calls++; return new Promise(resolve => {release = resolve;});};
  const first = race.context.logout();
  await race.context.logout();
  assert.equal(calls, 1);
  race.state.token = 'AUD15-new-login';
  release({ok: true, status: 200, json: async () => ({revoked: true})});
  await first;
  assert.equal(race.state.token, 'AUD15-new-login');
  assert.equal(race.cleared(), 1, 'Old logout response must not clear a subsequent login');
  assert.ok(!race.messages.at(-1).text.includes('Đã đăng xuất'));
  const signedIn = [];
  const loginState = {};
  const loginContext = {
    state: loginState, byId: () => ({value: 'synthetic'}), localStorage: {setItem() {}},
    setMessage() {}, setSignedIn: user => signedIn.push(user), openChangePasswordModal() {},
    api: async path => {
      if (path === '/auth/login') return {token: 'AUD15-new-token', username: 'user', role: 'user'};
      loginState.token = ''; // api() clears state on a rejected /auth/me.
      throw new Error('Session revoked during login');
    },
  };
  vm.createContext(loginContext);
  vm.runInContext(source.slice(source.indexOf('async function login('), source.indexOf('async function logout(')), loginContext);
  await loginContext.login({preventDefault() {}});
  assert.equal(signedIn.length, 0, 'A revoked /auth/me must not restore a signed-in view');
  console.log('Logout: captured token, local clear, server confirmation, timeout, duplicate and stale response: PASS');
})().catch(error => {console.error(error); process.exitCode = 1;});
