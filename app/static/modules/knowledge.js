async function loadKnowledge() {
  try {
    const catEl = byId("knowledgeCategoryFilter");
    if (catEl && typeof catEl.value === "string") {
      state.knowledgeCategory = catEl.value;
    }
    const searchEl = byId("knowledgeSearch");
    if (searchEl && typeof searchEl.value === "string" && !state.knowledgeSearch && searchEl.value.trim()) {
      state.knowledgeSearch = searchEl.value.trim();
    }

    const params = new URLSearchParams();
    if (state.knowledgeStatus) params.set("status", state.knowledgeStatus);
    if (state.knowledgeCategory) params.set("category", state.knowledgeCategory);
    if (state.knowledgeSearch) params.set("search", state.knowledgeSearch);

    const query = params.toString() ? `?${params.toString()}` : "";
    const documents = await api(`/knowledge${query}`);
    state.knowledgeDocs = documents;

    try {
      const allDocs = state.knowledgeStatus === "" ? documents : await api("/knowledge");
      const pendingCount = allDocs.filter((d) => d.status === "pending_review").length;
      const badge = byId("pendingReviewBadge");
      if (badge) {
        badge.textContent = pendingCount;
        badge.classList.toggle("hidden", pendingCount === 0);
      }
    } catch {
      // ignore badge error
    }

    byId("knowledgeCount").textContent = window.helpdeskI18n.translate(`${documents.length} tài liệu`);
    const list = byId("knowledgeList");
    list.replaceChildren();

    if (!documents.length) {
      const empty = node("div", "empty-state");
      empty.append(
        node("strong", "", "Chưa có tài liệu nào"),
        node("span", "", 'Bấm "+ Soạn runbook mới" để tạo bài viết tri thức.')
      );
      list.append(empty);
      return;
    }

    documents.forEach((doc) => {
      const row = node("div", "knowledge-document");
      const main = node("div", "knowledge-doc-main");
      const titleRow = node("div", "knowledge-doc-title-row");

      titleRow.append(node("strong", "", doc.title));

      const statusTag = node("span", `tag tag-status-${doc.status}`, statusLabels[doc.status] || doc.status);
      titleRow.append(statusTag);

      const catTag = node("span", "tag", categoryLabels[doc.category] || doc.category);
      titleRow.append(catTag);

      const verTag = node("span", "tag tag-version", `v${doc.version_count || 1}`);
      titleRow.append(verTag);

      if (doc.is_builtin) {
        titleRow.append(node("span", "tag tag-builtin", "Hệ thống"));
      }

      const metaRow = node("div", "knowledge-doc-meta");
      metaRow.append(node("span", "", `Tệp: ${doc.source || doc.slug}`));
      metaRow.append(node("span", "", `Tác giả: ${doc.author}`));
      if (doc.reviewer && doc.status === "published") {
        metaRow.append(node("span", "", `Duyệt bởi: ${doc.reviewer}`));
      }
      if (doc.updated_at) {
        metaRow.append(node("span", "", `Cập nhật: ${new Date(doc.updated_at).toLocaleDateString(window.helpdeskI18n.locale())}`));
      }
      main.append(titleRow, metaRow);

      if (doc.tags) {
        const tagsRow = node("div", "knowledge-doc-tags");
        tagsRow.append(node("span", "", `Thẻ: ${doc.tags}`));
        main.append(tagsRow);
      }

      row.append(main);

      const actions = node("div", "knowledge-doc-actions");

      const editBtn = node("button", "button button-soft", "Xem hướng dẫn");
      editBtn.type = "button";
      editBtn.addEventListener("click", () => openKnowledgeReader(doc.slug || doc.id, editBtn));
      actions.append(editBtn);

      const versionsBtn = node("button", "button button-quiet", `Lịch sử (v${doc.version_count || 1})`);
      versionsBtn.type = "button";
      versionsBtn.addEventListener("click", () => openKnowledgeVersions(doc.slug || doc.id, doc.title));
      actions.append(versionsBtn);

      if (doc.status === "draft") {
        const submitReviewBtn = node("button", "button button-quiet", "Gửi duyệt");
        submitReviewBtn.type = "button";
        submitReviewBtn.addEventListener("click", async () => {
          try {
            await api(`/knowledge/${encodeURIComponent(doc.slug || doc.id)}`, {
              method: "PUT",
              body: JSON.stringify({ status: "pending_review", change_summary: "Gửi duyệt tài liệu" }),
            });
            await loadKnowledge();
          } catch (err) {
            alertUser(err.message);
          }
        });
        actions.append(submitReviewBtn);
      }

      if (doc.status === "pending_review" && state.user.role === "admin") {
        const approveBtn = node("button", "button button-primary", "✓ Duyệt & Xuất bản");
        approveBtn.type = "button";
        approveBtn.addEventListener("click", async () => {
          try {
            await api(`/knowledge/${encodeURIComponent(doc.slug || doc.id)}/review`, {
              method: "POST",
              body: JSON.stringify({ action: "approve" }),
            });
            await loadKnowledge();
          } catch (err) {
            alertUser(err.message);
          }
        });
        actions.append(approveBtn);

        const rejectBtn = node("button", "button button-quiet", "✕ Trả về nháp");
        rejectBtn.type = "button";
        rejectBtn.addEventListener("click", async () => {
          try {
            await api(`/knowledge/${encodeURIComponent(doc.slug || doc.id)}/review`, {
              method: "POST",
              body: JSON.stringify({ action: "reject" }),
            });
            await loadKnowledge();
          } catch (err) {
            alertUser(err.message);
          }
        });
        actions.append(rejectBtn);
      }

      if (state.user.role === "admin") {
        const reindex = node("button", "button button-quiet", "Cập nhật chỉ mục");
        reindex.type = "button";
        reindex.addEventListener("click", async () => {
          try {
            await api(`/knowledge/${encodeURIComponent(doc.source || doc.slug)}/reindex`, { method: "POST" });
            alertUser("Đã cập nhật chỉ mục tìm kiếm BM25.");
            await loadKnowledge();
          } catch (error) {
            alertUser(error.message);
          }
        });
        actions.append(reindex);

        if (!doc.is_builtin) {
          const remove = node("button", "button button-quiet", "Xóa");
          remove.type = "button";
          remove.addEventListener("click", async () => {
            if (!window.confirm(window.helpdeskI18n.translate(`Xóa tài liệu ${doc.source || doc.slug} khỏi thư viện?`))) return;
            try {
              await api(`/knowledge/${encodeURIComponent(doc.source || doc.slug)}`, { method: "DELETE" });
              await loadKnowledge();
            } catch (error) {
              alertUser(error.message);
            }
          });
          actions.append(remove);
        }
      }

      row.append(actions);
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
    setMessage("knowledgeMessage", "Đã thêm tài liệu vào Kho tri thức.", false);
    byId("knowledgeUploadForm").classList.add("hidden");
    await loadKnowledge();
  } catch (error) {
    setMessage("knowledgeMessage", error.message);
  }
}

function updateLivePreview() {
  const content = byId("editDocContent").value;
  const preview = byId("editDocPreview");
  if (!content.trim()) {
    preview.replaceChildren(node("p", "muted", "Nhập nội dung ở khung bên trái để xem trước tại đây..."));
    return;
  }
  preview.replaceChildren(renderRunbook(content));
}

async function openKnowledgeReader(identifier, trigger) {
  try {
    const doc = await api(`/knowledge/${encodeURIComponent(identifier)}`);
    const modal = byId("knowledgeReaderModal");
    byId("knowledgeReaderTitle").textContent = doc.title;
    byId("knowledgeReaderMeta").textContent = `${categoryLabels[doc.category] || doc.category} · ${statusLabels[doc.status] || doc.status}`;
    byId("knowledgeReaderContent").replaceChildren(renderRunbook(doc.content));
    const close = () => { modal.classList.add("hidden"); trigger?.focus(); };
    byId("closeKnowledgeReader").onclick = close;
    byId("editKnowledgeReader").classList.toggle("hidden", state.user.role === "user");
    byId("editKnowledgeReader").onclick = () => { close(); openKnowledgeEditor(identifier); };
    modal.onclick = (event) => { if (event.target === modal) close(); };
    modal.onkeydown = (event) => {
      if (event.key === "Escape") { event.stopPropagation(); close(); }
      if (event.key === "Tab") {
        const controls = [...modal.querySelectorAll("button:not(.hidden)")];
        const first = controls[0], last = controls[controls.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === byId("knowledgeReaderTitle"))) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    modal.classList.remove("hidden");
    byId("knowledgeReaderTitle").focus();
  } catch (error) { alertUser(error.message); }
}

async function openKnowledgeEditor(identifier) {
  const modal = byId("knowledgeEditorModal");
  const form = byId("knowledgeEditorForm");
  form.reset();
  setMessage("knowledgeEditorMessage", "");

  const titleEl = byId("knowledgeEditorTitle");
  const idInput = byId("editDocIdentifier");
  const changeSummaryRow = byId("changeSummaryRow");
  const approveBtn = byId("approveKnowledgeDocBtn");
  const statusBadge = byId("editorStatusBadge");

  byId("statusOptionPublished").classList.toggle("hidden", state.user.role !== "admin");

  if (identifier) {
    try {
      const doc = await api(`/knowledge/${encodeURIComponent(identifier)}`);
      idInput.value = doc.slug || doc.id;
      byId("editDocTitle").value = doc.title;
      byId("editDocCategory").value = doc.category;
      byId("editDocTags").value = doc.tags || "";
      byId("editDocStatus").value = doc.status;
      byId("editDocContent").value = doc.content;
      byId("editDocChangeSummary").value = "";
      changeSummaryRow.classList.remove("hidden");

      titleEl.textContent = `Chỉnh sửa: ${doc.title}`;
      statusBadge.className = `tag tag-status-${doc.status}`;
      statusBadge.textContent = statusLabels[doc.status] || doc.status;

      approveBtn.classList.toggle("hidden", !(state.user.role === "admin" && doc.status === "pending_review"));
      updateLivePreview();
    } catch (err) {
      alertUser(err.message);
      return;
    }
  } else {
    idInput.value = "";
    byId("editDocTitle").value = "";
    byId("editDocCategory").value = "general";
    byId("editDocTags").value = "";
    byId("editDocStatus").value = "draft";
    byId("editDocContent").value =
      "# Tiêu đề Runbook\n\n## 1. Mô tả sự cố\n...\n\n## 2. Các bước xử lý\n- Bước 1: ...\n- Bước 2: ...\n\n## 3. Kiểm tra kết quả\n...";
    byId("editDocChangeSummary").value = "";
    changeSummaryRow.classList.add("hidden");
    approveBtn.classList.add("hidden");

    titleEl.textContent = "Soạn thảo Runbook mới";
    statusBadge.className = "tag tag-status-draft";
    statusBadge.textContent = "Bản nháp";
    updateLivePreview();
  }

  modal.classList.remove("hidden");
  byId("editDocTitle").focus();
}

async function saveKnowledgeDocument(event) {
  event.preventDefault();
  const idInput = byId("editDocIdentifier").value;
  const title = byId("editDocTitle").value.trim();
  const category = byId("editDocCategory").value;
  const tags = byId("editDocTags").value.trim();
  const status = byId("editDocStatus").value;
  const content = byId("editDocContent").value.trim();
  const changeSummary = byId("editDocChangeSummary").value.trim();

  setMessage("knowledgeEditorMessage", "Đang lưu tài liệu...", false);
  try {
    if (idInput) {
      await api(`/knowledge/${encodeURIComponent(idInput)}`, {
        method: "PUT",
        body: JSON.stringify({
          title,
          category,
          tags,
          status,
          content,
          change_summary: changeSummary || "Cập nhật nội dung",
        }),
      });
      setMessage("knowledgeEditorMessage", "Đã lưu cập nhật thành công.", false);
    } else {
      await api("/knowledge", {
        method: "POST",
        body: JSON.stringify({
          title,
          category,
          tags,
          status,
          content,
        }),
      });
      setMessage("knowledgeEditorMessage", "Đã tạo tài liệu thành công.", false);
    }
    setTimeout(() => {
      byId("knowledgeEditorModal").classList.add("hidden");
      loadKnowledge();
    }, 600);
  } catch (err) {
    setMessage("knowledgeEditorMessage", err.message);
  }
}

async function openKnowledgeVersions(identifier, title) {
  const modal = byId("knowledgeVersionsModal");
  byId("knowledgeVersionsTitle").textContent = `Lịch sử phiên bản: ${title || identifier}`;
  const list = byId("knowledgeVersionsList");
  list.replaceChildren(node("span", "muted", "Đang tải lịch sử phiên bản..."));
  modal.classList.remove("hidden");

  try {
    const versions = await api(`/knowledge/${encodeURIComponent(identifier)}/versions`);
    list.replaceChildren();
    if (!versions.length) {
      list.append(node("p", "muted", "Không tìm thấy phiên bản nào."));
      return;
    }

    versions.forEach((ver) => {
      const card = node("div", "version-card");
      const main = node("div", "version-card-main");

      const header = node("div", "version-card-header");
      header.append(
        node("span", "tag tag-version", `v${ver.version_number}`),
        node("strong", "", ver.title),
        node("span", "tag", categoryLabels[ver.category] || ver.category)
      );

      const summary = node("div", "version-summary", `Thay đổi: ${ver.change_summary || "Không có tóm tắt"}`);
      const meta = node(
        "div",
        "version-meta",
        `Tác giả: ${ver.author} · ${new Date(ver.created_at).toLocaleString(window.helpdeskI18n.locale())}`
      );

      main.append(header, summary, meta);

      const contentDetails = node("details", "version-content-details");
      contentDetails.append(node("summary", "", "Xem nội dung phiên bản này"));
      contentDetails.append(renderRunbook(ver.content));
      main.append(contentDetails);

      card.append(main);

      if (state.user.role === "admin") {
        const restoreBtn = node("button", "button button-soft", "Khôi phục phiên bản này");
        restoreBtn.type = "button";
        restoreBtn.addEventListener("click", async () => {
          if (!window.confirm(window.helpdeskI18n.translate(`Bạn có chắc muốn khôi phục về phiên bản #${ver.version_number}?`))) return;
          try {
            await api(`/knowledge/${encodeURIComponent(identifier)}/restore/${ver.version_number}`, { method: "POST" });
            alertUser(`Đã khôi phục về phiên bản #${ver.version_number}.`);
            modal.classList.add("hidden");
            await loadKnowledge();
          } catch (err) {
            alertUser(err.message);
          }
        });
        card.append(restoreBtn);
      }

      list.append(card);
    });
  } catch (err) {
    list.replaceChildren(node("span", "muted", err.message));
  }
}

function openKnowledgeEditorForTicket(ticket) {
  openKnowledgeEditor();
  byId("editDocTitle").value = `Xử lý sự cố: ${ticket.title}`;
  byId("editDocCategory").value = ticket.category;
  byId("editDocTags").value = `${ticket.category}, ticket-${ticket.id}`;
  byId("editDocStatus").value = "draft";

  const commentsText = (ticket.comments || [])
    .map((c) => `- ${c.author}: ${c.comment}`)
    .join("\n");

  byId("editDocContent").value = `# Xử lý sự cố: ${ticket.title}\n\n## 1. Mô tả sự cố\n${ticket.description}\n\n## 2. Quá trình xử lý (tham chiếu Ticket HD-${String(ticket.id).padStart(4, "0")})\n${commentsText || "- Các bước giải quyết đã xác nhận thành công."}\n\n## 3. Hướng dẫn khắc phục nhanh\n1. Kiểm tra nguyên nhân gốc rễ.\n2. Thực hiện cấu hình hoặc khắc phục sự cố.\n3. Xác minh người dùng hoạt động bình thường.\n\n## 4. Biện pháp phòng ngừa\n- Lưu ý định kỳ cập nhật thông tin và kiểm tra thiết bị.`;

  updateLivePreview();
}

if (typeof window !== "undefined") {
  window.loadKnowledge = loadKnowledge;
  window.uploadKnowledge = uploadKnowledge;
  window.updateLivePreview = updateLivePreview;
  window.openKnowledgeEditor = openKnowledgeEditor;
  window.saveKnowledgeDocument = saveKnowledgeDocument;
  window.openKnowledgeVersions = openKnowledgeVersions;
  window.openKnowledgeEditorForTicket = openKnowledgeEditorForTicket;
}
