async function loadNotificationStatus() {
  if (state.user?.role !== "admin") return;
  try {
    const data = await api("/admin/notifications/status");
    const tg = data.telegram || {};
    const tgBadge = byId("telegramStatusBadge");
    const tgUser = byId("telegramBotUsername");
    const tgChat = byId("telegramChatId");
    if (tgBadge) {
      tgBadge.textContent = tg.enabled ? "Đã kết nối" : "Chưa kết nối";
      tgBadge.className = `tag ${tg.enabled ? "tag-status-published" : "tag-status-draft"}`;
    }
    if (tgUser) tgUser.textContent = tg.enabled ? "Đã cấu hình" : "Chưa cấu hình";
    if (tgChat) tgChat.textContent = tg.target || "Chưa cấu hình";

    const dc = data.discord || {};
    const dcBadge = byId("discordStatusBadge");
    const dcUrl = byId("discordWebhookUrl");
    if (dcBadge) {
      dcBadge.textContent = dc.enabled ? "Đã kết nối" : "Chưa kết nối";
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
  } catch (error) {
    console.error("Không thể tải trạng thái kênh thông báo:", error);
  }
}

async function testNotification(channel) {
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
  }
  const button = byId(buttonId);
  if (button) button.disabled = true;
  setMessage(messageId, "Đang gửi thông báo thử nghiệm...", false);
  try {
    const payload = { channel };
    if (targetEmail) payload.target_email = targetEmail;
    const result = await api("/admin/notifications/test", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setMessage(messageId, result.message || "Gửi thông báo thử nghiệm thành công.", false);
  } catch (error) {
    setMessage(messageId, error.message);
  } finally {
    if (button) button.disabled = false;
  }
}

if (typeof window !== "undefined") {
  window.loadNotificationStatus = loadNotificationStatus;
  window.testNotification = testNotification;
}
