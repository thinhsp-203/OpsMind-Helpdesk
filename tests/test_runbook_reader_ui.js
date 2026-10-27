const assert = require("node:assert/strict");
const fs = require("node:fs");

const page = fs.readFileSync("app/static/index.html", "utf8");
const knowledge = fs.readFileSync("app/static/modules/knowledge.js", "utf8");

assert.match(page, /id="knowledgeReaderModal"/);
assert.match(page, /id="knowledgeReaderContent"/);
assert.match(page, /id="closeKnowledgeReader"/);
assert.match(knowledge, /async function openKnowledgeReader\(identifier, trigger\)/);
assert.match(knowledge, /api\(`\/knowledge\/\$\{encodeURIComponent\(identifier\)\}`\)/);
assert.match(knowledge, /byId\("knowledgeReaderContent"\)\.replaceChildren\(renderRunbook\(doc\.content\)\)/);
assert.match(knowledge, /editBtn\.addEventListener\("click", \(\) => openKnowledgeReader/);
console.log("Runbook reader modal wiring PASS");
