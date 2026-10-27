const assert = require("node:assert/strict");
const fs = require("node:fs");

const page = fs.readFileSync("app/static/index.html", "utf8");
const script = fs.readFileSync("app/static/app.js", "utf8");
const styles = fs.readFileSync("app/static/styles.css", "utf8");

assert.match(page, /id="password"[^>]*type="password"/);
assert.match(page, /id="profileCurrentPasswordInput"[^>]*type="password"/);
assert.match(page, /id="newPasswordInput"[^>]*type="password"/);
assert.match(page, /id="resetNewPasswordInput"[^>]*type="password"/);
assert.match(script, /function initializePasswordVisibilityToggles\(\)/);
assert.match(script, /input\.type = isVisible \? "password" : "text"/);
assert.match(script, /aria-label", isVisible \? "Hiện mật khẩu" : "Ẩn mật khẩu"/);
assert.match(styles, /\.password-visibility-toggle/);
console.log("Password visibility controls are wired for password inputs PASS");
