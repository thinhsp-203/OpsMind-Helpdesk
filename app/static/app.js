const state = {
  token: localStorage.getItem("helpdesk-token") || "",
  user: null,
  tickets: [],
  staff: [],
  chatSessionId: null,
  activeView: "",
  knowledgeDocs: [],
};

const byId = (id) => document.getElementById(id);
const alertUser = (message) => window.alert(window.helpdeskI18n.translate(message));
const statusLabels = {
  new: "Mới",
  in_progress: "Đang xử lý",
  pending_waiting_user: "Chờ người gửi",
  resolved: "Đã giải quyết",
  closed: "Đã đóng",
  escalated: "Chuyển cấp",
};
const priorityLabels = { low: "Thấp", medium: "Thông thường", high: "Cao", urgent: "Khẩn cấp" };
const categoryLabels = {
  network: "Mạng & VPN",
  hardware: "Phần cứng",
  software: "Phần mềm",
  security: "Tài khoản & bảo mật",
  general: "Khác",
};
const roleLabels = { user: "Nhân viên", agent: "IT Support", admin: "Quản trị IT" };
const transitions = {
  new: ["in_progress"],
  in_progress: ["pending_waiting_user", "resolved", "escalated"],
  pending_waiting_user: ["in_progress"],
  resolved: ["in_progress"],
  escalated: ["in_progress"],
  closed: [],
};

function node(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text) element.textContent = window.helpdeskI18n.translate(text);
  return element;
}

function setMessage(id, message, isError = true) {
  const target = byId(id);
  target.textContent = window.helpdeskI18n.translate(message);
  target.classList.toggle("success-message", !isError && Boolean(message));
}

async function loadPublicConfig() {
  try {
    const response = await fetch("/config");
    if (!response.ok) throw new Error(`Không tải được cấu hình (${response.status}).`);
    const config = await response.json();
    byId("demoCredentials").classList.toggle("hidden", !config.demo_mode);
  } catch (error) {
    console.error("Không tải được cấu hình công khai:", error);
  }
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...options, headers });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(data?.detail || `Yêu cầu thất bại (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return data;
}

function setSignedIn(user) {
  state.user = user;
  byId("workspaceView").dataset.role = user.role;
  byId("loginView").classList.add("hidden");
  byId("workspaceView").classList.remove("hidden");
  byId("logoutBtn").classList.remove("hidden");
  const badge = byId("userBadge");
  badge.textContent = `${user.username} · ${roleLabels[user.role] || user.role}`;
  badge.classList.remove("hidden");
  byId("greeting").textContent = `Xin chào, ${user.username}`;
  byId("roleEyebrow").textContent = roleLabels[user.role].toUpperCase();
  byId("todayLabel").textContent = new Intl.DateTimeFormat(window.helpdeskI18n.locale(), {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date());

  const isStaff = user.role === "agent" || user.role === "admin";
  byId("createSection").classList.toggle("hidden", isStaff);
  byId("employeeWorkflowNote").classList.toggle("hidden", isStaff);
  byId("analyticsSection").classList.remove("hidden");
  byId("statResolutionCard").classList.toggle("hidden", !isStaff);
  byId("statRatingCard").classList.toggle("hidden", !isStaff);
  byId("knowledgePanel").classList.toggle("hidden", user.role !== "admin");
  byId("knowledgeUploadForm").classList.toggle("hidden", user.role !== "admin");
  byId("adminUsersPanel").classList.toggle("hidden", user.role !== "admin");
  byId("assistantTitle").textContent = isStaff ? "Tra cứu runbook IT" : "Tìm cách xử lý trước";
  byId("assistantIntro").textContent = isStaff
    ? "Tra cứu hướng dẫn nội bộ có nguồn để phản hồi nhất quán cho người gửi."
    : "Mô tả lỗi để tìm hướng dẫn nội bộ. Nếu chưa xử lý được, chuyển tiếp thành yêu cầu IT.";
  byId("ticketHeading").textContent = isStaff ? "Hàng đợi hỗ trợ" : "Yêu cầu của tôi";
  byId("ticketEyebrow").textContent = isStaff ? "ĐIỀU PHỐI" : "THEO DÕI";
  byId("workspaceSubtitle").textContent = isStaff
    ? "Theo dõi hàng đợi, ưu tiên và thời hạn xử lý."
    : "Mọi yêu cầu hỗ trợ của bạn, được theo dõi rõ ràng.";
  configureWorkspaceNavigation(user.role);
  setWorkspaceView(user.role === "admin" || user.role === "agent" ? "dashboard" : "dashboard");
  byId("statTotalLabel").textContent = isStaff ? "Tổng ticket" : "Ticket của bạn";
  refreshWorkspace().catch((error) => {
    console.error("Không thể tải toàn bộ workspace:", error);
  });
}

async function login(event) {
  event.preventDefault();
  setMessage("loginMessage", "Đang xác thực...", false);
  try {
    const result = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username: byId("username").value.trim(),
        password: byId("password").value,
      }),
    });
    state.token = result.token;
    localStorage.setItem("helpdesk-token", state.token);
    setSignedIn({ username: result.username, role: result.role });
  } catch (error) {
    setMessage("loginMessage", error.message);
  }
}

function signOut() {
  state.token = "";
  state.user = null;
  state.tickets = [];
  state.chatSessionId = null;
  localStorage.removeItem("helpdesk-token");
  byId("workspaceView").classList.add("hidden");
  byId("logoutBtn").classList.add("hidden");
  byId("userBadge").classList.add("hidden");
  byId("loginView").classList.remove("hidden");
  byId("loginMessage").textContent = "";
  byId("ticketList").replaceChildren();
  byId("workspaceView").dataset.role = "";
}

async function refreshWorkspace() {
  if (state.user.role !== "user") state.staff = await api("/staff");
  await Promise.all([
    loadTickets(),
    state.user.role === "admin" ? loadKnowledge() : Promise.resolve(),
  ]);
  if (state.user.role !== "user") await loadAnalytics();
  if (state.user.role === "agent") await loadAgentAnalytics();
  if (state.user.role === "admin") await loadAdminUsers();
  await loadRagSessions();
}

function configureWorkspaceNavigation(role) {
  const items = role === "user"
    ? [["dashboard", "Tổng quan"], ["assistant", "Trợ lý IT"], ["tickets", "Ticket của tôi"], ["submit", "Tạo yêu cầu"]]
    : role === "agent"
      ? [["dashboard", "Tổng quan"], ["tickets", "Hàng đợi"], ["personal", "Thống kê của tôi"], ["assistant", "Tra cứu tri thức"]]
      : [["dashboard", "Tổng quan"], ["tickets", "Hàng đợi"], ["assistant", "Tra cứu tri thức"], ["knowledge", "Knowledge Base"], ["users", "Người dùng"], ["reports", "Báo cáo"]];
  const nav = byId("workspaceNav");
  nav.replaceChildren();
  items.forEach(([view, label]) => {
    const button = node("button", "workspace-nav-button", label);
    button.type = "button";
    button.dataset.view = view;
    button.addEventListener("click", () => setWorkspaceView(view));
    nav.append(button);
  });
  nav.classList.remove("hidden");
}

function setWorkspaceView(view) {
  state.activeView = view;
  document.querySelectorAll("#workspaceView .workspace-panel").forEach((panel) => {
    const views = panel.dataset.view.split(/\s+/);
    const roleHidden = panel.id === "employeeWorkflowNote" && state.user.role !== "user";
    panel.classList.toggle("hidden", roleHidden || !views.includes(view));
  });
  document.querySelectorAll(".workspace-nav-button").forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle("active", active);
    button.setAttribute("aria-current", active ? "page" : "false");
  });
}

async function loadTickets() {
  const params = new URLSearchParams();
  const search = byId("ticketSearch").value.trim();
  const status = byId("statusFilter").value;
  const category = byId("categoryFilter").value;
  const fromDate = byId("fromDateFilter").value;
  const toDate = byId("toDateFilter").value;
  if (search) params.set("q", search);
  if (status) params.set("status", status);
  if (category) params.set("category", category);
  if (fromDate) params.set("from", fromDate);
  if (toDate) params.set("to", toDate);
  byId("ticketList").replaceChildren(node("div", "empty-state", "Đang tải yêu cầu..."));
  try {
    state.tickets = await api(`/tickets?${params.toString()}`);
    if (state.user.role === "user") {
      const tickets = search || status || category || fromDate || toDate
        ? await api("/tickets")
        : state.tickets;
      byId("statTotal").textContent = tickets.length;
      byId("statActive").textContent = tickets.filter((ticket) =>
        ["new", "in_progress", "pending_waiting_user", "escalated"].includes(ticket.status),
      ).length;
      byId("statResolved").textContent = tickets.filter((ticket) =>
        ["resolved", "closed"].includes(ticket.status),
      ).length;
      byId("statOverdue").textContent = tickets.filter((ticket) =>
        !["resolved", "closed"].includes(ticket.status) &&
        new Date(ticket.sla_deadline) < new Date(),
      ).length;
      byId("statResolution").textContent = "—";
      byId("statRating").textContent = "—";
      byId("ratingCount").textContent = "Thống kê cá nhân";
    }
    renderTickets(state.tickets);
  } catch (error) {
    showEmpty("Không thể tải danh sách", error.message);
  }
}

function showEmpty(title, message) {
  const empty = node("div", "empty-state");
  empty.append(node("strong", "", title), node("span", "", message));
  byId("ticketList").replaceChildren(empty);
}

function renderTickets(tickets) {
  byId("ticketCount").textContent = `${tickets.length} yêu cầu`;
  if (!tickets.length) {
    showEmpty(
      state.user.role === "user" ? "Chưa có yêu cầu nào" : "Hàng đợi hiện trống",
      state.user.role === "user"
        ? "Bạn có thể tra cứu hướng dẫn trước hoặc gửi yêu cầu IT."
        : "Bỏ bộ lọc hoặc chờ yêu cầu mới từ nhân viên.",
    );
    return;
  }
  const fragment = document.createDocumentFragment();
  tickets.forEach((ticket) => fragment.append(createTicketCard(ticket)));
  byId("ticketList").replaceChildren(fragment);
}

function createTicketCard(ticket) {
  const card = node("article", "ticket-card");
  const top = node("div", "ticket-card-top");
  const titleWrap = node("div");
  titleWrap.append(
    node("span", "ticket-id", `HD-${String(ticket.id).padStart(4, "0")} · ${new Date(ticket.created_at).toLocaleDateString(window.helpdeskI18n.locale())}`),
    node("h3", "", ticket.title),
  );
  const status = node("span", `tag tag-status-${ticket.status}`, statusLabels[ticket.status] || ticket.status);
  top.append(titleWrap, status);

  const summary = node("p", "ticket-card-summary", ticket.description);
  const meta = node("div", "ticket-meta");
  meta.append(
    node("span", "tag", categoryLabels[ticket.category] || ticket.category),
    node("span", `tag ${["urgent", "high"].includes(ticket.priority) ? `tag-${ticket.priority}` : ""}`, priorityLabels[ticket.priority] || ticket.priority),
  );
  if (state.user.role !== "user") meta.append(node("span", "tag", `Người gửi: ${ticket.requester}`));
  meta.append(node("span", "tag", `IT: ${ticket.assignee || "Chưa phân công"}`));
  const sla = new Date(ticket.sla_deadline);
  if (["resolved", "closed"].includes(ticket.status)) {
    meta.append(node("span", "tag", `Đã xử lý · ${new Date(ticket.resolved_at || ticket.updated_at).toLocaleString(window.helpdeskI18n.locale(), { dateStyle: "short", timeStyle: "short" })}`));
  } else {
    const remaining = sla.getTime() - Date.now();
    const isOverdue = remaining < 0;
    const hours = Math.floor(Math.abs(remaining) / 3_600_000);
    const minutes = Math.floor((Math.abs(remaining) % 3_600_000) / 60_000);
    const countdown = isOverdue
      ? `Quá hạn ${hours}h ${minutes}p`
      : remaining < 3_600_000
        ? `Còn ${Math.max(1, minutes)} phút`
        : `Còn ${hours}h ${minutes}p`;
    const urgency = isOverdue || remaining < 3_600_000
      ? "tag-overdue"
      : remaining < 4 * 3_600_000
        ? "tag-warning"
        : "";
    const slaTag = node("span", `tag ${urgency}`, `SLA · ${countdown}`);
    slaTag.title = `Hạn: ${sla.toLocaleString(window.helpdeskI18n.locale(), { dateStyle: "short", timeStyle: "short" })}`;
    meta.append(slaTag);
  }

  const details = node("details", "ticket-details");
  const summaryToggle = node("summary", "", `Trao đổi & xử lý (${ticket.comments.length})`);
  const detailsBody = node("div", "ticket-details-body");
  const info = node("div", "ticket-info");
  info.append(
    node("span", "", `Tạo lúc: ${new Date(ticket.created_at).toLocaleString(window.helpdeskI18n.locale())}`),
    node("span", "", `Cập nhật: ${new Date(ticket.updated_at).toLocaleString(window.helpdeskI18n.locale())}`),
  );

  if (state.user.role !== "user") detailsBody.append(createStaffActions(ticket));
  if (ticket.status !== "closed" && (state.user.role !== "user" || ticket.status === "new")) {
    detailsBody.append(createTicketEditForm(ticket));
  }
  const commentList = node("div", "comment-list");
  ticket.comments.forEach((comment) => {
    const item = node("div", "comment-item");
    item.append(
      node("strong", "", `${comment.author} · ${new Date(comment.timestamp).toLocaleString(window.helpdeskI18n.locale())}`),
      document.createTextNode(comment.comment),
    );
    commentList.append(item);
  });
  if (!ticket.comments.length) commentList.append(node("span", "muted", "Chưa có trao đổi."));
  const attachmentList = node("div", "attachment-list");
  ticket.attachments.forEach((attachment) => {
    const link = node("a", "attachment-link", `📎 ${attachment.original_name}`);
    link.href = `/tickets/${ticket.id}/attachments/${attachment.id}`;
    link.addEventListener("click", downloadAttachment);
    attachmentList.append(link);
  });
  if (!ticket.attachments.length) attachmentList.append(node("span", "muted", "Chưa có tệp đính kèm."));
  detailsBody.append(attachmentList);
  if (ticket.status !== "closed") detailsBody.append(createAttachmentForm(ticket));
  if (state.user.role === "user" && ticket.status === "resolved") {
    const confirmation = node("div", "ticket-actions customer-confirmation");
    const resolvedButton = node("button", "button button-primary", "Đã giải quyết");
    resolvedButton.type = "button";
    resolvedButton.addEventListener("click", () => changeTicketStatus(ticket.id, "closed"));
    const reopenButton = node("button", "button button-soft", "Chưa xong · yêu cầu xử lý lại");
    reopenButton.type = "button";
    reopenButton.addEventListener("click", () => changeTicketStatus(ticket.id, "in_progress"));
    confirmation.append(resolvedButton, reopenButton);
    detailsBody.append(confirmation);
  }
  if (state.user.role === "user" && ["resolved", "closed"].includes(ticket.status)) {
    detailsBody.append(createRatingForm(ticket));
  }
  const commentForm = document.createElement("form");
  commentForm.className = "comment-form";
  commentForm.dataset.ticketId = ticket.id;
  const commentInput = document.createElement("input");
  commentInput.name = "comment";
  commentInput.maxLength = 3000;
  commentInput.placeholder = "Viết phản hồi...";
  commentInput.required = true;
  const commentButton = node("button", "button button-soft", "Gửi");
  commentButton.type = "submit";
  commentForm.append(commentInput, commentButton);
  commentForm.addEventListener("submit", submitComment);

  const auditButton = node("button", "button button-quiet", "Xem lịch sử xử lý");
  auditButton.type = "button";
  auditButton.addEventListener("click", () => loadAudit(ticket.id, detailsBody));
  detailsBody.append(info, commentList);
  if (ticket.status !== "closed") detailsBody.append(commentForm);
  detailsBody.append(auditButton);
  if (state.user.role === "admin") {
    const archiveButton = node("button", "button button-quiet", "Lưu trữ ticket");
    archiveButton.type = "button";
    archiveButton.addEventListener("click", async () => {
      if (!window.confirm(window.helpdeskI18n.translate("Lưu trữ ticket này? Ticket sẽ ẩn khỏi hàng đợi nhưng audit được giữ lại."))) return;
      try {
        await api(`/tickets/${ticket.id}`, { method: "DELETE" });
        await refreshWorkspace();
      } catch (error) {
        alertUser(error.message);
      }
    });
    detailsBody.append(archiveButton);
  }
  details.append(summaryToggle, detailsBody);
  card.append(top, summary, meta, details);
  card.dataset.ticketId = ticket.id;
  return card;
}

function createAttachmentForm(ticket) {
  const form = document.createElement("form");
  form.className = "attachment-form";
  form.dataset.ticketId = ticket.id;
  const file = document.createElement("input");
  file.type = "file";
  file.name = "file";
  file.accept = ".png,.jpg,.jpeg,.txt,.log";
  file.setAttribute("aria-label", "Chọn ảnh chụp màn hình hoặc tệp log");
  file.required = true;
  const button = node("button", "button button-quiet", "Đính kèm tệp");
  button.type = "submit";
  form.append(file, button);
  form.addEventListener("submit", uploadAttachment);
  return form;
}

function createRatingForm(ticket) {
  const form = document.createElement("form");
  form.className = "rating-form";
  form.dataset.ticketId = ticket.id;
  if (ticket.rating) {
    form.append(node("strong", "", `Bạn đã đánh giá ${ticket.rating}/5 sao`));
    if (ticket.rating_comment) form.append(node("span", "", ticket.rating_comment));
    return form;
  }
  const label = document.createElement("label");
  label.textContent = "Đánh giá sau xử lý";
  const select = document.createElement("select");
  select.name = "rating";
  select.setAttribute("aria-label", "Đánh giá từ 1 đến 5 sao");
  for (let rating = 5; rating >= 1; rating -= 1) {
    const option = node("option", "", `${rating} sao`);
    option.value = rating;
    select.append(option);
  }
  const comment = document.createElement("input");
  comment.name = "comment";
  comment.maxLength = 2000;
  comment.placeholder = "Nhận xét (không bắt buộc)";
  const button = node("button", "button button-soft", "Gửi đánh giá");
  button.type = "submit";
  form.append(label, select, comment, button);
  form.addEventListener("submit", submitRating);
  return form;
}

function createTicketEditForm(ticket) {
  const form = document.createElement("form");
  form.className = "ticket-edit-form";
  form.dataset.ticketId = ticket.id;
  const title = document.createElement("input");
  title.name = "title";
  title.required = true;
  title.minLength = 5;
  title.maxLength = 160;
  title.value = ticket.title;
  title.setAttribute("aria-label", "Tiêu đề ticket");
  const category = document.createElement("select");
  category.name = "category";
  Object.entries(categoryLabels).forEach(([value, label]) => {
    const option = node("option", "", label);
    option.value = value;
    option.selected = ticket.category === value;
    category.append(option);
  });
  const priority = document.createElement("select");
  priority.name = "priority";
  Object.entries(priorityLabels).forEach(([value, label]) => {
    const option = node("option", "", label);
    option.value = value;
    option.selected = ticket.priority === value;
    priority.append(option);
  });
  const description = document.createElement("textarea");
  description.name = "description";
  description.required = true;
  description.minLength = 10;
  description.maxLength = 5000;
  description.value = ticket.description;
  description.setAttribute("aria-label", "Mô tả ticket");
  const button = node("button", "button button-soft", "Lưu chỉnh sửa");
  button.type = "submit";
  form.append(title, category, priority, description, button);
  form.addEventListener("submit", submitTicketEdit);
  return form;
}

async function submitTicketEdit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    await api(`/tickets/${form.dataset.ticketId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    await refreshWorkspace();
  } catch (error) {
    alertUser(error.message);
  }
}

function createStaffActions(ticket) {
  const actions = node("div", "ticket-actions");
  const suggestButton = node("button", "button button-soft", "Tra cứu runbook cho ticket");
  suggestButton.type = "button";
  suggestButton.addEventListener("click", () => {
    setWorkspaceView("assistant");
    askKnowledge(null, {
      question: `${ticket.title}\n${ticket.description}`,
      ticketId: ticket.id,
    });
  });
  const statusSelect = document.createElement("select");
  statusSelect.setAttribute("aria-label", `Trạng thái ticket ${ticket.id}`);
  [ticket.status, ...transitions[ticket.status]].forEach((status) => {
    const option = node("option", "", statusLabels[status]);
    option.value = status;
    statusSelect.append(option);
  });
  const statusButton = node("button", "button button-soft", "Cập nhật trạng thái");
  statusButton.type = "button";
  statusButton.addEventListener("click", async () => {
    if (statusSelect.value === ticket.status) return;
    try {
      await api(`/tickets/${ticket.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: statusSelect.value }),
      });
      await refreshWorkspace();
    } catch (error) {
      alertUser(error.message);
    }
  });

  const assigneeSelect = document.createElement("select");
  assigneeSelect.setAttribute("aria-label", `Người xử lý ticket ${ticket.id}`);
  const unassigned = node("option", "", "Chọn nhân viên IT");
  unassigned.value = "";
  unassigned.selected = !ticket.assignee;
  assigneeSelect.append(unassigned);
  state.staff.forEach(({ username, role }) => {
    const option = node("option", "", `${roleLabels[role]} · ${username}`);
    option.value = username;
    option.selected = ticket.assignee === username;
    assigneeSelect.append(option);
  });
  const assignButton = node("button", "button button-quiet", "Giao cho IT");
  assignButton.type = "button";
  assignButton.disabled = !state.staff.length || !ticket.assignee;
  assigneeSelect.addEventListener("change", () => {
    assignButton.disabled = !assigneeSelect.value;
  });
  assignButton.addEventListener("click", async () => {
    try {
      await api(`/tickets/${ticket.id}/assignment`, {
        method: "PUT",
        body: JSON.stringify({ assignee: assigneeSelect.value }),
      });
      await refreshWorkspace();
    } catch (error) {
      alertUser(error.message);
    }
  });
  actions.append(suggestButton, statusSelect, statusButton, assigneeSelect, assignButton);
  return actions;
}

async function loadAudit(ticketId, container) {
  try {
    const entries = await api(`/tickets/${ticketId}/audit`);
    const history = node("div", "audit-list");
    entries.forEach((entry) => {
      const label = entry.event === "status_changed"
        ? `${statusLabels[entry.from_status]} → ${statusLabels[entry.to_status]}`
        : entry.event === "assigned"
          ? `Giao cho ${entry.details}`
          : entry.event === "comment_added"
            ? "Thêm phản hồi"
            : entry.event === "ticket_updated"
              ? `Cập nhật: ${entry.details}`
              : entry.event === "archived"
                ? "Lưu trữ ticket"
                : "Tạo ticket";
      const eventLabels = {
        status_changed: "Thay đổi trạng thái",
        assigned: "Phân công",
        comment_added: "Thêm phản hồi",
        ticket_updated: "Cập nhật ticket",
        archived: "Lưu trữ ticket",
        created: "Tạo ticket",
      };
      history.append(node("div", "comment-item", `${new Date(entry.timestamp).toLocaleString(window.helpdeskI18n.locale())} · ${entry.actor} · ${label} · ${eventLabels[entry.event] || entry.event}`));
    });
    const previous = container.querySelector(".audit-list");
    if (previous) previous.remove();
    container.append(history);
  } catch (error) {
    alertUser(error.message);
  }
}

async function submitComment(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const input = form.elements.comment;
  try {
    await api(`/tickets/${form.dataset.ticketId}/comments`, {
      method: "POST",
      body: JSON.stringify({ comment: input.value.trim() }),
    });
    await refreshWorkspace();
  } catch (error) {
    alertUser(error.message);
  }
}

async function changeTicketStatus(ticketId, status) {
  const prompt = status === "in_progress"
    ? "Yêu cầu IT tiếp tục xử lý ticket này?"
    : status === "closed"
      ? "Xác nhận ticket đã giải quyết?"
      : `Chuyển ticket sang trạng thái ${statusLabels[status]}?`;
  if (!window.confirm(window.helpdeskI18n.translate(prompt))) return;
  try {
    await api(`/tickets/${ticketId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    await refreshWorkspace();
  } catch (error) {
    alertUser(error.message);
  }
}

async function uploadAttachment(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const input = form.elements.file;
  const file = input.files[0];
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) {
    alertUser("Tệp vượt quá giới hạn 10 MiB.");
    return;
  }
  const payload = new FormData();
  payload.append("file", file);
  try {
    await api(`/tickets/${form.dataset.ticketId}/attachments`, {
      method: "POST",
      body: payload,
    });
    await refreshWorkspace();
  } catch (error) {
    alertUser(error.message);
  }
}

async function downloadAttachment(event) {
  event.preventDefault();
  const link = event.currentTarget;
  try {
    const response = await fetch(link.href, {
      headers: { Authorization: `******` },
    });
    const data = await response.blob();
    if (!response.ok) {
      const message = await data.text();
      throw new Error(JSON.parse(message).detail || "Không tải được tệp.");
    }
    const url = URL.createObjectURL(data);
    const download = document.createElement("a");
    download.href = url;
    download.download = link.textContent.replace(/^📎\s*/, "");
    download.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    alertUser(error.message);
  }
}

async function submitRating(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const values = new FormData(form);
  try {
    await api(`/tickets/${form.dataset.ticketId}/rate`, {
      method: "POST",
      body: JSON.stringify({
        rating: Number(values.get("rating")),
        comment: values.get("comment"),
      }),
    });
    await refreshWorkspace();
  } catch (error) {
    alertUser(error.message);
  }
}

async function submitTicket(event) {
  event.preventDefault();
  const form = event.currentTarget;
  setMessage("ticketMessage", "");
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    await api("/tickets", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    byId("ticketSearch").value = "";
    byId("statusFilter").value = "";
    byId("categoryFilter").value = "";
    byId("fromDateFilter").value = "";
    byId("toDateFilter").value = "";
    setMessage("ticketMessage", "Đã gửi yêu cầu. Mã ticket và tiến độ được lưu trong mục bên dưới.", false);
    await refreshWorkspace();
    setWorkspaceView("tickets");
    const firstTicket = byId("ticketList").querySelector(".ticket-card");
    firstTicket?.scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (error) {
    setMessage("ticketMessage", error.message);
  }
}

async function askKnowledge(event, options = {}) {
  event?.preventDefault();
  const question = (options.question || byId("ragQuestion").value).trim();
  if (!question) {
    showRagResult("Nhập mô tả sự cố để tìm hướng dẫn.");
    byId("ragQuestion").focus();
    return;
  }
  byId("ragQuestion").value = question;
  byId("assistantPanel").scrollIntoView({ behavior: "smooth", block: "start" });
  const result = byId("ragResult");
  result.classList.remove("hidden");
  result.replaceChildren(node("p", "rag-answer", "Đang tìm trong tài liệu nội bộ..."));
  try {
    const data = await api("/rag/ask", {
      method: "POST",
      body: JSON.stringify({
        question,
        ...(state.chatSessionId ? { session_id: state.chatSessionId } : {}),
      }),
    });
    state.chatSessionId = data.session_id;
    result.replaceChildren(node("p", "rag-answer", data.answer));
    if (data.sources.length) {
      const sourceCard = (match, source, index) => {
        const card = node("div", "rag-source");
        const heading = node("strong", "", `${index + 1}. ${source.title} · ${source.source}`);
        card.append(heading, node("p", "", match.content));
        return card;
      };
      result.append(sourceCard(data.matches[0], data.sources[0], 0));
      if (data.matches.length > 1) {
        const moreSources = document.createElement("details");
        moreSources.className = "additional-sources";
        moreSources.append(node("summary", "", `Xem ${data.matches.length - 1} nguồn liên quan khác`));
        data.matches.slice(1).forEach((match, index) => {
          moreSources.append(sourceCard(match, data.sources[index + 1], index + 1));
        });
        result.append(moreSources);
      }
    }
    addTicketHandoff(result, question, data.grounded, data.triage, {
      ticketId: options.ticketId,
      matches: data.matches,
    });
    const feedback = node("div", "rag-feedback");
    feedback.append(node("span", "muted", "Hướng dẫn này có hữu ích không?"));
    [["up", "👍"], ["down", "👎"]].forEach(([value, label]) => {
      const button = node("button", "button button-quiet", label);
      button.type = "button";
      button.setAttribute("aria-label", value === "up" ? "Hữu ích" : "Không hữu ích");
      button.addEventListener("click", async () => {
        try {
          await api("/rag/feedback", {
            method: "POST",
            body: JSON.stringify({ message_id: data.assistant_message_id, feedback: value }),
          });
          feedback.replaceChildren(node("span", "success-message", "Đã ghi nhận phản hồi."));
        } catch (error) {
          alertUser(error.message);
        }
      });
      feedback.append(button);
    });
    result.append(feedback);
    await loadRagSessions();
    result.focus({ preventScroll: true });
    result.scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (error) {
    showRagResult(error.message);
  }
}

function addTicketHandoff(container, question, grounded, triage, options = {}) {
  const triageCard = node("div", "triage-card");
  triageCard.append(
    node("strong", "", "Gợi ý phân loại · cần bạn xác nhận"),
    node(
      "span",
      "triage-values",
      `${categoryLabels[triage.category] || triage.category} · ${priorityLabels[triage.priority] || triage.priority}`,
    ),
    node("small", "", `${triage.category_reason} ${triage.priority_reason}`),
  );
  container.append(triageCard);
  if (state.user.role !== "user") {
    container.append(
      node("p", "handoff-note", "Đối chiếu nguồn trước khi dùng hướng dẫn để phản hồi ticket."),
    );
    if (grounded && options.ticketId) {
      const insertButton = node("button", "button button-soft", `Chèn trích đoạn vào phản hồi #${options.ticketId}`);
      insertButton.type = "button";
      insertButton.addEventListener("click", () => {
        const card = document.querySelector(`[data-ticket-id="${options.ticketId}"]`);
        const commentInput = card?.querySelector('.comment-form input[name="comment"]');
        if (!commentInput) {
          showRagResult("Không tìm thấy ô phản hồi của ticket. Hãy tải lại hàng đợi rồi thử lại.");
          return;
        }
        const excerpts = options.matches
          .map((match) => `${match.content}\nNguồn: ${match.title} (${match.source})`)
          .join("\n\n");
        commentInput.value = `Gợi ý tham khảo từ runbook (cần IT kiểm tra trước khi gửi):\n\n${excerpts}`;
        card.scrollIntoView({ behavior: "smooth", block: "center" });
        commentInput.focus({ preventScroll: true });
      });
      container.append(insertButton);
    }
    return;
  }
  const handoff = node(
    "p",
    "handoff-note",
    grounded
      ? "Chưa giải quyết được? Chuyển nội dung này cho IT, không cần gõ lại."
      : "Chưa có hướng dẫn phù hợp. Gửi yêu cầu để IT tiếp nhận.",
  );
  const draftButton = node(
    "button",
    "button button-soft",
    grounded ? "Chuyển thành yêu cầu IT" : "Gửi yêu cầu cho IT",
  );
  draftButton.type = "button";
  draftButton.addEventListener("click", () => {
    setWorkspaceView("submit");
    const title = question.replace(/\s+/g, " ").trim().slice(0, 160);
    byId("ticketTitle").value = title.length >= 5 ? title : `Hỗ trợ: ${title}`;
    byId("ticketDescription").value = question;
    byId("ticketCategory").value = triage.category;
    byId("ticketPriority").value = triage.priority;
    byId("ticketMessage").textContent = "Đã điền sẵn nội dung. Kiểm tra lại rồi gửi cho IT.";
    byId("ticketMessage").classList.add("success-message");
    byId("createSection").scrollIntoView({ behavior: "smooth", block: "start" });
    byId("ticketTitle").focus({ preventScroll: true });
  });
  container.append(handoff, draftButton);
}

function showRagResult(message) {
  const result = byId("ragResult");
  result.classList.remove("hidden");
  result.replaceChildren(node("p", "rag-answer", message));
  result.focus({ preventScroll: true });
  result.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function loadKnowledge() {
  try {
    const documents = await api("/knowledge");
    byId("knowledgeCount").textContent = window.helpdeskI18n.translate(`${documents.length} tài liệu`);
    const list = byId("knowledgeList");
    list.replaceChildren();
    documents.forEach((document) => {
      const row = node("div", "knowledge-document");
      const label = node("div", "knowledge-document-label");
      label.append(node("strong", "", document.title), node("span", "", document.source));
      row.append(label);
      if (state.user.role === "admin") {
        const reindex = node("button", "button button-quiet", "Re-index");
        reindex.type = "button";
        reindex.addEventListener("click", async () => {
          try {
            await api(`/knowledge/${encodeURIComponent(document.source)}/reindex`, { method: "POST" });
            await loadKnowledge();
          } catch (error) {
            alertUser(error.message);
          }
        });
        const remove = node("button", "button button-quiet", "Xóa");
        remove.type = "button";
        remove.addEventListener("click", async () => {
          if (!window.confirm(window.helpdeskI18n.translate(`Xóa tài liệu ${document.source} khỏi thư viện?`))) return;
          try {
            await api(`/knowledge/${encodeURIComponent(document.source)}`, { method: "DELETE" });
            await loadKnowledge();
          } catch (error) {
            alertUser(error.message);
          }
        });
        row.append(reindex, remove);
      }
      list.append(row);
    });
  } catch {
    byId("knowledgeList").replaceChildren(node("span", "muted", "Không tải được danh mục tri thức."));
  }
}

async function uploadKnowledge(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const fileInput = byId("knowledgeFile");
  if (!fileInput.files.length) {
    setMessage("knowledgeMessage", "Chọn một tệp Markdown trước.");
    return;
  }
  if (fileInput.files[0].size > 262144) {
    setMessage("knowledgeMessage", "Tệp vượt quá giới hạn 256 KiB.");
    return;
  }
  const payload = new FormData(form);
  setMessage("knowledgeMessage", "Đang kiểm tra và nạp tài liệu...", false);
  try {
    await api("/knowledge", { method: "POST", body: payload });
    form.reset();
    setMessage("knowledgeMessage", "Đã thêm tài liệu vào Knowledge Base.", false);
    await loadKnowledge();
  } catch (error) {
    setMessage("knowledgeMessage", error.message);
  }
}

async function loadAdminUsers() {
  try {
    const users = await api("/admin/users");
    const list = byId("adminUserList");
    list.replaceChildren();
    users.forEach((user) => {
      const row = node("div", "admin-user-row");
      const identity = node("div", "admin-user-identity");
      identity.append(
        node("strong", "", user.full_name || user.username),
        node("span", "", `${user.username} · ${user.email || "Chưa có email"} · ${user.department || "Chưa có phòng ban"}`),
      );
      const actions = node("div", "admin-user-actions");
      const profileDetails = document.createElement("details");
      profileDetails.className = "admin-profile-details";
      profileDetails.append(node("summary", "", "Sửa hồ sơ"));
      const profileForm = document.createElement("form");
      profileForm.className = "admin-profile-form";
      profileForm.dataset.username = user.username;
      [
        ["full_name", "Họ tên", user.full_name],
        ["email", "Email", user.email],
        ["department", "Phòng ban", user.department],
        ["phone", "Điện thoại", user.phone],
      ].forEach(([name, label, value]) => {
        const input = document.createElement("input");
        input.name = name;
        input.value = value || "";
        input.maxLength = name === "email" ? 254 : name === "phone" ? 40 : 120;
        if (name === "email") input.type = "email";
        input.setAttribute("aria-label", `${label} ${user.username}`);
        input.placeholder = label;
        profileForm.append(input);
      });
      const saveProfile = node("button", "button button-soft", "Lưu hồ sơ");
      saveProfile.type = "submit";
      profileForm.append(saveProfile);
      profileForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const payload = Object.fromEntries(new FormData(form).entries());
        try {
          await api(`/admin/users/${encodeURIComponent(form.dataset.username)}`, {
            method: "PATCH",
            body: JSON.stringify(payload),
          });
          await loadAdminUsers();
        } catch (error) {
          alertUser(error.message);
        }
      });
      profileDetails.append(profileForm);
      const roleSelect = document.createElement("select");
      roleSelect.setAttribute("aria-label", `Vai trò ${user.username}`);
      Object.entries(roleLabels).forEach(([value, label]) => {
        const option = node("option", "", label);
        option.value = value;
        option.selected = user.role === value;
        roleSelect.append(option);
      });
      const saveRole = node("button", "button button-quiet", "Lưu vai trò");
      saveRole.type = "button";
      saveRole.addEventListener("click", async () => {
        try {
          await api(`/admin/users/${encodeURIComponent(user.username)}`, {
            method: "PATCH",
            body: JSON.stringify({ role: roleSelect.value }),
          });
          await loadAdminUsers();
          state.staff = await api("/staff");
        } catch (error) {
          alertUser(error.message);
        }
      });
      const activeButton = node(
        "button",
        "button button-quiet",
        user.is_active ? "Khóa" : "Mở khóa",
      );
      activeButton.type = "button";
      activeButton.addEventListener("click", async () => {
        try {
          await api(`/admin/users/${encodeURIComponent(user.username)}`, {
            method: "PATCH",
            body: JSON.stringify({ is_active: !user.is_active }),
          });
          await loadAdminUsers();
          state.staff = await api("/staff");
        } catch (error) {
          alertUser(error.message);
        }
      });
      actions.append(roleSelect, saveRole, activeButton);
      row.append(
        identity,
        profileDetails,
        node("span", "", user.is_active ? "Hoạt động" : "Đã khóa"),
        actions,
      );
      list.append(row);
    });
  } catch (error) {
    byId("adminUserList").replaceChildren(node("span", "muted", error.message));
  }
}

async function createAdminUser(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    await api("/admin/users", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    form.reset();
    setMessage("adminUserMessage", "Đã tạo tài khoản.", false);
    await loadAdminUsers();
    state.staff = await api("/staff");
    await loadTickets();
  } catch (error) {
    setMessage("adminUserMessage", error.message);
  }
}

async function loadAnalytics() {
  try {
    const analytics = await api("/analytics");
    byId("statTotal").textContent = analytics.total_tickets;
    byId("statActive").textContent =
      (analytics.status_breakdown.new || 0) +
      (analytics.status_breakdown.in_progress || 0) +
      (analytics.status_breakdown.pending_waiting_user || 0) +
      (analytics.status_breakdown.escalated || 0);
    byId("statResolved").textContent =
      (analytics.status_breakdown.resolved || 0) + (analytics.status_breakdown.closed || 0);
    byId("statOverdue").textContent = analytics.overdue_tickets;
    byId("statResolution").textContent = analytics.average_resolution_hours === null
      ? "—"
      : analytics.average_resolution_hours;
    byId("statRating").textContent = analytics.average_rating === null
      ? "—"
      : `${analytics.average_rating}/5`;
    byId("ratingCount").textContent = `${analytics.rating_count} đánh giá`;
    renderAnalyticsCharts(analytics);
    const agentList = byId("agentReportList");
    agentList.replaceChildren();
    if (!analytics.agent_performance.length) {
      agentList.append(node("span", "muted", "Chưa có ticket được gán và giải quyết để tính hiệu suất."));
    } else {
      analytics.agent_performance.forEach((agent) => {
        const row = node("div", "agent-report-row");
        row.append(
          node("strong", "", agent.assignee),
          node("span", "", `${agent.resolved_tickets} ticket`),
          node("span", "", `SLA ${agent.sla_compliance_percent}%`),
          node("span", "", `TB ${agent.average_resolution_hours} giờ`),
        );
        agentList.append(row);
      });
    }
    const activity = byId("recentActivity");
    activity.replaceChildren(node("strong", "", "Hoạt động gần đây"));
    analytics.recent_activity.forEach((entry) => {
      activity.append(node(
        "div",
        "comment-item",
        `${new Date(entry.timestamp).toLocaleString(window.helpdeskI18n.locale())} · ${entry.actor} · HD-${String(entry.ticket_id).padStart(4, "0")} · ${entry.event}`,
      ));
    });
  } catch (error) {
    byId("statTotal").textContent = "—";
    byId("statActive").textContent = "—";
    byId("statResolved").textContent = "—";
    byId("statOverdue").textContent = "—";
    console.error("Không tải được analytics:", error);
  }
}

function renderAnalyticsCharts(analytics) {
  const trend = byId("dailyTrend");
  trend.replaceChildren();
  const days = Object.entries(analytics.daily_created).sort(([left], [right]) =>
    left.localeCompare(right),
  );
  const maximum = Math.max(1, ...days.map(([, count]) => count));
  if (!days.length) trend.append(node("span", "muted", "Chưa có dữ liệu ticket."));
  days.forEach(([day, count]) => {
    const column = node("div", "daily-trend-column");
    const bar = node("span", "daily-trend-bar");
    bar.style.height = `${Math.max(4, (count / maximum) * 64)}px`;
    bar.title = `${day}: ${count} ticket`;
    column.append(node("strong", "", String(count)), bar, node("small", "", day.slice(5)));
    trend.append(column);
  });
  const categoryReport = byId("categoryReport");
  categoryReport.replaceChildren();
  const categoryEntries = Object.entries(analytics.category_breakdown);
  const total = categoryEntries.reduce((sum, [, count]) => sum + count, 0);
  if (!total) categoryReport.append(node("span", "muted", "Chưa có dữ liệu danh mục."));
  categoryEntries.forEach(([category, count]) => {
    const row = node("div", "category-report-row");
    const label = node("span", "", categoryLabels[category] || category);
    const bar = node("span", "category-report-bar");
    bar.style.width = `${(count / total) * 100}%`;
    row.append(label, bar, node("strong", "", `${Math.round((count / total) * 100)}%`));
    categoryReport.append(row);
  });
}

async function loadAgentAnalytics() {
  try {
    const metrics = await api("/analytics/agents/me");
    byId("agentAssigned").textContent = metrics.assigned_tickets;
    byId("agentResolved").textContent = metrics.resolved_tickets;
    byId("agentResolution").textContent = metrics.average_resolution_hours === null
      ? "—"
      : `${metrics.average_resolution_hours} giờ`;
    byId("agentSla").textContent = metrics.sla_compliance_percent === null
      ? "—"
      : `${metrics.sla_compliance_percent}%`;
    byId("agentOverdue").textContent = metrics.overdue_tickets;
    const categories = byId("agentCategoryStats");
    categories.replaceChildren(node("strong", "", "Ticket theo danh mục"));
    const entries = Object.entries(metrics.category_breakdown);
    if (!entries.length) categories.append(node("span", "muted", "Chưa có ticket được giao."));
    entries.forEach(([category, count]) => {
      categories.append(node("div", "agent-report-row", `${categoryLabels[category] || category} · ${count}`));
    });
  } catch (error) {
    console.error("Không tải được thống kê cá nhân:", error);
  }
}

async function loadRagSessions() {
  try {
    const sessions = await api("/rag/sessions");
    const list = byId("chatHistoryList");
    list.replaceChildren();
    if (!sessions.length) {
      list.append(node("span", "muted", "Chưa có hội thoại."));
      return;
    }
    sessions.forEach((session) => {
      const button = node(
        "button",
        "chat-history-item",
        `${session.first_question || "Tra cứu"} · ${new Date(session.last_message_at).toLocaleString(window.helpdeskI18n.locale())}`,
      );
      button.type = "button";
      button.addEventListener("click", async () => {
        try {
          const conversation = await api(`/rag/sessions/${encodeURIComponent(session.id)}`);
          state.chatSessionId = session.id;
          const result = byId("ragResult");
          result.classList.remove("hidden");
          result.replaceChildren();
          conversation.messages.forEach((message) => {
            const bubble = node(
              "div",
              `chat-history-message chat-${message.role}`,
              `${message.role === "user" ? "Bạn" : "Trợ lý"}: ${message.content}`,
            );
            if (message.feedback) bubble.append(node("small", "muted", `Phản hồi: ${message.feedback}`));
            if (message.role === "assistant" && message.sources.length) {
              message.sources.forEach((source) => {
                bubble.append(node("small", "muted", `Nguồn: ${source.title} · ${source.source}`));
              });
            }
            result.append(bubble);
          });
          byId("assistantPanel").scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (error) {
          alertUser(error.message);
        }
      });
      list.append(button);
    });
  } catch (error) {
    byId("chatHistoryList").replaceChildren(node("span", "muted", error.message));
  }
}

async function exportReport() {
  try {
    const response = await fetch("/analytics/export", {
      headers: { Authorization: `******` },
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "Không thể xuất báo cáo.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "helpdesk-report.csv";
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    alertUser(error.message);
  }
}

let searchTimer;
window.addEventListener("helpdesk-language-changed", () => {
  if (state.user) {
    byId("todayLabel").textContent = new Intl.DateTimeFormat(window.helpdeskI18n.locale(), {
      weekday: "long",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(new Date());
    refreshWorkspace().catch((error) => {
      console.error("Không thể làm mới workspace sau khi đổi ngôn ngữ:", error);
    });
  }
});
loadPublicConfig();
byId("loginForm").addEventListener("submit", login);
byId("logoutBtn").addEventListener("click", signOut);
byId("ticketForm").addEventListener("submit", submitTicket);
byId("ragForm").addEventListener("submit", askKnowledge);
byId("knowledgeUploadForm").addEventListener("submit", uploadKnowledge);
byId("adminUserForm").addEventListener("submit", createAdminUser);
byId("exportReportBtn").addEventListener("click", exportReport);
byId("knowledgeSearch").addEventListener("input", () => {
  const query = byId("knowledgeSearch").value.trim().toLocaleLowerCase();
  byId("knowledgeList").querySelectorAll(".knowledge-document").forEach((row) => {
    row.classList.toggle("hidden", !row.textContent.toLocaleLowerCase().includes(query));
  });
});
byId("newChatBtn").addEventListener("click", () => {
  state.chatSessionId = null;
  byId("ragQuestion").value = "";
  byId("ragResult").replaceChildren();
  byId("ragResult").classList.add("hidden");
  byId("ragQuestion").focus();
});
byId("popularQuestions").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-question]");
  if (!button) return;
  byId("ragQuestion").value = button.dataset.question;
  byId("ragForm").requestSubmit();
});
byId("draftFromRagBtn").addEventListener("click", () => {
  const ticketDescription = byId("ticketDescription").value.trim();
  const ticketTitle = byId("ticketTitle").value.trim();
  const question = ticketDescription || ticketTitle;
  if (question) byId("ragQuestion").value = question;
  byId("assistantPanel").scrollIntoView({ behavior: "smooth", block: "start" });
  byId("ragQuestion").focus({ preventScroll: true });
  if (question) {
    byId("ragForm").requestSubmit();
  } else {
    setMessage("ticketMessage", "Nhập sự cố ở ô tra cứu phía trên; nếu chưa xử lý được, chuyển nội dung sang yêu cầu IT.", false);
  }
});
byId("statusFilter").addEventListener("change", loadTickets);
byId("categoryFilter").addEventListener("change", loadTickets);
byId("fromDateFilter").addEventListener("change", loadTickets);
byId("toDateFilter").addEventListener("change", loadTickets);
byId("ticketSearch").addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(loadTickets, 250);
});

if (state.token) {
  api("/auth/me")
    .then(setSignedIn)
    .catch(() => signOut());
}

async function refreshServiceState() {
  const label = byId("serviceStateLabel");
  try {
    const response = await fetch("/health", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await response.json();
    label.textContent = "Hệ thống sẵn sàng";
    label.classList.remove("service-state-error");
    label.classList.add("service-state-ok");
  } catch {
    label.textContent = "Dịch vụ đang gián đoạn";
    label.classList.remove("service-state-ok");
    label.classList.add("service-state-error");
  }
}

refreshServiceState();
window.setInterval(refreshServiceState, 30000);
