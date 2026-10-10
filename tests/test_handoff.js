const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/app.js', 'utf8');
const elements = new Map();
const get = id => {
  if (!elements.has(id)) elements.set(id, {value:'',textContent:'',classList:{add(){},remove(){}},querySelector(){return null;}});
  return elements.get(id);
};
let calls = 0;
let release;
const pending = new Promise(resolve => { release = resolve; });
const button = {disabled:false};
const form = {querySelector:()=>button,setAttribute(){},removeAttribute(){},reset(){}};
const context = {
  state:{}, window:{helpdeskI18n:{translate:x=>x}}, byId:get,
  FormData:class {entries(){return [['title','Example ticket']];}},
  setMessage(){}, refreshWorkspace:async()=>{},setWorkspaceView(){},
  api:async()=>{ calls++; return pending; },
};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('async function submitTicket('), source.indexOf('async function askKnowledge(')), context);
const build = context.buildHandoffDescription;
assert.equal(build('Question', []), 'Question');
const draft=build('Question', [{source:'vpn.md'},{source:'vpn.md'}]);
assert.equal(draft.split('- vpn.md').length-1,1);
assert.ok(draft.includes('chưa xác nhận'));
assert.ok(build('Q'.repeat(2000), Array.from({length:20},(_,i)=>({source:String(i)+'x'.repeat(1000)}))).length<=5000);
(async()=>{
 const event={preventDefault(){},currentTarget:form};
 const first=context.submitTicket(event);
 await context.submitTicket(event);
 assert.equal(calls,1);
 assert.equal(button.disabled,true);
 release({ticket:{id:42}});
 await first;
 assert.equal(button.disabled,false);
 assert.equal(context.state.ticketBusy,false);
 assert.ok(get('ticketReceipt').textContent.includes('HD-0042'));
 context.api=async()=>{throw new Error('offline');};
 await context.submitTicket(event);
 assert.equal(button.disabled,false);
 assert.equal(context.state.ticketBusy,false);
 console.log('Handoff and ticket submission passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
