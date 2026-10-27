const assert = require("node:assert/strict");
const fs = require("node:fs");

const page = fs.readFileSync("app/static/index.html", "utf8");
const script = fs.readFileSync("app/static/app.js", "utf8");

assert.doesNotMatch(page, /id="createSection"/);
assert.doesNotMatch(page, /id="ticketForm"/);
assert.doesNotMatch(page, /data-view="[^"]*\bsubmit\b/);
assert.doesNotMatch(script, /\["submit", "Tạo yêu cầu"\]/);
assert.doesNotMatch(script, /setWorkspaceView\("submit"\)/);
assert.doesNotMatch(script, /function submitTicket\(/);
assert.match(script, /createAssistantTicket\(/);
console.log("Direct-assistant-only ticket creation UI PASS");
