const assert = require("node:assert/strict");
const fs = require("node:fs");

const page = fs.readFileSync("app/static/index.html", "utf8");
const script = fs.readFileSync("app/static/app.js", "utf8");

assert.doesNotMatch(page, /id="deleteAccountBtn"/);
assert.match(page, /id="profileDeleteAccountBtn"/);
assert.match(script, /byId\("profileDeleteAccountBtn"\)\?\.addEventListener\("click", deleteAccount\)/);
console.log("Permanent account deletion is available only from the personal profile PASS");
