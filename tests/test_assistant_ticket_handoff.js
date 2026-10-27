const assert = require("node:assert/strict");
const fs = require("node:fs");

const source = fs.readFileSync("app/static/app.js", "utf8");
const receipt = source.slice(source.indexOf("function appendAssistantTicketReceipt("), source.indexOf("async function createAssistantTicket("));
const handoff = source.slice(source.indexOf("async function createAssistantTicket("), source.indexOf("function addTicketHandoff("));
const selfService = source.slice(source.indexOf("const btnEscalateFallback"), source.indexOf("btnGroup.append(btnResolved, btnEscalateFallback)"));
const escalation = source.slice(source.indexOf("const btnDirectHandoff"), source.indexOf("btnGroup.append(btnDirectHandoff)"));

assert.match(handoff, /api\("\/tickets", \{ method: "POST"/);
assert.match(handoff, /Kiểm tra Ticket của tôi trước khi gửi lại để tránh tạo trùng/);
assert.match(handoff, /appendAssistantTicketReceipt/);
assert.doesNotMatch(handoff, /setWorkspaceView\("submit"\)/);
assert.doesNotMatch(selfService, /setWorkspaceView\("submit"\)/);
assert.doesNotMatch(escalation, /setWorkspaceView\("submit"\)/);
assert.match(selfService, /createAssistantTicket\(actionContainer/);
assert.match(escalation, /createAssistantTicket\(escalateContainer/);
assert.match(receipt, /done\.textContent = "Đã ghi nhận"/);
assert.match(receipt, /assistant-ticket-complete/);
console.log("Assistant ticket handoff stays in chat and uses one direct ticket API path PASS");
