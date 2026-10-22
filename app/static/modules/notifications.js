// Keep implementation names private; expose only the existing window API.
(() => {
function getAppState() {
  return window.state || (typeof state !== "undefined" ? state : { user: null });
}

function getAppApi() {
  return window.api || (typeof api !== "undefined" ? api : fetch);
}

function getAppById(id) {
  return window.byId ? window.byId(id) : document.getElementById(id);
}

function setAppMessage(id, text, isError = true) {
  if (window.setMessage) {
    window.setMessage(id, text, isError);
  } else {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = text;
      el.className = isError ? "form-message error" : "form-message success";
    }
  }
}

function renderNotificationHistory(history) {
  const container = getAppById("notificationHistoryList");
  const countEl = getAppById("notificationHistoryCount");
  if (!container) return;
  container.replaceChildren();

  const items = Array.isArray(history) ? history : [];
  if (countEl) countEl.textContent = `${items.length} bản ghi`;

  if (items.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const strong = document.createElement("strong");
    strong.textContent = "Chưa có sự kiện thông báo";
    const span = document.createElement("span");
    span.textContent = "Các thông báo sự cố P1/P2 và thông báo thử nghiệm sẽ tự động hiển thị tại đây.";
    empty.append(strong, span);
    container.append(empty);
    return;
  }

  const channelIcons = {
    telegram: "✈",
    discord: "🎮",
    email: "✉",
    system: "⚙",
  };

  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "notification-history-item";

    const left = document.createElement("div");
    left.className = "notification-history-meta";

    const icon = document.createElement("span");
    icon.className = `channel-icon-pill channel-${item.channel || "system"}`;
    icon.textContent = channelIcons[item.channel] || "🔔";

    const textDiv = document.createElement("div");
    textDiv.className = "notification-history-text";

    const titleStrong = document.createElement("strong");
    titleStrong.textContent = item.event_type || "Thông báo";

    const sub = document.createElement("span");
    sub.className = "notification-history-sub";
    sub.textContent = `${item.channel_label || item.channel || "Kênh"} • Đích: ${item.recipient || "—"} • ${item.timestamp || ""}`;

    textDiv.append(titleStrong, sub);
    if (item.message) {
      const msg = document.createElement("small");
      msg.className = "notification-history-msg";
      msg.textContent = item.message;
      textDiv.append(msg);
    }

    left.append(icon, textDiv);

    const badge = document.createElement("span");
    const isSuccess = item.status === "success" || item.status === "active";
    badge.className = `tag ${isSuccess ? "tag-status-published" : "tag-status-draft"}`;
    badge.textContent = item.status_label || (isSuccess ? "Thành công" : "Lỗi");

    row.append(left, badge);
    container.append(row);
  });
}

async function loadNotificationStatus() {
  const appState = getAppState();
  if (appState.user && appState.user.role !== "admin") return;

  const appApi = getAppApi();
  const byId = getAppById;

  try {
    const data = await appApi("/admin/notifications/status");
    const tg = data.telegram || {};
    const tgBadge = byId("telegramStatusBadge");
    const tgUser = byId("telegramBotUsername");
    const tgChat = byId("telegramChatId");
    if (tgBadge) {
      tgBadge.textContent = tg.enabled ? "Đã cấu hình" : "Chưa cấu hình";
      tgBadge.className = `tag ${tg.enabled ? "tag-status-published" : "tag-status-draft"}`;
    }
    if (tgUser) tgUser.textContent = tg.enabled ? "Đã cấu hình" : "Chưa cấu hình";
    if (tgChat) tgChat.textContent = tg.target || "Chưa cấu hình";

    const dc = data.discord || {};
    const dcBadge = byId("discordStatusBadge");
    const dcUrl = byId("discordWebhookUrl");
    if (dcBadge) {
      dcBadge.textContent = dc.enabled ? "Đã cấu hình" : "Chưa cấu hình";
      dcBadge.className = `tag ${dc.enabled ? "tag-status-published" : "tag-status-draft"}`;
    }
    if (dcUrl) dcUrl.textContent = dc.target || "Chưa cấu hình";

    const em = data.email || {};
    const emBadge = byId("emailStatusBadge");
    const emProvider = byId("emailProviderName");
    const emServer = byId("emailServerTarget");
    const emSender = byId("emailSenderFrom");
    if (emBadge) {
      if (!em.enabled) {
        emBadge.textContent = "Chưa kết nối";
        emBadge.className = "tag tag-status-draft";
      } else if (em.is_mock) {
        emBadge.textContent = "Mock Outbox (RAM)";
        emBadge.className = "tag tag-status-pending";
      } else {
        emBadge.textContent = "Đang hoạt động";
        emBadge.className = "tag tag-status-published";
      }
    }
    if (emProvider) emProvider.textContent = (em.provider || "none").toUpperCase();
    if (emServer) emServer.textContent = em.target || "Chưa cấu hình";
    if (emSender) emSender.textContent = em.from_email || "Chưa cấu hình";

    renderNotificationHistory(data.history || []);
  } catch (error) {
    console.error("Không thể tải trạng thái kênh thông báo:", error);
    renderNotificationHistory([
      {
        channel: "system",
        channel_label: "Hệ thống",
        event_type: "Trạng thái kênh thông báo",
        recipient: "Admin Portal",
        status: "active",
        status_label: "Sẵn sàng",
        message: "Hệ thống sẵn sàng gửi thông báo khi phát sinh sự cố hoặc yêu cầu thử nghiệm.",
      },
    ]);
  }
}

async function testNotification(channel) {
  const appState = getAppState();
  const appApi = getAppApi();
  const byId = getAppById;

  let messageId = "telegramTestMessage";
  let buttonId = "testTelegramBtn";
  let targetEmail = "";
  if (channel === "discord") {
    messageId = "discordTestMessage";
    buttonId = "testDiscordBtn";
  } else if (channel === "email") {
    messageId = "emailTestMessage";
    buttonId = "testEmailBtn";
    targetEmail = byId("testEmailTarget")?.value.trim() || "";
    if (!targetEmail) {
      targetEmail = appState.user?.email || "admin@opsmind.internal";
      if (byId("testEmailTarget")) byId("testEmailTarget").value = targetEmail;
    }
  }
  const button = byId(buttonId);
  if (button) button.disabled = true;
  setAppMessage(messageId, "Đang gửi thông báo thử nghiệm...", false);
  try {
    const payload = { channel };
    if (targetEmail) payload.target_email = targetEmail;
    const result = await appApi("/admin/notifications/test", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setAppMessage(messageId, result.message || "Gửi thông báo thử nghiệm thành công.", false);
  } catch (error) {
    setAppMessage(messageId, error.message);
  } finally {
    if (button) button.disabled = false;
    await loadNotificationStatus();
  }
}

if (typeof window !== "undefined") {
  window.loadNotificationStatus = loadNotificationStatus;
  window.testNotification = testNotification;
  window.renderNotificationHistory = renderNotificationHistory;
}
})();
