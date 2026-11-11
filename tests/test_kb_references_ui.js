const assert = require("node:assert/strict");
const fs = require("node:fs");

const app = fs.readFileSync("app/static/app.js", "utf8");
const knowledge = fs.readFileSync("app/static/modules/knowledge.js", "utf8");

// References come from a separate field and open the existing safe reader.
assert.match(app, /Array\.isArray\(data\.kb_references\)/);
assert.match(app, /function renderKbReferences\(references\)/);
assert.match(app, /window\.openKnowledgeReader\(ref\.source, button\)/);
assert.match(app, /không phải bước chẩn đoán đã được phê duyệt/);
assert.match(knowledge, /window\.openKnowledgeReader = openKnowledgeReader;/);
// Reference titles are rendered as text via node(), never as HTML.
assert.doesNotMatch(app.slice(app.indexOf("function renderKbReferences")), /^[^\n]*innerHTML[^\n]*ref\./m);
console.log("KB reference UI wiring PASS");
