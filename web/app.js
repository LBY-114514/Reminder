const state = {
  issues: [],
  filter: "all",
  editingId: null,
  displayedDueIssueIds: new Set(),
};

const elements = {
  form: document.querySelector("#issueForm"),
  formTitle: document.querySelector("#formTitle"),
  issueId: document.querySelector("#issueId"),
  title: document.querySelector("#title"),
  detail: document.querySelector("#detail"),
  remindAt: document.querySelector("#remindAt"),
  cancelEdit: document.querySelector("#cancelEdit"),
  nextReminder: document.querySelector("#nextReminder"),
  appAlert: document.querySelector("#appAlert"),
  issueList: document.querySelector("#issueList"),
  filterButtons: document.querySelectorAll(".filter-button"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function pad(number) {
  return String(number).padStart(2, "0");
}

function offsetString(date) {
  const offsetMinutes = -date.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const absolute = Math.abs(offsetMinutes);
  return `${sign}${pad(Math.floor(absolute / 60))}:${pad(absolute % 60)}`;
}

function localInputToIsoWithOffset(value) {
  if (!value) {
    return "";
  }

  const [datePart, timePart = "00:00"] = value.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour = 0, minute = 0, second = 0] = timePart.split(":").map(Number);
  const localDate = new Date(year, month - 1, day, hour, minute, second, 0);

  return `${datePart}T${pad(hour)}:${pad(minute)}:${pad(second)}${offsetString(localDate)}`;
}

function isoToLocalInput(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
  ].join("-") + `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "时间无效";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function isDue(issue) {
  const remindTime = new Date(issue.remind_at).getTime();
  return issue.status !== "done" && !Number.isNaN(remindTime) && remindTime <= Date.now();
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("Content-Type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    const message = payload?.error || `请求失败：${response.status}`;
    throw new Error(message);
  }

  return payload;
}

function setAlert(message, type = "info") {
  elements.appAlert.className = "app-alert";
  if (type === "error") {
    elements.appAlert.classList.add("has-error");
  }
  if (type === "due") {
    elements.appAlert.classList.add("has-due");
  }
  elements.appAlert.textContent = message;
}

function renderLoadFailure() {
  elements.nextReminder.textContent = "加载失败";
  elements.issueList.innerHTML = '<div class="empty-state">加载失败，请确认程序是否正常运行。</div>';
}

function renderNextReminder() {
  const pending = state.issues
    .filter((issue) => issue.status !== "done")
    .sort((left, right) => new Date(left.remind_at) - new Date(right.remind_at));

  if (pending.length === 0) {
    elements.nextReminder.innerHTML = "暂无待处理提醒。";
    return;
  }

  const next = pending[0];
  elements.nextReminder.innerHTML = `
    <strong>${escapeHtml(next.title)}</strong><br />
    <span>${escapeHtml(formatDateTime(next.remind_at))}</span>
    ${next.detail ? `<div>${escapeHtml(next.detail)}</div>` : ""}
  `;
}

function filteredIssues() {
  if (state.filter === "all") {
    return state.issues;
  }

  return state.issues.filter((issue) => issue.status === state.filter);
}

function renderIssues() {
  const issues = filteredIssues().sort((left, right) => new Date(left.remind_at) - new Date(right.remind_at));

  if (issues.length === 0) {
    elements.issueList.innerHTML = '<div class="empty-state">当前筛选下暂无问题。</div>';
    return;
  }

  elements.issueList.innerHTML = issues
    .map((issue) => {
      const done = issue.status === "done";
      const due = isDue(issue);
      return `
        <article class="issue-card ${done ? "done" : ""} ${due ? "due" : ""}">
          <div class="issue-top">
            <div>
              <h3 class="issue-title">${escapeHtml(issue.title)}</h3>
              <div class="issue-meta">提醒时间：${escapeHtml(formatDateTime(issue.remind_at))}</div>
            </div>
            <span class="status ${done ? "done" : ""}">${done ? "已处理" : due ? "已到期" : "待处理"}</span>
          </div>
          ${issue.detail ? `<div class="issue-detail">${escapeHtml(issue.detail)}</div>` : ""}
          <div class="card-actions">
            <button type="button" class="card-button" data-action="edit" data-id="${escapeHtml(issue.id)}">编辑</button>
            ${
              done
                ? ""
                : `<button type="button" class="card-button" data-action="done" data-id="${escapeHtml(issue.id)}">标记已处理</button>`
            }
            <button type="button" class="card-button danger-button" data-action="delete" data-id="${escapeHtml(issue.id)}">删除</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function render() {
  renderNextReminder();
  renderIssues();
}

async function loadIssues() {
  try {
    state.issues = await apiRequest("/api/issues");
    render();
  } catch (error) {
    renderLoadFailure();
    setAlert(`加载问题失败：${error.message}`, "error");
  }
}

function resetForm() {
  state.editingId = null;
  elements.form.reset();
  elements.issueId.value = "";
  elements.formTitle.textContent = "新增提醒";
  elements.cancelEdit.hidden = true;
}

async function handleSubmit(event) {
  event.preventDefault();

  const payload = {
    title: elements.title.value.trim(),
    detail: elements.detail.value.trim(),
    remind_at: localInputToIsoWithOffset(elements.remindAt.value),
  };

  const editingId = state.editingId;
  const path = editingId ? `/api/issues/${encodeURIComponent(editingId)}` : "/api/issues";
  const method = editingId ? "PUT" : "POST";

  try {
    await apiRequest(path, {
      method,
      body: JSON.stringify(payload),
    });
    resetForm();
    await loadIssues();
    setAlert("提醒已保存。");
  } catch (error) {
    setAlert(`保存失败：${error.message}`, "error");
  }
}

function startEdit(issue) {
  state.editingId = issue.id;
  elements.issueId.value = issue.id;
  elements.title.value = issue.title || "";
  elements.detail.value = issue.detail || "";
  elements.remindAt.value = isoToLocalInput(issue.remind_at);
  elements.formTitle.textContent = "编辑提醒";
  elements.cancelEdit.hidden = false;
  elements.title.focus();
}

async function handleListClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const { action, id } = button.dataset;
  const issue = state.issues.find((item) => item.id === id);
  if (!issue) {
    setAlert("未找到该问题，请刷新后重试。", "error");
    return;
  }

  if (action === "edit") {
    startEdit(issue);
    return;
  }

  if (action === "delete" && !window.confirm(`确定删除「${issue.title}」吗？`)) {
    return;
  }

  try {
    if (action === "done") {
      await apiRequest(`/api/issues/${encodeURIComponent(id)}/done`, { method: "POST" });
      if (state.editingId === id) {
        resetForm();
      }
      setAlert("已标记为处理完成。");
    }

    if (action === "delete") {
      await apiRequest(`/api/issues/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (state.editingId === id) {
        resetForm();
      }
      setAlert("提醒已删除。");
    }

    await loadIssues();
  } catch (error) {
    setAlert(`操作失败：${error.message}`, "error");
  }
}

function handleFilterClick(event) {
  const button = event.target.closest(".filter-button");
  if (!button) {
    return;
  }

  state.filter = button.dataset.filter;
  elements.filterButtons.forEach((item) => {
    item.classList.toggle("active", item === button);
  });
  renderIssues();
}

async function pollDueReminders() {
  try {
    const dueIssues = await apiRequest("/api/reminders/due");
    const newDueIssues = dueIssues.filter((issue) => !state.displayedDueIssueIds.has(issue.id));
    newDueIssues.forEach((issue) => state.displayedDueIssueIds.add(issue.id));
    if (newDueIssues.length > 0) {
      setAlert(
        `有 ${newDueIssues.length} 条提醒已到期：${newDueIssues.map((issue) => issue.title).join("、")}`,
        "due",
      );
      await loadIssues();
    }
  } catch (error) {
    setAlert(`检查到期提醒失败：${error.message}`, "error");
  }
}

elements.form.addEventListener("submit", handleSubmit);
elements.cancelEdit.addEventListener("click", resetForm);
elements.issueList.addEventListener("click", handleListClick);
document.querySelector(".filters").addEventListener("click", handleFilterClick);

loadIssues().then(pollDueReminders);
window.setInterval(pollDueReminders, 30000);
