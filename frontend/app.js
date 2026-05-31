const app = document.querySelector("#app");

const localApiBase = localStorage.getItem("scs_api_base");
const configuredApiBase = window.SCS_API_BASE || "";
const defaultApiBase = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:8000"
  : window.location.origin;

const state = {
  apiBase: (localApiBase || configuredApiBase || defaultApiBase).replace(/\/+$/, ""),
  token: localStorage.getItem("scs_token") || "",
  user: null,
  authMode: "login",
  activeTab: "files",
  myFiles: [],
  sharedFiles: [],
  adminUsers: [],
  adminFiles: [],
  adminLogs: [],
  metadata: null,
  lastShare: null,
  lastLink: null,
  notice: null,
  loading: false,
};

const tabs = [
  { id: "files", label: "My Files" },
  { id: "shared", label: "Shared With Me" },
  { id: "share", label: "Share" },
  { id: "links", label: "Expiring Link" },
  { id: "admin", label: "Admin" },
];

const fileFields = [
  ["id", "ID"],
  ["owner_id", "Owner ID"],
  ["original_filename", "File"],
  ["blob_path", "Blob Path"],
  ["size", "Size"],
  ["content_type", "Type"],
  ["uploaded_at", "Uploaded"],
  ["status", "Status"],
];

const friendlyErrors = {
  "Active file share not found": "No active share was found for that user.",
  "Azure Blob upload failed": "File upload could not reach Azure Blob Storage. Please try again.",
  "Could not validate credentials": "Your session could not be verified. Please log in again.",
  "File is already shared with this user": "This file is already shared with that user.",
  "Invalid email or password": "Invalid email or password.",
  "Invalid file type": "This file type is not allowed.",
  "Not Authorized": "You do not have permission to access this file.",
  "Payload too large": "The selected file is larger than the 10 MB limit.",
  "Share link expired": "This download link has expired.",
  "Token expired": "Your session has expired. Please log in again.",
  "Too many requests": "Too many attempts. Please wait a moment and try again.",
  "User already registered": "This email is already registered.",
  "User not found": "No user was found with that email address.",
};

function friendlyMessage(message) {
  return friendlyErrors[message] || message;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("tr-TR");
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function setNotice(type, text) {
  state.notice = { type, text };
  render();
  window.clearTimeout(setNotice.timer);
  setNotice.timer = window.setTimeout(() => {
    state.notice = null;
    render();
  }, 5000);
}

function saveApiBase(value) {
  state.apiBase = value.replace(/\/+$/, "");
  localStorage.setItem("scs_api_base", state.apiBase);
}

function saveToken(token) {
  state.token = token;
  localStorage.setItem("scs_token", token);
}

function clearSession() {
  state.token = "";
  state.user = null;
  state.myFiles = [];
  state.sharedFiles = [];
  state.adminUsers = [];
  state.adminFiles = [];
  state.adminLogs = [];
  state.metadata = null;
  state.lastShare = null;
  state.lastLink = null;
  localStorage.removeItem("scs_token");
}

function getErrorMessage(payload) {
  if (!payload) return "Request failed. Please try again.";
  if (typeof payload === "string") return friendlyMessage(payload);
  if (typeof payload.detail === "string") return friendlyMessage(payload.detail);
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => friendlyMessage(item.msg || JSON.stringify(item))).join(", ");
  }
  return JSON.stringify(payload);
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
  if (options.json) headers.set("Content-Type", "application/json");

  const response = await fetch(`${state.apiBase}${path}`, {
    ...options,
    headers,
    body: options.json ? JSON.stringify(options.json) : options.body,
  });

  if (!response.ok) {
    let payload = null;
    const text = await response.text();
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      payload = text;
    }
    const message = getErrorMessage(payload);
    if (response.status === 401 && state.token) {
      clearSession();
      throw new Error("Your session has expired. Please log in again.");
    }
    throw new Error(message);
  }

  if (options.responseType === "blob") {
    return {
      blob: await response.blob(),
      filename: getDownloadFilename(response.headers.get("Content-Disposition")),
    };
  }

  if (response.status === 204) return null;
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

function getDownloadFilename(header) {
  if (!header) return "download";
  const utfMatch = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch) return decodeURIComponent(utfMatch[1]);
  const plainMatch = header.match(/filename="?([^"]+)"?/i);
  return plainMatch ? plainMatch[1] : "download";
}

async function withLoading(task) {
  state.loading = true;
  render();
  try {
    await task();
  } catch (error) {
    setNotice("error", error.message);
  } finally {
    state.loading = false;
    render();
  }
}

async function bootstrap() {
  if (!state.token) {
    render();
    return;
  }

  await withLoading(async () => {
    await loadCurrentUser();
    await refreshWorkspace();
  });
}

async function loadCurrentUser() {
  state.user = await apiFetch("/users/me");
}

async function refreshWorkspace() {
  state.myFiles = await apiFetch("/files/my-files");
  state.sharedFiles = await apiFetch("/files/shared-with-me");
  if (state.user?.role === "admin") {
    state.adminUsers = await apiFetch("/admin/users");
    state.adminFiles = await apiFetch("/admin/files");
    state.adminLogs = await apiFetch("/admin/logs");
  }
}

async function login(email, password) {
  const token = await apiFetch("/auth/login", {
    method: "POST",
    json: { email, password },
  });
  saveToken(token.access_token);
  await loadCurrentUser();
  await refreshWorkspace();
}

async function register(email, password) {
  await apiFetch("/auth/register", {
    method: "POST",
    json: { email, password },
  });
  await login(email, password);
}

async function uploadFile(file) {
  const data = new FormData();
  data.append("file", file);
  await apiFetch("/files/upload", {
    method: "POST",
    body: data,
  });
  await refreshWorkspace();
  setNotice("success", "File uploaded successfully.");
}

async function downloadFile(fileId, tokenPath = null) {
  const path = tokenPath || `/files/${fileId}/download`;
  const result = await apiFetch(path, { responseType: "blob" });
  const url = URL.createObjectURL(result.blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = result.filename || "download";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function loadMetadata(fileId) {
  state.metadata = await apiFetch(`/files/${fileId}`);
  setNotice("info", "File metadata loaded.");
}

async function shareFile(fileId, email) {
  state.lastShare = await apiFetch(`/files/${fileId}/share`, {
    method: "POST",
    json: {
      shared_with_email: email,
      permission_type: "read",
    },
  });
  setNotice("success", "File shared successfully.");
}

async function revokeShare(fileId, email) {
  await apiFetch(`/files/${fileId}/share`, {
    method: "DELETE",
    json: {
      shared_with_email: email,
    },
  });
  state.lastShare = null;
  setNotice("success", "File share revoked.");
}

async function createLink(fileId, minutes) {
  state.lastLink = await apiFetch(`/files/${fileId}/share-link`, {
    method: "POST",
    json: {
      expires_in_minutes: Number(minutes),
    },
  });
  setNotice("success", "Download link created.");
}

function render() {
  if (!state.token || !state.user) {
    app.innerHTML = renderAuth();
    return;
  }

  app.innerHTML = `
    <div class="app-shell">
      <header class="topbar">
        <h1>Secure Cloud Storage</h1>
        <div class="topbar-meta">
          <span>${escapeHtml(state.user.email)}</span>
          <span class="role-pill">${escapeHtml(state.user.role)}</span>
          <button class="secondary" data-action="refresh">Refresh</button>
          <button class="secondary" data-action="logout">Logout</button>
        </div>
      </header>
      <div class="layout">
        <aside class="sidebar">
          <nav class="nav-list">
            ${tabs
              .filter((tab) => tab.id !== "admin" || state.user.role === "admin")
              .map((tab) => `
                <button class="tab-button ${state.activeTab === tab.id ? "active" : ""}" data-tab="${tab.id}">
                  ${tab.label}
                </button>
              `)
              .join("")}
          </nav>
        </aside>
        <main class="content">
          ${state.metadata ? renderMetadata(state.metadata) : ""}
          ${renderActiveTab()}
        </main>
      </div>
      ${renderNotice()}
    </div>
  `;
}

function renderAuth() {
  const isLogin = state.authMode === "login";
  return `
    <main class="auth-shell">
      <section class="auth-panel">
        <div class="brand-block">
          <div>
            <h1>Secure Cloud Storage</h1>
            <p>Encrypted upload, controlled sharing, expiring links, and audit logs in one secure workspace.</p>
          </div>
          <div class="muted">API: ${escapeHtml(state.apiBase)}</div>
        </div>
        <div class="auth-box">
          <div class="auth-tabs">
            <button class="${isLogin ? "active" : ""}" data-auth-mode="login">Login</button>
            <button class="${!isLogin ? "active" : ""}" data-auth-mode="register">Register</button>
          </div>
          <form class="form-grid" data-form="auth">
            <label>
              API URL
              <input name="apiBase" value="${escapeHtml(state.apiBase)}" autocomplete="url">
            </label>
            <label>
              Email
              <input name="email" type="email" required autocomplete="email">
            </label>
            <label>
              Password
              <input name="password" type="password" required autocomplete="${isLogin ? "current-password" : "new-password"}">
            </label>
            <button type="submit" ${state.loading ? "disabled" : ""}>${isLogin ? "Login" : "Register"}</button>
          </form>
          ${renderNotice()}
        </div>
      </section>
    </main>
  `;
}

function renderActiveTab() {
  if (state.activeTab === "shared") return renderSharedFiles();
  if (state.activeTab === "share") return renderShareTools();
  if (state.activeTab === "links") return renderLinkTools();
  if (state.activeTab === "admin") return renderAdmin();
  return renderMyFiles();
}

function renderMyFiles() {
  return `
    <section class="section-head">
      <h2>My Files</h2>
      <span class="muted">${state.myFiles.length} records</span>
    </section>
    <section class="panel">
      <h3>Upload</h3>
      <form class="toolbar" data-form="upload">
        <label>
          File
          <input type="file" name="file" required>
        </label>
        <button type="submit" ${state.loading ? "disabled" : ""}>${state.loading ? "Uploading..." : "Upload"}</button>
      </form>
    </section>
    <section class="panel">
      ${renderFileTable(state.myFiles, "owned")}
    </section>
  `;
}

function renderSharedFiles() {
  return `
    <section class="section-head">
      <h2>Shared With Me</h2>
      <span class="muted">${state.sharedFiles.length} records</span>
    </section>
    <section class="panel">
      ${renderFileTable(state.sharedFiles, "shared")}
    </section>
  `;
}

function renderShareTools() {
  return `
    <section class="section-head">
      <h2>Share</h2>
    </section>
    <section class="panel">
      <h3>Share File</h3>
      <form class="toolbar" data-form="share">
        ${renderFileSelect("fileId")}
        <label>
          User Email
          <input name="email" type="email" required placeholder="user2@example.com">
        </label>
        <button type="submit" ${state.loading || !state.myFiles.length ? "disabled" : ""}>Share</button>
      </form>
      ${state.lastShare ? renderShareResult(state.lastShare) : ""}
    </section>
    <section class="panel">
      <h3>Revoke Access</h3>
      <form class="toolbar" data-form="revoke">
        ${renderFileSelect("fileId")}
        <label>
          User Email
          <input name="email" type="email" required placeholder="user2@example.com">
        </label>
        <button class="danger" type="submit" ${state.loading || !state.myFiles.length ? "disabled" : ""}>Revoke</button>
      </form>
    </section>
  `;
}

function renderLinkTools() {
  const linkUrl = state.lastLink ? `${window.location.origin}/#share/${state.lastLink.token}` : "";
  const directApiUrl = state.lastLink ? `${state.apiBase}/share/${state.lastLink.token}/download` : "";
  return `
    <section class="section-head">
      <h2>Expiring Link</h2>
    </section>
    <section class="panel">
      <h3>Create Link</h3>
      <form class="toolbar" data-form="link">
        ${renderFileSelect("fileId")}
        <label>
          Minutes
          <input name="minutes" type="number" min="1" max="10080" value="60" required>
        </label>
        <button type="submit" ${state.loading || !state.myFiles.length ? "disabled" : ""}>Create</button>
      </form>
      ${
        state.lastLink
          ? `
            <div class="link-output">
              <div class="details-grid">
                <div class="detail-item">
                  <div class="detail-label">Token</div>
                  <div class="detail-value">${escapeHtml(state.lastLink.token)}</div>
                </div>
                <div class="detail-item">
                  <div class="detail-label">Expires</div>
                  <div class="detail-value">${formatDate(state.lastLink.expires_at)}</div>
                </div>
              </div>
              <div class="copy-row">
                <input readonly value="${escapeHtml(linkUrl)}">
                <button class="secondary" data-action="copy" data-copy="${escapeHtml(linkUrl)}">Copy</button>
              </div>
              <a href="${escapeHtml(directApiUrl)}" target="_blank" rel="noreferrer">${escapeHtml(directApiUrl)}</a>
            </div>
          `
          : ""
      }
    </section>
  `;
}

function renderAdmin() {
  return `
    <section class="section-head">
      <h2>Admin Panel</h2>
      <button class="secondary" data-action="refresh-admin">Refresh</button>
    </section>
    <section class="panel">
      <h3>Users</h3>
      ${renderUsersTable(state.adminUsers)}
    </section>
    <section class="panel">
      <h3>All Files</h3>
      ${renderFileTable(state.adminFiles, "admin")}
    </section>
    <section class="panel">
      <h3>Access Logs</h3>
      ${renderLogsTable(state.adminLogs)}
    </section>
  `;
}

function renderFileSelect(name) {
  return `
    <label>
      File
      <select name="${name}" required ${!state.myFiles.length ? "disabled" : ""}>
        ${state.myFiles
          .map((file) => `
            <option value="${file.id}">#${file.id} ${escapeHtml(file.original_filename)}</option>
          `)
          .join("")}
      </select>
    </label>
  `;
}

function renderShareResult(share) {
  return `
    <div class="message success">
      File ID ${escapeHtml(share.file_id)} -> User ID ${escapeHtml(share.shared_with_user_id)} (${escapeHtml(share.permission_type)})
    </div>
  `;
}

function renderFileTable(files, mode) {
  if (!files.length) return `<div class="empty">No records yet</div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>File</th>
            <th>Size</th>
            <th>Type</th>
            <th>Status</th>
            <th>Date</th>
            <th class="nowrap">Action</th>
          </tr>
        </thead>
        <tbody>
          ${files
            .map((file) => `
              <tr>
                <td>${escapeHtml(file.id)}</td>
                <td>${escapeHtml(file.original_filename)}</td>
                <td>${formatBytes(file.size)}</td>
                <td>${escapeHtml(file.content_type || "-")}</td>
                <td>${escapeHtml(file.status)}</td>
                <td>${formatDate(file.uploaded_at)}</td>
                <td>
                  <div class="actions">
                    <button class="secondary" data-action="download" data-file-id="${file.id}">Download</button>
                    ${
                      mode !== "shared"
                        ? `<button class="secondary" data-action="metadata" data-file-id="${file.id}">Metadata</button>`
                        : ""
                    }
                  </div>
                </td>
              </tr>
            `)
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderUsersTable(users) {
  if (!users.length) return `<div class="empty">No records yet</div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Email</th>
            <th>Role</th>
            <th>Active</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          ${users
            .map((user) => `
              <tr>
                <td>${escapeHtml(user.id)}</td>
                <td>${escapeHtml(user.email)}</td>
                <td>${escapeHtml(user.role)}</td>
                <td>${user.is_active ? "Yes" : "No"}</td>
                <td>${formatDate(user.created_at)}</td>
              </tr>
            `)
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderLogsTable(logs) {
  if (!logs.length) return `<div class="empty">No records yet</div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>User</th>
            <th>File</th>
            <th>Action</th>
            <th>Status</th>
            <th>IP</th>
            <th>Details</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          ${logs
            .map((log) => `
              <tr>
                <td>${escapeHtml(log.id)}</td>
                <td>${escapeHtml(log.user_id ?? "-")}</td>
                <td>${escapeHtml(log.file_id ?? "-")}</td>
                <td>${escapeHtml(log.action)}</td>
                <td>${escapeHtml(log.status)}</td>
                <td>${escapeHtml(log.ip_address || "-")}</td>
                <td>${escapeHtml(log.details || "-")}</td>
                <td>${formatDate(log.timestamp)}</td>
              </tr>
            `)
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderMetadata(file) {
  return `
    <section class="panel">
      <div class="section-head">
        <h3>Metadata</h3>
        <button class="secondary" data-action="clear-metadata">Close</button>
      </div>
      <div class="details-grid">
        ${fileFields
          .map(([key, label]) => `
            <div class="detail-item">
              <div class="detail-label">${label}</div>
              <div class="detail-value">${key === "size" ? formatBytes(file[key]) : escapeHtml(key.endsWith("_at") ? formatDate(file[key]) : file[key])}</div>
            </div>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function renderNotice() {
  if (!state.notice) return "";
  return `
    <div class="status-bar">
      <div class="message ${state.notice.type}">
        ${escapeHtml(state.notice.text)}
      </div>
    </div>
  `;
}

document.addEventListener("click", (event) => {
  const tabButton = event.target.closest("[data-tab]");
  if (tabButton) {
    state.activeTab = tabButton.dataset.tab;
    state.metadata = null;
    render();
    return;
  }

  const authMode = event.target.closest("[data-auth-mode]");
  if (authMode) {
    state.authMode = authMode.dataset.authMode;
    render();
    return;
  }

  const actionButton = event.target.closest("[data-action]");
  if (!actionButton) return;

  const action = actionButton.dataset.action;
  if (action === "logout") {
    clearSession();
    render();
    return;
  }
  if (action === "refresh") {
    withLoading(async () => {
      await refreshWorkspace();
      setNotice("success", "Workspace refreshed.");
    });
    return;
  }
  if (action === "refresh-admin") {
    withLoading(async () => {
      state.adminUsers = await apiFetch("/admin/users");
      state.adminFiles = await apiFetch("/admin/files");
      state.adminLogs = await apiFetch("/admin/logs");
      setNotice("success", "Admin data refreshed.");
    });
    return;
  }
  if (action === "download") {
    withLoading(async () => {
      await downloadFile(actionButton.dataset.fileId);
      setNotice("success", "Download started.");
    });
    return;
  }
  if (action === "metadata") {
    withLoading(async () => loadMetadata(actionButton.dataset.fileId));
    return;
  }
  if (action === "clear-metadata") {
    state.metadata = null;
    render();
    return;
  }
  if (action === "copy") {
    navigator.clipboard.writeText(actionButton.dataset.copy || "");
    setNotice("success", "Link copied.");
  }
});

document.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-form]");
  if (!form) return;
  event.preventDefault();

  const data = new FormData(form);
  const formType = form.dataset.form;

  if (formType === "auth") {
    withLoading(async () => {
      saveApiBase(data.get("apiBase"));
      const email = data.get("email");
      const password = data.get("password");
      if (state.authMode === "register") {
        await register(email, password);
      } else {
        await login(email, password);
      }
      setNotice("success", "Signed in successfully.");
    });
    return;
  }

  if (formType === "upload") {
    const file = data.get("file");
    if (!file || !file.size) {
      setNotice("error", "Please select a file first.");
      return;
    }
    withLoading(async () => uploadFile(file));
    return;
  }

  if (formType === "share") {
    withLoading(async () => {
      await shareFile(data.get("fileId"), data.get("email"));
      await refreshWorkspace();
    });
    return;
  }

  if (formType === "revoke") {
    withLoading(async () => {
      await revokeShare(data.get("fileId"), data.get("email"));
      await refreshWorkspace();
    });
    return;
  }

  if (formType === "link") {
    withLoading(async () => createLink(data.get("fileId"), data.get("minutes")));
  }
});

window.addEventListener("hashchange", () => {
  handleShareHash();
});

async function handleShareHash() {
  const match = window.location.hash.match(/^#share\/(.+)/);
  if (!match) return;
  const token = decodeURIComponent(match[1]);
  await withLoading(async () => {
    await downloadFile(null, `/share/${token}/download`);
    setNotice("success", "Download started.");
  });
}

bootstrap().then(handleShareHash);
