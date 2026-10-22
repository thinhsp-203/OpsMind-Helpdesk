const state = {
  token: localStorage.getItem("helpdesk-token") || "",
  user: null,
  tickets: [],
  staff: [],
  chatSessionId: null,
  activeView: "",
  knowledgeDocs: [],
  knowledgeStatus: "",
  knowledgeCategory: "",
  knowledgeSearch: "",
};

const byId = (id) => document.getElementById(id);
const alertUser = (message) => window.alert(window.helpdeskI18n.translate(message));

if (typeof window !== "undefined") {
  window.state = state;
  window.byId = byId;
  window.alertUser = alertUser;
}
const statusLabels = {
  new: "Mới",
  in_progress: "Đang xử lý",
  pending_waiting_user: "Chờ người gửi",
  resolved: "Đã giải quyết",
  closed: "Đã đóng",
  escalated: "Chuyển cấp",
  published: "Đã xuất bản",
  pending_review: "Chờ duyệt",
  draft: "Bản nháp",
  archived: "Đã lưu trữ",
};
const priorityLabels = { low: "P4 · Thấp", medium: "P3 · Thông thường", high: "P2 · Cao", urgent: "P1 · Khẩn cấp" };
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
  if (!target) return;
  target.textContent = window.helpdeskI18n.translate(message);
  target.classList.toggle("success-message", !isError && Boolean(message));
}

if (typeof window !== "undefined") {
  window.node = node;
  window.setMessage = setMessage;
}

async function loadPublicConfig() {
  try {
    const response = await fetch("/config");
    if (!response.ok) throw new Error(`Không tải được cấu hình (${response.status}).`);
    const config = await response.json();
    const demoEl = byId("demoCredentials");
    if (demoEl) {
      if (config.demo_mode) {
        demoEl.classList.remove("hidden");
      } else {
        demoEl.classList.add("hidden");
        demoEl.innerHTML = "";
      }
    }
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
    if (response.status === 401 && state.token) {
      const savedUser = state.user?.username || byId("username")?.value || "";
      signOut();
      if (savedUser && byId("username")) {
        byId("username").value = savedUser;
      }
      if (byId("password")) {
        byId("password").value = "";
        byId("password").focus();
      }
      setMessage("loginMessage", "Phiên đăng nhập đã hết hạn hoặc mật khẩu đã thay đổi. Vui lòng đăng nhập lại.");
    }
    let detailMsg = data?.detail;
    if (Array.isArray(detailMsg)) {
      detailMsg = detailMsg
        .map((err) => {
          if (err && typeof err === "object" && err.msg) {
            const m = String(err.msg);
            if (m.includes("at least 12 characters")) return "Mật khẩu mới phải có ít nhất 12 ký tự.";
            if (m.includes("at least 16 characters")) return "Mã xác thực phải có ít nhất 16 ký tự.";
            if (m.includes("at least 3 characters")) return "Vui lòng nhập tối thiểu 3 ký tự.";
            if (m.includes("at least 5 characters")) return "Tiêu đề phải có ít nhất 5 ký tự.";
            if (m.includes("at least 10 characters")) return "Mô tả phải có ít nhất 10 ký tự.";
            if (m.includes("at least 1 characters")) return "Vui lòng không để trống trường này.";
            if (m.includes("at most 200 characters")) return "Mật khẩu tối đa 200 ký tự.";
            if (m.includes("at most 160 characters")) return "Tiêu đề tối đa 160 ký tự.";
            if (m.includes("at most 5000 characters")) return "Mô tả tối đa 5000 ký tự.";
            if (m.includes("Field required")) return "Vui lòng điền đầy đủ các trường bắt buộc.";
            if (m.startsWith("Value error, ")) return m.replace("Value error, ", "").trim();
            if (m.includes("Input should be a valid string")) return "Dữ liệu không hợp lệ.";
            return err.msg;
          }
          return typeof err === "string" ? err : JSON.stringify(err);
        })
        .join("; ");
    } else if (typeof detailMsg === "object" && detailMsg !== null) {
      detailMsg = detailMsg.message || JSON.stringify(detailMsg);
    }
    const error = new Error(detailMsg || `Yêu cầu thất bại (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return data;
}

if (typeof window !== "undefined") {
  window.api = api;
}

function toggleUserDropdown() {
  const menu = byId("userDropdownMenu");
  const btn = byId("userMenuBtn");
  if (!menu || !btn) return;
  const isExpanded = btn.getAttribute("aria-expanded") === "true";
  btn.setAttribute("aria-expanded", String(!isExpanded));
  menu.classList.toggle("hidden", isExpanded);
}

function closeUserDropdown() {
  const menu = byId("userDropdownMenu");
  const btn = byId("userMenuBtn");
  if (!menu || !btn) return;
  btn.setAttribute("aria-expanded", "false");
  menu.classList.add("hidden");
}

function setSignedIn(user) {
  byId("ticketReceipt").classList.add("hidden");
  document.body.classList.add("signed-in");
  byId("workspaceSidebar").classList.remove("hidden");
  byId("workspacePageLabel").classList.remove("hidden");
  const displayName = user.full_name || user.username;
  const initials = displayName.slice(0, 2).toUpperCase();
  const avatarEl = byId("sidebarAvatar");
  if (avatarEl) avatarEl.textContent = initials;
  byId("sidebarUsername").textContent = displayName;
  byId("sidebarRole").textContent = roleLabels[user.role] || user.role;
  state.user = user;
  clearTicketFilters();
  byId("workspaceView").dataset.role = user.role;
  byId("loginView").classList.add("hidden");
  byId("workspaceView").classList.remove("hidden");

  // Modern unified user dropdown
  byId("userMenuWrapper")?.classList.remove("hidden");
  const topbarAv = byId("topbarAvatar");
  if (topbarAv) topbarAv.textContent = initials;
  const topbarName = byId("topbarUserName");
  if (topbarName) topbarName.textContent = displayName;
  const topbarRole = byId("topbarUserRole");
  if (topbarRole) topbarRole.textContent = roleLabels[user.role] || user.role;

  const dropAv = byId("dropdownAvatarLarge");
  if (dropAv) dropAv.textContent = initials;
  const dropFullname = byId("dropdownUserFullname");
  if (dropFullname) dropFullname.textContent = displayName;
  const dropRole = byId("dropdownUserRole");
  if (dropRole) dropRole.textContent = `@${user.username} · ${roleLabels[user.role] || user.role}`;
  closeUserDropdown();

  byId("logoutBtn")?.classList.remove("hidden");
  byId("openProfileBtn")?.classList.remove("hidden");
  byId("changePasswordBtn")?.classList.remove("hidden");
  const badge = byId("userBadge");
  if (badge) {
    badge.textContent = `${displayName} · ${roleLabels[user.role] || user.role}`;
    badge.classList.add("hidden");
  }
  byId("greeting").textContent = `Xin chào, ${displayName}`;
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
  byId("serviceCatalogSection")?.classList.toggle("hidden", isStaff);
  byId("analyticsSection").classList.remove("hidden");
  byId("statResolutionCard").classList.toggle("hidden", !isStaff);
  byId("statRatingCard").classList.toggle("hidden", !isStaff);
  byId("knowledgePanel").classList.toggle("hidden", !isStaff);
  byId("toggleUploadKnowledgeBtn").classList.toggle("hidden", user.role !== "admin");
  byId("adminUsersPanel").classList.toggle("hidden", user.role !== "admin");
  byId("adminNotificationsPanel")?.classList.toggle("hidden", user.role !== "admin");
  byId("assistantTitle").textContent = isStaff ? "Tra cứu runbook IT" : "IT Helpdesk Agent";
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
    try {
      const me = await api("/auth/me");
      setSignedIn(me);
    } catch (error) {
      if (!state.token) throw error;
      setSignedIn({ username: result.username, role: result.role });
    }
    if (result.force_password_change) {
      openChangePasswordModal(true);
    }
  } catch (error) {
    setMessage("loginMessage", error.message);
  }
}

async function logout() {
  if (state.logoutBusy) return;
  state.logoutBusy = true;
  const token = state.token;
  signOut();
  if (!token) {
    state.logoutBusy = false;
    return;
  }
  setMessage("loginMessage", "Đang xác nhận thu hồi phiên trên máy chủ...", false);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  try {
    // Use the captured token, independently of any subsequent login in this tab.
    const response = await fetch("/auth/logout", {
      method: "POST", headers: {Authorization: `Bearer ${token}`}, signal: controller.signal,
    });
    let message;
    if (response.status === 401) {
      message = "Phiên gửi lên không còn hiệu lực; dữ liệu đăng nhập trên trình duyệt đã được xóa.";
    } else {
      if (!response.ok) throw new Error("logout unconfirmed");
      const result = await response.json();
      if (result.revoked === true) {
        message = "Đã đăng xuất và thu hồi các phiên đăng nhập hiện hành của tài khoản.";
      } else if (result.revoked === false) {
        message = "Phiên gửi lên không còn hiệu lực; dữ liệu đăng nhập trên trình duyệt đã được xóa.";
      } else {
        throw new Error("logout response unconfirmed");
      }
    }
    if (!state.token) setMessage("loginMessage", message, false);
  } catch {
    if (!state.token) setMessage("loginMessage", "Chỉ đã xóa phiên trên trình duyệt; chưa xác nhận thu hồi trên máy chủ. Khi có kết nối, đăng nhập rồi đăng xuất lại.");
  } finally {
    clearTimeout(timer);
    state.logoutBusy = false;
  }
}

function signOut() {
  state.ticketRequestId = (state.ticketRequestId || 0) + 1;
  document.body.classList.remove("signed-in");
  byId("workspaceSidebar").classList.add("hidden");
  byId("workspacePageLabel").classList.add("hidden");
  byId("ragResult").replaceChildren();
  byId("ragResult").classList.add("hidden");
  byId("ragQuestion").value = "";
  state.token = "";
  state.user = null;
  state.tickets = [];
  state.chatSessionId = null;
  localStorage.removeItem("helpdesk-token");
  if (byId("password")) byId("password").value = "";
  byId("workspaceView").classList.add("hidden");
  byId("userMenuWrapper")?.classList.add("hidden");
  closeUserDropdown();
  byId("userBadge")?.classList.add("hidden");
  closeUserProfileModal();
  if (byId("changePasswordModal")) byId("changePasswordModal").dataset.forced = "false";
  closeChangePasswordModal();
  closeForgotPasswordModal();
  closeResetPasswordModal();
  byId("loginView").classList.remove("hidden");
  byId("loginMessage").textContent = "";
  byId("ticketList").replaceChildren();
  byId("workspaceView").dataset.role = "";
}

function openChangePasswordModal(isForced = false) {
  closeUserDropdown();
  const modal = byId("changePasswordModal");
  if (!modal) return;
  modal.dataset.forced = isForced ? "true" : "false";
  const cancelBtn = byId("cancelChangePasswordBtn");
  if (cancelBtn) {
    cancelBtn.classList.remove("hidden");
    cancelBtn.textContent = window.helpdeskI18n.translate(isForced ? "Đăng xuất" : "Hủy");
  }
  const subtitle = byId("changePasswordSubtitle");
  if (subtitle) {
    subtitle.textContent = window.helpdeskI18n.translate(
      isForced
        ? "Quản trị viên yêu cầu bạn đổi mật khẩu trước khi tiếp tục."
        : "Mật khẩu mới phải có ít nhất 12 ký tự và khác mật khẩu hiện tại."
    );
  }
  byId("changePasswordForm").reset();
  setMessage("changePasswordMessage", "");
  modal.classList.remove("hidden");
  byId("currentPasswordInput").focus();
}

function closeChangePasswordModal() {
  const modal = byId("changePasswordModal");
  if (!modal) return;
  if (modal.dataset.forced === "true") return;
  modal.classList.add("hidden");
  byId("changePasswordForm").reset();
  setMessage("changePasswordMessage", "");
}

function openUserProfileModal() {
  closeUserDropdown();
  const modal = byId("userProfileModal");
  if (!modal || !state.user) return;
  const user = state.user;
  const displayName = user.full_name || user.username;
  const initials = displayName.slice(0, 2).toUpperCase();

  const avatarEl = byId("profileAvatarLarge");
  if (avatarEl) avatarEl.textContent = initials;
  const nameEl = byId("profileDisplayName");
  if (nameEl) nameEl.textContent = displayName;
  const tagEl = byId("profileUsernameTag");
  if (tagEl) tagEl.textContent = `@${user.username}`;
  const roleEl = byId("profileRoleBadge");
  if (roleEl) roleEl.textContent = roleLabels[user.role] || user.role;

  const fnInput = byId("profileFullNameInput");
  if (fnInput) fnInput.value = user.full_name || "";
  const emailInput = byId("profileEmailInput");
  if (emailInput) emailInput.value = user.email || "";
  const deptInput = byId("profileDepartmentInput");
  if (deptInput) deptInput.value = user.department || "";
  const phoneInput = byId("profilePhoneInput");
  if (phoneInput) phoneInput.value = user.phone || "";
  const pwdConfirmInput = byId("profileCurrentPasswordInput");
  if (pwdConfirmInput) pwdConfirmInput.value = "";

  const activity = user.activity || {};
  const statCreated = byId("profileStatCreated");
  if (statCreated) statCreated.textContent = String(activity.tickets_created ?? 0);
  const statAssigned = byId("profileStatAssigned");
  if (statAssigned) statAssigned.textContent = String(activity.tickets_assigned ?? 0);
  const statResolved = byId("profileStatResolved");
  if (statResolved) statResolved.textContent = String(activity.tickets_resolved ?? 0);
  byId("profileStatAssignedWrap")?.classList.toggle("hidden", user.role === "user");

  const pwdEl = byId("profilePwdChangedAt");
  if (pwdEl) {
    const pwdAt = user.password_changed_at;
    if (pwdAt) {
      try {
        pwdEl.textContent = new Intl.DateTimeFormat(window.helpdeskI18n.locale(), {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }).format(new Date(pwdAt));
      } catch {
        pwdEl.textContent = pwdAt;
      }
    } else {
      pwdEl.textContent = window.helpdeskI18n.translate("Chưa cập nhật");
    }
  }

  setMessage("userProfileMessage", "");
  modal.classList.remove("hidden");
  byId("profileFullNameInput")?.focus();
}

function closeUserProfileModal() {
  const modal = byId("userProfileModal");
  if (!modal) return;
  modal.classList.add("hidden");
  const pwdConfirmInput = byId("profileCurrentPasswordInput");
  if (pwdConfirmInput) pwdConfirmInput.value = "";
  setMessage("userProfileMessage", "");
}

async function handleProfileUpdate(event) {
  event.preventDefault();
  const fullName = byId("profileFullNameInput")?.value.trim() || "";
  const email = byId("profileEmailInput")?.value.trim() || "";
  const department = byId("profileDepartmentInput")?.value.trim() || "";
  const phone = byId("profilePhoneInput")?.value.trim() || "";
  const currentPassword = byId("profileCurrentPasswordInput")?.value || "";

  setMessage("userProfileMessage", "Đang lưu thông tin cá nhân...", false);
  try {
    const payload = {
      full_name: fullName,
      email,
      department,
      phone,
    };
    if (currentPassword) {
      payload.current_password = currentPassword;
    }
    const result = await api("/auth/profile", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    state.user = { ...state.user, ...result.profile };
    const pwdConfirmInput = byId("profileCurrentPasswordInput");
    if (pwdConfirmInput) pwdConfirmInput.value = "";
    const displayName = state.user.full_name || state.user.username;
    const initials = displayName.slice(0, 2).toUpperCase();
    const avatarEl = byId("sidebarAvatar");
    if (avatarEl) avatarEl.textContent = initials;
    byId("sidebarUsername").textContent = displayName;
    const profileAvatar = byId("profileAvatarLarge");
    if (profileAvatar) profileAvatar.textContent = initials;
    byId("profileDisplayName").textContent = displayName;
    const topbarAv = byId("topbarAvatar");
    if (topbarAv) topbarAv.textContent = initials;
    const topbarName = byId("topbarUserName");
    if (topbarName) topbarName.textContent = displayName;
    const dropAv = byId("dropdownAvatarLarge");
    if (dropAv) dropAv.textContent = initials;
    const dropFullname = byId("dropdownUserFullname");
    if (dropFullname) dropFullname.textContent = displayName;
    byId("greeting").textContent = `Xin chào, ${displayName}`;
    const badge = byId("userBadge");
    if (badge) badge.textContent = `${displayName} · ${roleLabels[state.user.role] || state.user.role}`;
    setMessage("userProfileMessage", result.message || "Cập nhật thông tin cá nhân thành công.", false);
    setTimeout(() => {
      closeUserProfileModal();
    }, 1200);
  } catch (error) {
    setMessage("userProfileMessage", error.message || "Không thể cập nhật thông tin cá nhân.");
  }
}

async function handleChangePassword(event) {
  event.preventDefault();
  const currentPassword = byId("currentPasswordInput").value;
  const newPassword = byId("newPasswordInput").value;
  const confirmPassword = byId("confirmPasswordInput").value;

  if (newPassword !== confirmPassword) {
    setMessage("changePasswordMessage", "Mật khẩu xác nhận không khớp.");
    return;
  }

  setMessage("changePasswordMessage", "Đang lưu...", false);
  try {
    const currentUsername = state.user?.username || byId("username")?.value || "";
    const result = await api("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        old_password: currentPassword,
        new_password: newPassword,
      }),
    });
    const finalUsername = result.username || currentUsername;
    const modal = byId("changePasswordModal");
    if (modal) {
      modal.dataset.forced = "false";
      modal.classList.add("hidden");
    }
    closeUserProfileModal();
    signOut();
    if (finalUsername && byId("username")) {
      byId("username").value = finalUsername;
    }
    if (byId("password")) {
      byId("password").value = "";
      byId("password").focus();
    }
    setMessage("loginMessage", result.message || "Đổi mật khẩu thành công. Vui lòng đăng nhập lại bằng mật khẩu mới.", false);
  } catch (error) {
    setMessage("changePasswordMessage", error.message);
  }
}

function openForgotPasswordModal() {
  signOut();
  const modal = byId("forgotPasswordModal");
  if (!modal) return;
  byId("forgotPasswordForm")?.reset();
  setMessage("forgotPasswordMessage", "");
  modal.classList.remove("hidden");
  byId("forgotIdentifierInput")?.focus();
}

function closeForgotPasswordModal() {
  const modal = byId("forgotPasswordModal");
  if (!modal) return;
  modal.classList.add("hidden");
  byId("forgotPasswordForm")?.reset();
  setMessage("forgotPasswordMessage", "");
}

async function handleForgotPassword(event) {
  event.preventDefault();
  const input = byId("forgotIdentifierInput");
  const identifier = input ? input.value.trim() : "";
  if (!identifier) return;
  setMessage("forgotPasswordMessage", "Đang gửi yêu cầu...", false);
  try {
    const result = await api("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    });
    setMessage("forgotPasswordMessage", result.message, false);
  } catch (error) {
    setMessage("forgotPasswordMessage", error.message);
  }
}

function openResetPasswordModal(token = "") {
  signOut();
  const modal = byId("resetPasswordModal");
  if (!modal) return;
  byId("resetPasswordForm")?.reset();
  setMessage("resetPasswordMessage", "");
  if (token) {
    byId("resetTokenInput").value = token;
  }
  modal.classList.remove("hidden");
  if (token) {
    byId("resetNewPasswordInput")?.focus();
  } else {
    byId("resetTokenInput")?.focus();
  }
}

function closeResetPasswordModal() {
  const modal = byId("resetPasswordModal");
  if (!modal) return;
  modal.classList.add("hidden");
  byId("resetPasswordForm")?.reset();
  setMessage("resetPasswordMessage", "");
  if (window.location.hash.includes("reset-token")) {
    history.replaceState(null, "", window.location.pathname);
  }
}

async function handleResetPassword(event) {
  event.preventDefault();
  const token = byId("resetTokenInput").value.trim();
  const newPassword = byId("resetNewPasswordInput").value;
  const confirmPassword = byId("resetConfirmPasswordInput").value;

  if (newPassword !== confirmPassword) {
    setMessage("resetPasswordMessage", "Mật khẩu xác nhận không khớp.");
    return;
  }

  if (newPassword.length < 12) {
    setMessage("resetPasswordMessage", "Mật khẩu mới phải có ít nhất 12 ký tự.");
    return;
  }

  setMessage("resetPasswordMessage", "Đang cập nhật mật khẩu...", false);
  try {
    const result = await api("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    });
    const targetUsername = result.username || "";
    closeResetPasswordModal();
    signOut();
    if (targetUsername && byId("username")) {
      byId("username").value = targetUsername;
    }
    if (byId("password")) {
      byId("password").value = "";
      byId("password").focus();
    }
    setMessage("loginMessage", result.message || "Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại.", false);
    if (window.location.hash.includes("reset-token")) {
      history.replaceState(null, "", window.location.pathname);
    }
  } catch (error) {
    setMessage("resetPasswordMessage", error.message);
  }
}

function checkResetPasswordTokenInUrl() {
  const hash = window.location.hash || "";
  const match = hash.match(/reset-token=([^&]+)/);
  if (match && match[1]) {
    signOut();
    const token = decodeURIComponent(match[1]);
    openResetPasswordModal(token);
  }
}

function openEmergencyModal() {
  const modal = byId("emergencyModal");
  if (!modal) return;
  const form = byId("emergencyTicketForm");
  if (form && form.dataset.submitting !== "true") {
    form.reset();
    delete form.dataset.ticketCreated;
    form.querySelector('button[type="submit"]').disabled = false;
    setMessage("emergencyMessage", "");
  }
  modal.classList.remove("hidden");
  byId("emergencyDescriptionInput")?.focus();
}

function closeEmergencyModal() {
  byId("emergencyModal")?.classList.add("hidden");
}

async function handleEmergencyTicket(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (form.dataset.submitting === "true" || form.dataset.ticketCreated === "true") return;
  const submitBtn = form.querySelector('button[type="submit"]');
  const title = byId("emergencyTitleInput")?.value.trim() || "Sự cố bảo mật khẩn cấp";
  const desc = byId("emergencyDescriptionInput")?.value.trim() || "";
  if (desc.length < 10) {
    setMessage("emergencyMessage", "Vui lòng mô tả ít nhất 10 ký tự về triệu chứng sự cố.");
    return;
  }
  const translate = window.helpdeskI18n.translate;
  form.dataset.submitting = "true";
  submitBtn.disabled = true;
  setMessage("emergencyMessage", "Đang tạo ticket P1...", false);
  try {
    const result = await api("/tickets", {
      method: "POST",
      body: JSON.stringify({
        title,
        description: `${desc}\n\n[SỰ CỐ BẢO MẬT KHẨN CẤP P1]`,
        category: "security",
        priority: "urgent",
      }),
    });
    // A successful POST does not contain a delivery or responder acknowledgement.
    form.dataset.ticketCreated = "true";
    const ticketId = result?.ticket?.id;
    if (!Number.isSafeInteger(ticketId) || ticketId <= 0) {
      setMessage("emergencyMessage", "Chưa xác định được mã ticket từ phản hồi. Kiểm tra danh sách trước khi gửi lại.");
      return;
    }
    const receipt = `${translate("Đã tạo ticket P1")} HD-${String(ticketId).padStart(4, "0")}. ${translate("Chưa có xác nhận gửi thông báo hoặc nhân viên tiếp nhận. Nếu cần hỗ trợ ngay, liên hệ IT qua kênh nội bộ.")}`;
    setMessage("emergencyMessage", receipt, false);
    try {
      await refreshWorkspace();
    } catch {
      setMessage("emergencyMessage", `${receipt} ${translate("Chưa tải lại được danh sách; không cần gửi lại ticket.")}`, false);
    }
  } catch (error) {
    setMessage("emergencyMessage", `${translate(error.message || "Không xác nhận được việc tạo ticket.")} ${translate("Kiểm tra danh sách trước khi thử lại.")}`);
  } finally {
    delete form.dataset.submitting;
    submitBtn.disabled = form.dataset.ticketCreated === "true";
  }
}

async function refreshWorkspace() {
  if (byId("knowledgeCategoryFilter")) {
    state.knowledgeCategory = byId("knowledgeCategoryFilter").value;
  }
  if (byId("knowledgeSearch")) {
    state.knowledgeSearch = byId("knowledgeSearch").value.trim();
  }
  if (state.user.role !== "user") state.staff = await api("/staff");
  await Promise.all([
    loadTickets(),
    state.user.role !== "user" ? loadKnowledge() : Promise.resolve(),
  ]);
  if (state.user.role !== "user") await loadAnalytics();
  if (state.user.role === "agent") await loadAgentAnalytics();
  if (state.user.role === "admin") {
    await loadAdminUsers();
    await loadNotificationStatus();
  }
  await loadRagSessions();
}

function configureWorkspaceNavigation(role) {
  const items = role === "user"
    ? [["dashboard", "Tổng quan"], ["assistant", "Trợ lý IT"], ["tickets", "Ticket của tôi"], ["submit", "Tạo yêu cầu"]]
    : role === "agent"
      ? [["dashboard", "Tổng quan"], ["tickets", "Hàng đợi"], ["personal", "Thống kê của tôi"], ["assistant", "Tra cứu tri thức"], ["knowledge", "Kho tri thức"]]
      : [["dashboard", "Tổng quan"], ["tickets", "Hàng đợi"], ["assistant", "Tra cứu tri thức"], ["knowledge", "Kho tri thức"], ["users", "Người dùng"], ["notifications", "Kênh thông báo"], ["reports", "Báo cáo"]];
  const nav = byId("workspaceNav");
  nav.replaceChildren();
  items.forEach(([view, label]) => {
    const button = node("button", "workspace-nav-button", label);
    button.type = "button";
    button.dataset.view = view;
    button.dataset.label = label;
    const icons = { dashboard: "▦", assistant: "✦", tickets: "▤", submit: "+", knowledge: "▧", users: "♙", notifications: "🔔", reports: "▥", personal: "◷" };
    const icon = node("span", "nav-icon", icons[view] || "•");
    icon.setAttribute("aria-hidden", "true");
    button.prepend(icon);
    button.addEventListener("click", () => setWorkspaceView(view));
    nav.append(button);
  });
  nav.classList.remove("hidden");
}

function setWorkspaceView(view) {
  state.activeView = view;
  byId("workspaceView").dataset.view = view;
  byId("assistantContext").classList.toggle("hidden", view !== "assistant");
  const activeButton = document.querySelector(`.workspace-nav-button[data-view="${view}"]`);
  byId("workspacePageLabel").textContent = window.helpdeskI18n.translate(activeButton?.dataset.label || "OpsMind");

  document.querySelectorAll("#workspaceView .workspace-panel").forEach((panel) => {
    const views = panel.dataset.view.split(/\s+/);
    const roleHidden = (
      (panel.id === "employeeWorkflowNote" || panel.id === "serviceCatalogSection") && state.user?.role !== "user"
    ) || (
      panel.id === "assistantPanel" && view === "dashboard" && state.user?.role !== "user"
    );
    panel.classList.toggle("hidden", roleHidden || !views.includes(view));
  });
  document.querySelectorAll(".workspace-nav-button").forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle("active", active);
    button.setAttribute("aria-current", active ? "page" : "false");
  });

  if (view === "assistant") loadAssistantTickets();
  if (view === "notifications" && state.user?.role === "admin") {
    try {
      loadNotificationStatus();
    } catch (e) {
      console.error("Lỗi khi gọi loadNotificationStatus:", e);
    }
  }
}

function filterQueueTickets(tickets, mode, username, now = Date.now()) {
  return tickets.filter((ticket) => {
    const active = !["resolved", "closed"].includes(ticket.status);
    const remaining = new Date(ticket.sla_deadline).getTime() - now;
    if (mode === "unassigned") return active && !ticket.assignee;
    if (mode === "mine") return active && ticket.assignee === username;
    if (mode === "soon") return active && remaining >= 0 && remaining <= 2 * 60 * 60 * 1000;
    if (mode === "overdue") return active && remaining < 0;
    return true;
  });
}

const auditEventLabels = {
  created: "Tạo ticket", assigned: "Phân công", status_changed: "Thay đổi trạng thái",
  comment_added: "Thêm phản hồi", ticket_updated: "Cập nhật ticket",
  archived: "Lưu trữ ticket", attachment_added: "Thêm tệp đính kèm",
};

function hasTicketFilters() {
  return ["ticketSearch", "statusFilter", "categoryFilter", "fromDateFilter", "toDateFilter", "queueFilter"]
    .some((id) => (id !== "queueFilter" || state.user?.role !== "user") && byId(id).value.trim());
}

function clearTicketFilters() {
  ["ticketSearch", "statusFilter", "categoryFilter", "fromDateFilter", "toDateFilter", "queueFilter"]
    .forEach((id) => { byId(id).value = ""; });
}

async function loadTickets() {
  const requestId = state.ticketRequestId = (state.ticketRequestId || 0) + 1;
  const params = new URLSearchParams();
  const search = byId("ticketSearch").value.trim();
  const status = byId("statusFilter").value;
  const category = byId("categoryFilter").value;
  const fromDate = byId("fromDateFilter").value;
  const toDate = byId("toDateFilter").value;
  if (fromDate && toDate && fromDate > toDate) {
    byId("ticketCount").textContent = "—";
    showEmpty("Khoảng ngày chưa hợp lệ", "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.");
    return;
  }
  if (search) params.set("q", search);
  if (status) params.set("status", status);
  if (category) params.set("category", category);
  if (fromDate) params.set("from", fromDate);
  if (toDate) params.set("to", toDate);
  byId("ticketList").replaceChildren(node("div", "empty-state", "Đang tải yêu cầu..."));
  try {
    const loadedTickets = await api(`/tickets?${params.toString()}`);
    if (requestId !== state.ticketRequestId || !state.user) return;
    state.tickets = loadedTickets;
    if (state.user.role === "user") {
      const tickets = search || status || category || fromDate || toDate
        ? await api("/tickets")
        : state.tickets;
      if (requestId !== state.ticketRequestId || !state.user) return;
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
      if (byId("statSelfService")) byId("statSelfService").textContent = "—";
    }
    byId("queueFilter").classList.toggle("hidden", state.user.role === "user");
    renderTickets(filterQueueTickets(state.tickets,
      state.user.role === "user" ? "" : byId("queueFilter").value, state.user.username));
  } catch (error) {
    if (requestId !== state.ticketRequestId || !state.user) return;
    byId("ticketCount").textContent = "—";
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
    if (hasTicketFilters()) {
      showEmpty("Không có yêu cầu khớp bộ lọc", "Thử thay đổi điều kiện hoặc bấm Bỏ bộ lọc để xem lại danh sách.");
      return;
    }
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
    node("span", `tag tag-priority-${ticket.priority} ${["urgent", "high"].includes(ticket.priority) ? `tag-${ticket.priority}` : ""}`, priorityLabels[ticket.priority] || ticket.priority),
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
  if (state.user.role !== "user" && ["resolved", "closed"].includes(ticket.status)) {
    const createRunbookBtn = node("button", "button button-soft", "Tạo Runbook từ ticket");
    createRunbookBtn.type = "button";
    createRunbookBtn.addEventListener("click", () => {
      openKnowledgeEditorForTicket(ticket);
    });
    detailsBody.append(createRunbookBtn);
  }
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

  const assignmentLocked = ["resolved", "closed"].includes(ticket.status);
  const assigneeSelect = document.createElement("select");
  assigneeSelect.disabled = assignmentLocked;
  if (assignmentLocked) {
    assigneeSelect.title = window.helpdeskI18n.translate("Không thể đổi phân công khi ticket đã giải quyết hoặc đóng.");
  }
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
  assignButton.disabled = assignmentLocked || !state.staff.length || !ticket.assignee;
  assigneeSelect.addEventListener("change", () => {
    assignButton.disabled = assignmentLocked || !assigneeSelect.value;
  });
  assignButton.addEventListener("click", async () => {
    if (assignmentLocked) return;
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
      headers: { Authorization: `Bearer ${state.token}` },
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
  if (state.ticketBusy) return;
  state.ticketBusy = true;
  const form = event.currentTarget;
  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  form.setAttribute("aria-busy", "true");
  setMessage("ticketMessage", "");
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    const created = await api("/tickets", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    byId("ticketSearch").value = "";
    byId("statusFilter").value = "";
    byId("categoryFilter").value = "";
    byId("fromDateFilter").value = "";
    byId("toDateFilter").value = "";
    setMessage("ticketMessage", "Đã gửi yêu cầu. Mã ticket và tiến độ được lưu trong mục bên dưới.", false);
    await refreshWorkspace();
    setWorkspaceView("tickets");
    const receipt = byId("ticketReceipt");
    receipt.textContent = `${window.helpdeskI18n.translate("Đã tạo yêu cầu")} HD-${String(created.ticket.id).padStart(4, "0")}. ${window.helpdeskI18n.translate("Bạn có thể theo dõi tiến độ trong danh sách bên dưới.")}`;
    receipt.classList.remove("hidden");
    const firstTicket = byId("ticketList").querySelector(".ticket-card");
    firstTicket?.scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (error) {
    setMessage("ticketMessage", error.message);
  } finally {
    state.ticketBusy = false;
    submitButton.disabled = false;
    form.removeAttribute("aria-busy");
  }
}

function buildHandoffDescription(question, matches = []) {
  const sources = [...new Set(matches.map((match) => match.source).filter(Boolean))];
  if (!sources.length) return question;
  const heading = window.helpdeskI18n.translate("Tài liệu đã được gợi ý (chưa xác nhận đã thực hiện):");
  const note = window.helpdeskI18n.translate("Vui lòng bổ sung các bước bạn đã thử và kết quả trước khi gửi.");
  return `${question}\n\n${heading}\n${sources.slice(0, 5).map((source) => `- ${String(source).slice(0, 180)}`).join("\n")}\n\n${note}`.slice(0, 5000);
}

async function askKnowledge(event, options = {}) {
  event?.preventDefault();
  const question = (options.question || byId("ragQuestion").value).trim();
  if (!question) {
    showRagResult("Nhập mô tả sự cố để tìm hướng dẫn.");
    byId("ragQuestion").focus();
    return;
  }
  setWorkspaceView("assistant");
  if (state.ragBusy) return;
  state.ragBusy = true;
  const sendButton = byId("ragForm").querySelector('button[type="submit"]');
  sendButton.disabled = true;
  byId("ragForm").setAttribute("aria-busy", "true");
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
    result.replaceChildren(node("div", "question-bubble", question), node("p", "rag-answer", data.answer));
    result.append(node("p", `rag-evidence ${data.grounded ? "" : "rag-evidence-empty"}`,
      data.grounded ? "Có tài liệu tham khảo — hãy đối chiếu trước khi thực hiện." : "Chưa tìm thấy nguồn phù hợp. Bạn có thể bổ sung thông tin hoặc chuyển cho IT."));
    if (data.sources.length) {
      const sourceCard = (match, source, index) => {
        const card = node("div", "rag-source");
        const heading = node("strong", "", `${index + 1}. ${source.title} · ${source.source}`);
        card.append(heading, renderRunbook(match.content));
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
  } finally {
    state.ragBusy = false;
    sendButton.disabled = false;
    byId("ragForm").removeAttribute("aria-busy");
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
        setWorkspaceView("tickets");
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
    byId("ticketDescription").value = buildHandoffDescription(question, options.matches);
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

// Knowledge Base methods are modularized in /static/modules/knowledge.js
const loadKnowledge = () => (window.loadKnowledge ? window.loadKnowledge() : Promise.resolve());
const uploadKnowledge = (event) => (window.uploadKnowledge ? window.uploadKnowledge(event) : Promise.resolve());

const updateLivePreview = () => (window.updateLivePreview ? window.updateLivePreview() : undefined);
const openKnowledgeEditor = (identifier) => (window.openKnowledgeEditor ? window.openKnowledgeEditor(identifier) : Promise.resolve());
const saveKnowledgeDocument = (event) => (window.saveKnowledgeDocument ? window.saveKnowledgeDocument(event) : Promise.resolve());
const openKnowledgeVersions = (identifier, title) => (window.openKnowledgeVersions ? window.openKnowledgeVersions(identifier, title) : Promise.resolve());
const openKnowledgeEditorForTicket = (ticket) => (window.openKnowledgeEditorForTicket ? window.openKnowledgeEditorForTicket(ticket) : undefined);
const loadAdminUsers = () => (window.loadAdminUsers ? window.loadAdminUsers() : Promise.resolve());
const createAdminUser = (event) => (window.createAdminUser ? window.createAdminUser(event) : Promise.resolve());
const loadNotificationStatus = () => (window.loadNotificationStatus ? window.loadNotificationStatus() : Promise.resolve());
const testNotification = (channel) => (window.testNotification ? window.testNotification(channel) : Promise.resolve());

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
    if (byId("statSelfService")) {
      const rate = analytics.helpful_feedback_rate !== undefined ? analytics.helpful_feedback_rate : analytics.self_service_rate;
      byId("statSelfService").textContent =
        rate !== null && rate !== undefined ? `${rate}%` : "—";
      const detail = byId("statSelfServiceDetail");
      if (detail) {
        if (analytics.total_feedback > 0) {
          detail.textContent = `${analytics.helpful_feedback_count}/${analytics.total_feedback} đánh giá hữu ích (${analytics.total_rag_queries} câu hỏi)`;
        } else {
          detail.textContent = "Chưa có phản hồi từ người dùng";
        }
      }
    }
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
        `${new Date(entry.timestamp).toLocaleString(window.helpdeskI18n.locale())} · ${entry.actor} · HD-${String(entry.ticket_id).padStart(4, "0")} · ${window.helpdeskI18n.translate(auditEventLabels[entry.event] || entry.event)}`,
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
      headers: { Authorization: `Bearer ${state.token}` },
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
byId("logoutBtn").addEventListener("click", logout);
byId("changePasswordBtn").addEventListener("click", () => openChangePasswordModal(false));
byId("cancelChangePasswordBtn").addEventListener("click", () => {
  if (byId("changePasswordModal")?.dataset.forced === "true") logout();
  else closeChangePasswordModal();
});
byId("changePasswordForm").addEventListener("submit", handleChangePassword);
const changePasswordModal = byId("changePasswordModal");
if (changePasswordModal) {
  changePasswordModal.addEventListener("click", (event) => {
    if (event.target === changePasswordModal && changePasswordModal.dataset.forced !== "true") {
      closeChangePasswordModal();
    }
  });
}

byId("openForgotPasswordBtn")?.addEventListener("click", openForgotPasswordModal);
byId("cancelForgotPasswordBtn")?.addEventListener("click", closeForgotPasswordModal);
byId("forgotPasswordForm")?.addEventListener("submit", handleForgotPassword);
const forgotPasswordModal = byId("forgotPasswordModal");
if (forgotPasswordModal) {
  forgotPasswordModal.addEventListener("click", (event) => {
    if (event.target === forgotPasswordModal) {
      closeForgotPasswordModal();
    }
  });
}

byId("cancelResetPasswordBtn")?.addEventListener("click", closeResetPasswordModal);
byId("resetPasswordForm")?.addEventListener("submit", handleResetPassword);
const resetPasswordModal = byId("resetPasswordModal");
if (resetPasswordModal) {
  resetPasswordModal.addEventListener("click", (event) => {
    if (event.target === resetPasswordModal) {
      closeResetPasswordModal();
    }
  });
}

byId("openProfileBtn")?.addEventListener("click", openUserProfileModal);
byId("sidebarUserProfileBtn")?.addEventListener("click", openUserProfileModal);
byId("sidebarUserProfileBtn")?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    openUserProfileModal();
  }
});
byId("userBadge")?.addEventListener("click", openUserProfileModal);
byId("closeUserProfileBtn")?.addEventListener("click", closeUserProfileModal);
byId("cancelUserProfileBtn")?.addEventListener("click", closeUserProfileModal);
byId("userProfileForm")?.addEventListener("submit", handleProfileUpdate);
byId("profileChangePasswordBtn")?.addEventListener("click", () => {
  closeUserProfileModal();
  openChangePasswordModal();
});
const userProfileModal = byId("userProfileModal");
if (userProfileModal) {
  userProfileModal.addEventListener("click", (event) => {
    if (event.target === userProfileModal) closeUserProfileModal();
  });
}

byId("userMenuBtn")?.addEventListener("click", (event) => {
  event.stopPropagation();
  toggleUserDropdown();
});

document.addEventListener("click", (event) => {
  const wrapper = byId("userMenuWrapper");
  if (wrapper && !wrapper.contains(event.target)) {
    closeUserDropdown();
  }
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeUserDropdown();
    closeUserProfileModal();
    closeChangePasswordModal();
    closeForgotPasswordModal();
    closeResetPasswordModal();
    closeEmergencyModal();
    byId("knowledgeEditorModal")?.classList.add("hidden");
    byId("knowledgeVersionsModal")?.classList.add("hidden");
  }
});

byId("openEmergencyModalBtn")?.addEventListener("click", openEmergencyModal);
byId("closeEmergencyModalBtn")?.addEventListener("click", closeEmergencyModal);
byId("cancelEmergencyBtn")?.addEventListener("click", closeEmergencyModal);
byId("emergencyTicketForm")?.addEventListener("submit", handleEmergencyTicket);
const emergencyModal = byId("emergencyModal");
if (emergencyModal) {
  emergencyModal.addEventListener("click", (event) => {
    if (event.target === emergencyModal) closeEmergencyModal();
  });
}
const knowledgeEditorModal = byId("knowledgeEditorModal");
if (knowledgeEditorModal) {
  knowledgeEditorModal.addEventListener("click", (event) => {
    if (event.target === knowledgeEditorModal) {
      knowledgeEditorModal.classList.add("hidden");
    }
  });
}
const knowledgeVersionsModal = byId("knowledgeVersionsModal");
if (knowledgeVersionsModal) {
  knowledgeVersionsModal.addEventListener("click", (event) => {
    if (event.target === knowledgeVersionsModal) {
      knowledgeVersionsModal.classList.add("hidden");
    }
  });
}

byId("refreshNotificationsBtn")?.addEventListener("click", loadNotificationStatus);
byId("testTelegramBtn")?.addEventListener("click", () => testNotification("telegram"));
byId("testDiscordBtn")?.addEventListener("click", () => testNotification("discord"));
byId("testEmailBtn")?.addEventListener("click", () => testNotification("email"));

document.querySelectorAll(".service-tile").forEach((tile) => {
  tile.addEventListener("click", () => {
    const category = tile.dataset.category;
    if (category && byId("ticketCategory")) {
      byId("ticketCategory").value = category;
    }
    setWorkspaceView("submit");
    byId("ticketTitle")?.focus();
  });
});

checkResetPasswordTokenInUrl();
window.addEventListener("hashchange", checkResetPasswordTokenInUrl);

byId("openCreateKnowledgeBtn")?.addEventListener("click", () => openKnowledgeEditor());
byId("toggleUploadKnowledgeBtn")?.addEventListener("click", () => {
  byId("knowledgeUploadForm").classList.toggle("hidden");
});
byId("closeUploadKnowledgeBtn")?.addEventListener("click", () => {
  byId("knowledgeUploadForm").classList.add("hidden");
});
byId("knowledgeUploadForm")?.addEventListener("submit", uploadKnowledge);

document.querySelectorAll(".knowledge-status-tabs .status-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".knowledge-status-tabs .status-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    state.knowledgeStatus = tab.dataset.status || "";
    loadKnowledge();
  });
});
byId("knowledgeSearch")?.addEventListener("input", () => {
  state.knowledgeSearch = byId("knowledgeSearch").value.trim();
  loadKnowledge();
});
byId("knowledgeCategoryFilter")?.addEventListener("change", () => {
  state.knowledgeCategory = byId("knowledgeCategoryFilter").value;
  loadKnowledge();
});

byId("knowledgeEditorForm")?.addEventListener("submit", saveKnowledgeDocument);
byId("cancelKnowledgeEditorBtn")?.addEventListener("click", () => {
  byId("knowledgeEditorModal").classList.add("hidden");
});
byId("editDocContent")?.addEventListener("input", updateLivePreview);

document.querySelectorAll(".editor-toolbar .toolbar-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const textarea = byId("editDocContent");
    const insert = btn.dataset.insert;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    textarea.value = text.slice(0, start) + insert + text.slice(end);
    textarea.focus();
    textarea.selectionStart = textarea.selectionEnd = start + insert.length;
    updateLivePreview();
  });
});

byId("approveKnowledgeDocBtn")?.addEventListener("click", async () => {
  const identifier = byId("editDocIdentifier").value;
  if (!identifier) return;
  try {
    await api(`/knowledge/${encodeURIComponent(identifier)}/review`, {
      method: "POST",
      body: JSON.stringify({ action: "approve" }),
    });
    alertUser("Đã duyệt và xuất bản tài liệu.");
    byId("knowledgeEditorModal").classList.add("hidden");
    await loadKnowledge();
  } catch (err) {
    alertUser(err.message);
  }
});
byId("closeKnowledgeVersionsBtn")?.addEventListener("click", () => {
  byId("knowledgeVersionsModal").classList.add("hidden");
});

byId("ticketForm").addEventListener("submit", submitTicket);
byId("ragForm").addEventListener("submit", askKnowledge);
byId("adminUserForm").addEventListener("submit", createAdminUser);
byId("exportReportBtn").addEventListener("click", exportReport);
byId("newChatBtn").addEventListener("click", () => {
  state.chatSessionId = null;
  byId("ragQuestion").value = "";
  byId("ragResult").replaceChildren();
  byId("ragResult").classList.add("hidden");
  byId("ragQuestion").focus();
});
document.querySelector(".scenario-chips-bar")?.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-question]");
  if (!button) return;
  byId("ragQuestion").value = button.dataset.question;
  byId("ragForm").requestSubmit();
  byId("ragResult")?.scrollIntoView({ behavior: "smooth", block: "start" });
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
  setWorkspaceView("assistant");
  byId("assistantPanel").scrollIntoView({ behavior: "smooth", block: "start" });
  byId("ragQuestion").focus({ preventScroll: true });
  if (question) {
    byId("ragForm").requestSubmit();
  } else {
    setMessage("ticketMessage", "Nhập sự cố ở ô tra cứu phía trên; nếu chưa xử lý được, chuyển nội dung sang yêu cầu IT.", false);
  }
});
byId("clearFiltersBtn").addEventListener("click", () => {
  window.clearTimeout(searchTimer);
  clearTicketFilters();
  loadTickets();
});
byId("queueFilter").addEventListener("change", loadTickets);
byId("statusFilter").addEventListener("change", loadTickets);
byId("categoryFilter").addEventListener("change", loadTickets);
byId("fromDateFilter").addEventListener("change", loadTickets);
byId("toDateFilter").addEventListener("change", loadTickets);
byId("ticketSearch").addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(loadTickets, 250);
});

function parseJwt(token) {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(decodeURIComponent(escape(atob(base64))));
  } catch {
    return null;
  }
}

if (window.location.hash.includes("reset-token")) {
  localStorage.removeItem("helpdesk-token");
  state.token = "";
  state.user = null;
}

if (state.token) {
  const payload = parseJwt(state.token);
  api("/auth/me")
    .then((user) => {
      if (
        window.location.hash.includes("reset-token") ||
        !byId("resetPasswordModal")?.classList.contains("hidden") ||
        !byId("forgotPasswordModal")?.classList.contains("hidden")
      ) {
        signOut();
        return;
      }
      setSignedIn(user);
      if (payload && payload.force_pwd) {
        openChangePasswordModal(true);
      }
    })
    .catch(() => signOut());
}

window.addEventListener("storage", (event) => {
  if (event.key === "helpdesk-token" && !event.newValue) {
    signOut();
  }
});

async function refreshServiceState() {
  const label = byId("serviceStateLabel");
  const textEl = byId("serviceStateText");
  try {
    const response = await fetch("/health", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await response.json();
    const okText = window.helpdeskI18n ? window.helpdeskI18n.translate("Hệ thống sẵn sàng") : "Hệ thống sẵn sàng";
    if (textEl) {
      textEl.textContent = okText;
    } else if (label) {
      label.textContent = okText;
    }
    if (label) {
      label.title = okText;
      label.classList.remove("service-state-error");
      label.classList.add("service-state-ok");
    }
  } catch {
    const errText = window.helpdeskI18n ? window.helpdeskI18n.translate("Dịch vụ đang gián đoạn") : "Dịch vụ đang gián đoạn";
    if (textEl) {
      textEl.textContent = errText;
    } else if (label) {
      label.textContent = errText;
    }
    if (label) {
      label.title = errText;
      label.classList.remove("service-state-ok");
      label.classList.add("service-state-error");
    }
  }
}

refreshServiceState();
window.setInterval(refreshServiceState, 30000);


// Safe markdown parser method is modularized in /static/modules/markdown.js
const renderRunbook = (text) => (window.renderRunbook ? window.renderRunbook(text) : document.createElement("div"));

async function loadAssistantTickets() {
  const list = byId("assistantRecentTickets");
  const username = state.user?.username;
  list.replaceChildren(node("p", "muted", "Đang tải yêu cầu..."));
  try {
    const tickets = await api("/tickets");
    if (state.user?.username !== username) return;
    list.replaceChildren();
    if (!tickets.length) {
      const empty = node("div", "empty-state");
      empty.append(node("strong", "", "Chưa có yêu cầu nào"), node("span", "", "Ticket của bạn sẽ xuất hiện tại đây."));
      list.append(empty);
    }
    tickets.slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 3).forEach((ticket) => {
      const card = node("article", "recent-ticket");
      card.append(node("span", "ticket-id", `HD-${String(ticket.id).padStart(4, "0")}`), node("h3", "", ticket.title), node("span", `tag tag-status-${ticket.status}`, statusLabels[ticket.status] || ticket.status), node("p", "muted", `IT: ${ticket.assignee || "Chưa phân công"}`));
      list.append(card);
    });
  } catch {
    list.replaceChildren(node("p", "muted", "Không tải được ticket. Mở hàng đợi để thử lại."));
  }
}
byId("openTicketsBtn").addEventListener("click", () => setWorkspaceView("tickets"));
