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

// Exercise the actual loader with responses arriving out of order.
const fields = new Map();
const field = id => {
  if (!fields.has(id)) fields.set(id, { value:'', textContent:'', classList:{toggle(){}}, replaceChildren(){} });
  return fields.get(id);
};
let renders=[];
let errors=[];
const requests=[];
Object.assign(context, {
  URLSearchParams,
  state:{user:{role:'admin',username:'admin'}},
  byId:field, node:()=>({}),
  showEmpty:(...args)=>errors.push(args),
  renderTickets:rows=>renders.push(rows),
  api:()=>new Promise(resolve=>requests.push(resolve)),
});
vm.runInContext(source.slice(source.indexOf('function hasTicketFilters()'), source.indexOf('function showEmpty(')), context);
(async()=>{
 field('ticketSearch').value='old';
 const old=context.loadTickets();
 field('ticketSearch').value='new';
 const latest=context.loadTickets();
 requests[1]([{id:2}]); await latest;
 requests[0]([{id:1}]); await old;
 assert.equal(renders.length,1);
 assert.equal(renders[0][0].id,2);
 assert.equal(context.hasTicketFilters(),true);
 context.clearTicketFilters();
 assert.equal(context.hasTicketFilters(),false);
 field('fromDateFilter').value='2026-10-11';
 field('toDateFilter').value='2026-10-10';
 await context.loadTickets();
 assert.equal(requests.length,2);
 assert.equal(errors[0][0],'Khoảng ngày chưa hợp lệ');
 console.log('Queue loading passed: stale responses, reset and invalid date range.');
})().catch(error=>{console.error(error);process.exitCode=1;});
