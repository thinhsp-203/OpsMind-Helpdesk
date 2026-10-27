// Keep implementation names private; expose only the existing window API.
(() => {
// Render a small Markdown subset using text nodes only: never execute document HTML.
function renderRunbook(text) {
  const container = document.createElement("div");
  container.className = "runbook-content";
  let list = null;

  function inline(element, value) {
    value.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).forEach((part) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        const bold = document.createElement("strong");
        bold.textContent = part.slice(2, -2);
        element.append(bold);
      } else if (part.startsWith("`") && part.endsWith("`")) {
        const code = document.createElement("code");
        code.textContent = part.slice(1, -1);
        element.append(code);
      } else {
        element.append(document.createTextNode(part));
      }
    });
  }

  String(text || "")
    .split(/\r?\n/)
    .forEach((line) => {
      if (!line.trim()) {
        list = null;
        return;
      }
      const heading = line.match(/^#{1,6}\s+(.+)$/);
      const item = line.match(/^\s*(?:(\d+)\.\s+|[-*]\s+)(.+)$/);
      if (heading) {
        list = null;
        const title = document.createElement("h3");
        inline(title, heading[1]);
        container.append(title);
      } else if (item) {
        const type = item[1] ? "OL" : "UL";
        if (!list || list.tagName !== type) {
          list = document.createElement(type.toLowerCase());
          if (item[1]) list.start = Number(item[1]);
          container.append(list);
        }
        const entry = document.createElement("li");
        inline(entry, item[2]);
        list.append(entry);
      } else {
        list = null;
        const paragraph = document.createElement("p");
        inline(paragraph, line);
        container.append(paragraph);
      }
    });
  return container;
}

if (typeof window !== "undefined") {
  window.renderRunbook = renderRunbook;
}
})();
