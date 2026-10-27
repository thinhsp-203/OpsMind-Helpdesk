// Keep implementation names private; expose only the existing window API.
(() => {
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
        node(
          "span",
          "",
          `${user.username} · ${user.email || "Chưa có email"} · ${user.department || "Chưa có phòng ban"}`
        )
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
      const resetDetails = document.createElement("details");
      resetDetails.className = "admin-profile-details";
      resetDetails.append(node("summary", "", "Đặt lại MK"));
      const resetForm = document.createElement("form");
      resetForm.className = "admin-profile-form";
      resetForm.dataset.username = user.username;

      const resetInput = document.createElement("input");
      resetInput.type = "password";
      resetInput.name = "new_password";
      resetInput.placeholder = window.helpdeskI18n.translate("Mật khẩu mới (tối thiểu 12 ký tự)");
      resetInput.required = true;
      resetInput.minLength = 12;
      resetInput.maxLength = 200;
      resetInput.setAttribute("aria-label", `Mật khẩu mới ${user.username}`);

      const forceLabel = document.createElement("label");
      const forceCheckbox = document.createElement("input");
      forceCheckbox.type = "checkbox";
      forceCheckbox.name = "force_password_change";
      forceCheckbox.checked = true;
      forceLabel.append(forceCheckbox, node("span", "", "Buộc đổi khi đăng nhập"));

      const resetBtn = node("button", "button button-soft", "Lưu mật khẩu");
      resetBtn.type = "submit";

      const generateLinkBtn = node("button", "button button-quiet", "Tạo mã khôi phục (IT cấp mã)");
      generateLinkBtn.type = "button";
      generateLinkBtn.style.marginTop = "4px";
      generateLinkBtn.addEventListener("click", async () => {
        try {
          const res = await api(`/admin/users/${encodeURIComponent(user.username)}/create-reset-token`, {
            method: "POST",
          });
          const info = `Liên kết đặt lại mật khẩu cho ${user.username} (hiệu lực ${res.expires_minutes} phút):\n\n${res.reset_link}\n\nMã token: ${res.token}`;
          if (navigator.clipboard && navigator.clipboard.writeText) {
            try {
              await navigator.clipboard.writeText(res.reset_link);
              alertUser(`${info}\n\n(Đã sao chép liên kết vào clipboard)`);
              return;
            } catch {
              // fallback to alert
            }
          }
          alertUser(info);
        } catch (error) {
          alertUser(error.message);
        }
      });

      resetForm.append(resetInput, forceLabel, resetBtn, generateLinkBtn);
      resetForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
          const res = await api(`/admin/users/${encodeURIComponent(user.username)}/reset-password`, {
            method: "POST",
            body: JSON.stringify({
              new_password: resetInput.value,
              force_change: forceCheckbox.checked,
            }),
          });
          const isSelf = (user.username || "").toLowerCase() === (state.user?.username || "").toLowerCase();
          if (isSelf) {
            alertUser("Đổi mật khẩu tài khoản hiện tại thành công. Vui lòng đăng nhập lại.");
            signOut();
            if (byId("username")) {
              byId("username").value = user.username;
            }
            if (byId("password")) {
              byId("password").value = "";
              byId("password").focus();
            }
            setMessage("loginMessage", "Đổi mật khẩu thành công. Vui lòng đăng nhập lại với mật khẩu mới.", false);
            return;
          }
          alertUser(res?.message || "Đổi mật khẩu thành công.");
          resetForm.reset();
          forceCheckbox.checked = true;
          resetDetails.removeAttribute("open");
        } catch (error) {
          alertUser(error.message);
        }
      });
      resetDetails.append(resetForm);

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
        user.is_active ? "Khóa" : "Mở khóa"
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
      if (user.username !== state.user?.username) {
        const deleteButton = node("button", "button button-quiet", "Xóa vĩnh viễn");
        deleteButton.type = "button";
        deleteButton.addEventListener("click", async () => {
          const confirmation = window.prompt(`Xóa vĩnh viễn ${user.username}? Thông tin đăng nhập, hồ sơ và hội thoại riêng sẽ bị xóa. Ticket/bình luận vẫn giữ với danh tính ẩn danh; nội dung do người dùng viết vẫn còn. Nhập chính xác tên tài khoản để xác nhận:`);
          if (confirmation !== user.username) return;
          deleteButton.disabled = true;
          try {
            const response = await api(`/admin/users/${encodeURIComponent(user.username)}`, {
              method: "DELETE", body: JSON.stringify({confirm_username: confirmation}),
            });
            await loadAdminUsers();
            state.staff = await api("/staff");
            await loadTickets();
            alertUser(response.message);
          } catch (error) {
            alertUser(error.message);
          } finally {
            deleteButton.disabled = false;
          }
        });
        actions.append(deleteButton);
      }
      row.append(
        identity,
        profileDetails,
        resetDetails,
        node("span", "", user.is_active ? "Hoạt động" : "Đã khóa"),
        actions
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

if (typeof window !== "undefined") {
  window.loadAdminUsers = loadAdminUsers;
  window.createAdminUser = createAdminUser;
}
})();
