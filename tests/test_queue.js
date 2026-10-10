const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("app/static/app.js", "utf8");
const start = source.indexOf("function filterQueueTickets(");
const end = source.indexOf("const auditEventLabels", start);
const context = {};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
const now = Date.parse("2026-10-10T00:00:00Z");
const rows = [
  {id:1, status:"new", assignee:null, sla_deadline:"2026-10-10T01:00:00Z"},
  {id:2, status:"in_progress", assignee:"agent", sla_deadline:"2026-10-09T23:00:00Z"},
  {id:3, status:"closed", assignee:"agent", sla_deadline:"2026-10-09T22:00:00Z"},
  {id:4, status:"new", assignee:"other", sla_deadline:"invalid"},
  {id:5, status:"resolved", assignee:null, sla_deadline:"2026-10-10T01:00:00Z"},
];
const ids = (mode) => Array.from(context.filterQueueTickets(rows, mode, "agent", now), r => r.id);
assert.deepEqual(ids("unassigned"), [1]);
assert.deepEqual(ids("mine"), [2]);
assert.deepEqual(ids("soon"), [1]);
assert.deepEqual(ids("overdue"), [2]);
assert.deepEqual(ids(""), [1,2,3,4,5]);
console.log("Queue filters passed: ownership, active status, SLA and invalid dates.");
