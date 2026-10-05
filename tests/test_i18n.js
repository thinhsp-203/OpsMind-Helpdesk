const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const button = {
  attributes: {},
  addEventListener(event, listener) {
    this.listener = listener;
  },
  setAttribute(name, value) {
    this.attributes[name] = value;
  },
  textContent: "",
  title: "",
};
const document = {
  body: {
    nodeType: 1,
    hasAttribute: () => false,
    querySelectorAll: () => [],
  },
  documentElement: {},
  createTreeWalker: () => ({ nextNode: () => null }),
  getElementById: () => button,
  title: "",
};
const storage = new Map();
const window = { dispatchEvent() {} };
const context = {
  document,
  Event: class {
    constructor(type) {
      this.type = type;
    }
  },
  localStorage: {
    getItem: (key) => storage.get(key) || null,
    setItem: (key, value) => storage.set(key, value),
  },
  MutationObserver: class {
    observe() {}
  },
  Node: { ELEMENT_NODE: 1, TEXT_NODE: 3 },
  NodeFilter: { SHOW_TEXT: 4 },
  window,
};
vm.runInNewContext(fs.readFileSync("app/static/i18n.js", "utf8"), context);

const i18n = window.helpdeskI18n;
assert.equal(i18n.locale(), "vi-VN");
assert.equal(i18n.translate("Đăng nhập"), "Đăng nhập");
assert.equal(i18n.translate("Chờ người gửi"), "Chờ người gửi");

i18n.setLanguage("en");
assert.equal(document.documentElement.lang, "en");
assert.equal(i18n.locale(), "en-US");
assert.equal(storage.get("helpdesk-language"), "en");
assert.equal(i18n.translate("Đăng nhập"), "Sign in");
assert.equal(i18n.translate("Comments & activity (4)"), "Comments & activity (4)");
assert.equal(i18n.translate("Trao đổi & xử lý (4)"), "Comments & activity (4)");
assert.equal(i18n.translate("Chờ người gửi"), "Awaiting requester");
assert.equal(i18n.translate("SLA · Quá hạn 3h 20p"), "SLA · Overdue by 3h 20m");
assert.equal(i18n.translate("Không tìm thấy ticket."), "Ticket not found.");
assert.equal(i18n.translate("Người dùng · Nhân viên"), "Người dùng · Requester");
assert.equal(i18n.translate("thinh · Chưa có email · Chưa có phòng ban"), "thinh · No email · No department");

const page = fs.readFileSync("app/static/index.html", "utf8");
i18n.setLanguage("en");
const staticText = [
  ...page.matchAll(/>([^<>]+)</g),
  ...page.matchAll(/(?:placeholder|aria-label)="([^"]+)"/g),
].map((match) => match[1].replaceAll("&amp;", "&").trim())
  .filter((text) => /[ăâđêôơư]/i.test(text));
const untranslated = staticText.filter((text) => i18n.translate(text) === text);
assert.deepEqual(untranslated, []);

i18n.setLanguage("vi");
assert.equal(document.documentElement.lang, "vi");
assert.equal(i18n.locale(), "vi-VN");
assert.equal(i18n.translate("Sign in"), "Đăng nhập");
assert.equal(i18n.translate("Awaiting requester"), "Chờ người gửi");
assert.equal(i18n.translate("SLA · Overdue by 3h 20m"), "SLA · Quá hạn 3h 20p");
assert.equal(i18n.translate("Ticket not found."), "Không tìm thấy ticket.");
assert.equal(i18n.translate("Người dùng · Requester"), "Người dùng · Nhân viên");
