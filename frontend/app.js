/**
 * app.js — TaskFlow v3
 * Features: JWT auth, Forgot-password/OTP, Admin panel,
 *           Notifications bell, Pagination, Groq AI indicator,
 *           dark/light mode, binary/linear search, status toggle,
 *           edit modal, localStorage cache, XSS-safe DOM rendering.
 */

const API       = "http://127.0.0.1:8000";
const CACHE_KEY = "tf_tasks_v3";
const TOKEN_KEY = "tf_token";
const USER_KEY  = "tf_user";

// ── State ─────────────────────────────────────────────────────────────────────
let currentFilter    = "all";
let currentProject   = null;
let sortedByPriority = false;
let editingTaskId    = null;
let currentPage      = 1;
let totalPages       = 1;
const PAGE_LIMIT     = 10;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const authView    = document.getElementById("authView");
const appView     = document.getElementById("appView");
const loginForm   = document.getElementById("loginForm");
const registerForm= document.getElementById("registerForm");
const tabLogin    = document.getElementById("tabLogin");
const tabRegister = document.getElementById("tabRegister");
const loginError  = document.getElementById("loginError");
const registerError = document.getElementById("registerError");
const loginSection  = document.getElementById("loginSection");
const forgotSection = document.getElementById("forgotSection");
const forgotStep1   = document.getElementById("forgotStep1");
const forgotStep2   = document.getElementById("forgotStep2");
const forgotError   = document.getElementById("forgotError");
const resetError    = document.getElementById("resetError");

const userAvatar     = document.getElementById("userAvatar");
const userNameDisplay= document.getElementById("userNameDisplay");
const logoutBtn      = document.getElementById("logoutBtn");
const themeToggle    = document.getElementById("themeToggle");
const aiDot          = document.getElementById("aiDot");
const aiLabel        = document.getElementById("aiLabel");
const quickAddBadge  = document.getElementById("quickAddBadge");

const notifBell      = document.getElementById("notifBell");
const notifBadge     = document.getElementById("notifBadge");
const notifDropdown  = document.getElementById("notifDropdown");
const notifList      = document.getElementById("notifList");
const markAllReadBtn = document.getElementById("markAllReadBtn");

const taskForm       = document.getElementById("taskForm");
const taskTitleInput = document.getElementById("taskTitle");
const taskPrioritySelect = document.getElementById("taskPriority");
const taskDueDateInput   = document.getElementById("taskDueDate");
const taskProjectSelect  = document.getElementById("taskProjectId");
const taskFormError      = document.getElementById("taskFormError");
const quickAddBtn        = document.getElementById("quickAddBtn");

const searchInput    = document.getElementById("searchInput");
const algoSelect     = document.getElementById("algoSelect");
const filterPriority = document.getElementById("filterPriority");
const sortPriorityBtn= document.getElementById("sortPriorityBtn");
const refreshBtn     = document.getElementById("refreshBtn");
const statusBanner   = document.getElementById("statusBanner");
const taskListContainer = document.getElementById("taskListContainer");
const taskListTitle  = document.getElementById("taskListTitle");
const taskCountBadge = document.getElementById("taskCountBadge");
const paginationContainer = document.getElementById("paginationContainer");

const statTotal      = document.getElementById("statTotal");
const statDone       = document.getElementById("statDone");
const statInProgress = document.getElementById("statInProgress");
const statHigh       = document.getElementById("statHigh");
const countAll       = document.getElementById("countAll");
const countTodo      = document.getElementById("countTodo");
const countInProgress= document.getElementById("countInProgress");
const countDone      = document.getElementById("countDone");

const projectList       = document.getElementById("projectList");
const showProjectFormBtn= document.getElementById("showProjectFormBtn");
const projectFormInline = document.getElementById("projectFormInline");
const newProjectName    = document.getElementById("newProjectName");
const saveProjectBtn    = document.getElementById("saveProjectBtn");

const mainTaskView    = document.getElementById("mainTaskView");
const adminView       = document.getElementById("adminView");
const adminSidebarSection = document.getElementById("adminSidebarSection");
const sidebarAdmin    = document.getElementById("sidebarAdmin");
const backToDashBtn   = document.getElementById("backToDashBtn");
const refreshAdminBtn = document.getElementById("refreshAdminBtn");
const adminUsersTbody = document.getElementById("adminUsersTbody");
const aStatUsers    = document.getElementById("aStatUsers");
const aStatProjects = document.getElementById("aStatProjects");
const aStatTasks    = document.getElementById("aStatTasks");
const aStatHigh     = document.getElementById("aStatHigh");

const editModal    = document.getElementById("editModal");
const editTitle    = document.getElementById("editTitle");
const editPriority = document.getElementById("editPriority");
const editStatus   = document.getElementById("editStatus");
const editDueDate  = document.getElementById("editDueDate");
const editSaveBtn  = document.getElementById("editSaveBtn");
const editCancelBtn= document.getElementById("editCancelBtn");

// ── Auth helpers ──────────────────────────────────────────────────────────────
const getToken = () => localStorage.getItem(TOKEN_KEY);
const getUser  = () => JSON.parse(localStorage.getItem(USER_KEY) || "null");

const authHeaders = () => ({
  "Content-Type": "application/json",
  "Authorization": `Bearer ${getToken()}`,
});

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  if (res.status === 401) { logout(); return null; }
  return res;
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  applyTheme(localStorage.getItem("tf_theme") || "dark");
  getToken() ? showApp() : showAuth();

  // Auth
  tabLogin.addEventListener("click",    () => switchAuthTab("login"));
  tabRegister.addEventListener("click", () => switchAuthTab("register"));
  loginForm.addEventListener("submit",    handleLogin);
  registerForm.addEventListener("submit", handleRegister);
  logoutBtn.addEventListener("click", logout);
  themeToggle.addEventListener("click", toggleTheme);

  // Forgot password
  document.getElementById("showForgotBtn").addEventListener("click",   showForgot);
  document.getElementById("backToLoginBtn").addEventListener("click",  showAuth);
  document.getElementById("sendOtpBtn").addEventListener("click",      handleSendOtp);
  document.getElementById("resetPasswordBtn").addEventListener("click",handleResetPassword);

  // Notifications
  notifBell.addEventListener("click", (e) => {
    e.stopPropagation();
    notifDropdown.classList.toggle("open");
    if (notifDropdown.classList.contains("open")) loadNotifications();
  });
  document.addEventListener("click", (e) => {
    if (!notifDropdown.contains(e.target) && e.target !== notifBell)
      notifDropdown.classList.remove("open");
  });
  markAllReadBtn.addEventListener("click", handleMarkAllRead);

  // Tasks
  taskForm.addEventListener("submit", handleAddTask);
  quickAddBtn.addEventListener("click", handleQuickAdd);
  taskTitleInput.addEventListener("input", () => showFormError(""));
  searchInput.addEventListener("input", debounce(handleSearch, 400));
  filterPriority.addEventListener("change", () => { currentPage = 1; fetchTasks(); });
  sortPriorityBtn.addEventListener("click", () => {
    sortedByPriority = !sortedByPriority;
    sortPriorityBtn.textContent = sortedByPriority ? "↕ Sorted ✓" : "↕ Sort Priority";
    currentPage = 1; fetchTasks();
  });
  refreshBtn.addEventListener("click", () => { currentPage = 1; fetchTasks(); });

  // Sidebar filters
  document.getElementById("sidebarAllTasks")  .addEventListener("click", () => setSidebarFilter("all"));
  document.getElementById("sidebarTodo")       .addEventListener("click", () => setSidebarFilter("todo"));
  document.getElementById("sidebarInProgress") .addEventListener("click", () => setSidebarFilter("in_progress"));
  document.getElementById("sidebarDone")        .addEventListener("click", () => setSidebarFilter("done"));

  // Projects
  showProjectFormBtn.addEventListener("click", () => {
    projectFormInline.style.display = projectFormInline.style.display === "none" ? "block" : "none";
  });
  saveProjectBtn.addEventListener("click", handleAddProject);

  // Admin
  sidebarAdmin.addEventListener("click",  showAdminPanel);
  backToDashBtn.addEventListener("click", showDashboard);
  refreshAdminBtn.addEventListener("click", loadAdminPanel);

  // Edit modal
  editCancelBtn.addEventListener("click", closeEditModal);
  editSaveBtn.addEventListener("click",   handleEditSave);
  editModal.addEventListener("click", e => { if (e.target === editModal) closeEditModal(); });
});

// ── Theme ─────────────────────────────────────────────────────────────────────
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  themeToggle.textContent = t === "dark" ? "🌙" : "☀️";
  localStorage.setItem("tf_theme", t);
}
function toggleTheme() {
  applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
}

// ── Auth ──────────────────────────────────────────────────────────────────────
function switchAuthTab(tab) {
  const isLogin = tab === "login";
  tabLogin.classList.toggle("active", isLogin);
  tabRegister.classList.toggle("active", !isLogin);
  loginForm.style.display    = isLogin ? "" : "none";
  registerForm.style.display = isLogin ? "none" : "";
  document.getElementById("showForgotBtn").style.display = isLogin ? "" : "none";
}

function showAuth() {
  authView.style.display = "flex";
  appView.classList.remove("visible");
  loginSection.style.display  = "";
  forgotSection.style.display = "none";
  switchAuthTab("login");
}

function showForgot() {
  loginSection.style.display  = "none";
  forgotSection.style.display = "";
  forgotStep1.style.display   = "";
  forgotStep2.style.display   = "none";
}

function showApp() {
  authView.style.display = "none";
  appView.classList.add("visible");
  const user = getUser();
  if (user) {
    userNameDisplay.textContent = user.user_name || user.email.split("@")[0];
    userAvatar.textContent      = (user.user_name || user.email)[0].toUpperCase();
    if (user.is_admin) adminSidebarSection.style.display = "";
  }
  checkAiStatus();
  const cached = localStorage.getItem(CACHE_KEY);
  if (cached) { try { renderTasks(JSON.parse(cached), 1, 1); } catch (_) {} }
  fetchProjects();
  fetchTasks();
  fetchUnreadCount();
}

function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  showAuth();
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  if (!email || !password) { setAuthError(loginError, "Email and password required."); return; }
  try {
    const res  = await fetch(`${API}/auth/login`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (res.ok) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_KEY,  JSON.stringify(data));
      setAuthError(loginError, "");
      showApp();
    } else { setAuthError(loginError, data.detail || "Login failed."); }
  } catch { setAuthError(loginError, "Cannot connect to server."); }
}

async function handleRegister(e) {
  e.preventDefault();
  const name     = document.getElementById("regName").value.trim();
  const email    = document.getElementById("regEmail").value.trim();
  const password = document.getElementById("regPassword").value;
  if (!email || !password) { setAuthError(registerError, "Email and password required."); return; }
  if (password.length < 6)  { setAuthError(registerError, "Password must be at least 6 chars."); return; }
  try {
    const res  = await fetch(`${API}/auth/register`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json();
    if (res.ok) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_KEY,  JSON.stringify(data));
      setAuthError(registerError, "");
      showApp();
    } else { setAuthError(registerError, data.detail || "Registration failed."); }
  } catch { setAuthError(registerError, "Cannot connect to server."); }
}

function setAuthError(el, msg) {
  el.textContent   = msg;
  el.style.display = msg ? "block" : "none";
}

// ── Forgot Password ───────────────────────────────────────────────────────────
async function handleSendOtp() {
  const email = document.getElementById("forgotEmail").value.trim();
  if (!email) { setAuthError(forgotError, "Enter your email."); return; }
  try {
    const res = await fetch(`${API}/auth/forgot-password`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    if (res.ok) {
      setAuthError(forgotError, "");
      forgotStep1.style.display = "none";
      forgotStep2.style.display = "";
    } else {
      const d = await res.json();
      setAuthError(forgotError, d.detail || "Error sending OTP.");
    }
  } catch { setAuthError(forgotError, "Cannot connect to server."); }
}

async function handleResetPassword() {
  const email       = document.getElementById("forgotEmail").value.trim();
  const otp         = document.getElementById("otpInput").value.trim();
  const newPassword = document.getElementById("newPassword").value;
  if (!otp || !newPassword) { setAuthError(resetError, "OTP and new password required."); return; }
  if (newPassword.length < 6){ setAuthError(resetError, "Password must be at least 6 chars."); return; }
  try {
    const res = await fetch(`${API}/auth/reset-password`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, otp, new_password: newPassword }),
    });
    const data = await res.json();
    if (res.ok) {
      setAuthError(resetError, "");
      showAuth();
      setTimeout(() => {
        document.getElementById("loginEmail").value = email;
        showBannerAuth("Password reset! Please log in. ✅");
      }, 100);
    } else { setAuthError(resetError, data.detail || "Reset failed."); }
  } catch { setAuthError(resetError, "Cannot connect to server."); }
}

function showBannerAuth(msg) {
  const b = document.createElement("div");
  b.className   = "status-banner success";
  b.textContent = msg;
  b.style.marginTop = "0.75rem";
  document.querySelector(".auth-card").appendChild(b);
  setTimeout(() => b.remove(), 3500);
}

// ── Groq AI status indicator ──────────────────────────────────────────────────
async function checkAiStatus() {
  try {
    const res = await apiFetch("/auth/me");
    if (!res) return;
    // We check by calling a simple endpoint — if Groq key is set server-side
    // the backend ai_parser will use it. We just show the env hint in UI.
    const groqActive = false; // server-side env — we'll update after first quick-add
    updateAiBadge(groqActive);
  } catch (_) {}
}

function updateAiBadge(isGroq) {
  aiDot.classList.toggle("active", isGroq);
  aiLabel.textContent       = isGroq ? "AI: Groq 🟢" : "AI: Mock";
  quickAddBadge.textContent = isGroq ? "Groq" : "Mock";
}

// ── Notifications ─────────────────────────────────────────────────────────────
async function fetchUnreadCount() {
  try {
    const res = await apiFetch("/notifications/unread-count");
    if (!res || !res.ok) return;
    const { count } = await res.json();
    notifBadge.textContent   = count > 9 ? "9+" : String(count);
    notifBadge.style.display = count > 0 ? "flex" : "none";
  } catch (_) {}
}

async function loadNotifications() {
  notifList.innerHTML = "<div class='notif-empty'>Loading…</div>";
  try {
    const res = await apiFetch("/notifications");
    if (!res || !res.ok) return;
    const notifs = await res.json();
    renderNotifications(notifs);
    fetchUnreadCount();
  } catch (_) {}
}

function renderNotifications(notifs) {
  notifList.innerHTML = "";
  if (!notifs.length) {
    notifList.innerHTML = "<div class='notif-empty'>No notifications yet 🎉</div>";
    return;
  }
  notifs.forEach(n => {
    const item = document.createElement("div");
    item.className = `notif-item${n.is_read ? "" : " unread"}`;

    const dot = document.createElement("div");
    dot.className = `notif-dot ${n.type}`;

    const msg = document.createElement("div");
    msg.className   = "notif-msg";
    msg.textContent = n.message;

    const time = document.createElement("div");
    time.className   = "notif-time";
    time.textContent = formatTime(n.created_at);

    item.appendChild(dot);
    item.appendChild(msg);
    item.appendChild(time);

    if (!n.is_read) {
      item.addEventListener("click", () => markNotifRead(n.id, item));
    }
    notifList.appendChild(item);
  });
}

async function markNotifRead(id, el) {
  el.classList.remove("unread");
  await apiFetch(`/notifications/${id}/read`, { method: "PATCH" });
  fetchUnreadCount();
}

async function handleMarkAllRead() {
  await apiFetch("/notifications/read-all", { method: "PATCH" });
  notifDropdown.classList.remove("open");
  fetchUnreadCount();
}

function formatTime(iso) {
  try {
    const d = new Date(iso + "Z");
    return d.toLocaleString("en-IN", { month:"short", day:"numeric", hour:"2-digit", minute:"2-digit" });
  } catch { return iso.slice(0, 16).replace("T", " "); }
}

// ── Projects ──────────────────────────────────────────────────────────────────
async function fetchProjects() {
  try {
    const res = await apiFetch("/projects");
    if (!res || !res.ok) return;
    const projects = await res.json();
    renderProjectSidebar(projects);
    populateProjectDropdown(projects);
  } catch (_) {}
}

function renderProjectSidebar(projects) {
  projectList.innerHTML = "";
  projects.forEach(p => {
    const btn = document.createElement("button");
    btn.className = "sidebar-item" + (currentProject === p.id ? " active" : "");
    const icon = document.createElement("span"); icon.className = "item-icon"; icon.textContent = "📁";
    const lbl  = document.createElement("span"); lbl.textContent = p.title;
    btn.appendChild(icon); btn.appendChild(lbl);
    btn.addEventListener("click", () => {
      currentProject = currentProject === p.id ? null : p.id;
      currentPage = 1;
      document.getElementById("sidebarAllTasks").classList.toggle("active", !currentProject);
      fetchTasks(); fetchProjects();
    });
    projectList.appendChild(btn);
  });
}

function populateProjectDropdown(projects) {
  taskProjectSelect.innerHTML = "";
  if (!projects.length) {
    const o = document.createElement("option"); o.value = "1"; o.textContent = "Project #1";
    taskProjectSelect.appendChild(o); return;
  }
  projects.forEach(p => {
    const o = document.createElement("option"); o.value = p.id; o.textContent = p.title;
    taskProjectSelect.appendChild(o);
  });
}

async function handleAddProject() {
  const name = newProjectName.value.trim();
  if (!name) return;
  const user = getUser();
  if (!user) return;
  const res = await apiFetch("/projects", {
    method: "POST", body: JSON.stringify({ title: name, owner_id: user.user_id }),
  });
  if (res && res.ok) {
    newProjectName.value = "";
    projectFormInline.style.display = "none";
    fetchProjects(); fetchUnreadCount();
  }
}

// ── Fetch Tasks (paginated) ───────────────────────────────────────────────────
async function fetchTasks() {
  showBanner("Loading…", "info");
  try {
    const params = new URLSearchParams();
    params.set("page",  currentPage);
    params.set("limit", PAGE_LIMIT);
    if (sortedByPriority)        params.set("sort",       "priority");
    if (currentProject)          params.set("project_id", currentProject);
    if (filterPriority.value)    params.set("priority",   filterPriority.value);
    if (currentFilter !== "all") params.set("status",     currentFilter);

    const res = await apiFetch(`/tasks?${params}`);
    if (!res) return;
    if (!res.ok) { showBanner("Failed to load tasks.", "error"); return; }

    const data = await res.json();         // PaginatedTaskResponse
    totalPages = data.total_pages;
    localStorage.setItem(CACHE_KEY, JSON.stringify(data.tasks));
    renderTasks(data.tasks, data.page, data.total);
    renderPagination(data.page, data.total_pages, data.total);
    updateStats(data.tasks, data.total);
    hideBanner();
    fetchUnreadCount();
  } catch (_) {
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) renderTasks(JSON.parse(cached), 1, 0);
    showBanner("Backend unreachable — showing cached data.", "error");
  }
}

// ── Sidebar filter ────────────────────────────────────────────────────────────
function setSidebarFilter(filter) {
  currentFilter  = filter;
  currentProject = null;
  currentPage    = 1;
  document.querySelectorAll(".sidebar-item[data-filter]").forEach(b =>
    b.classList.toggle("active", b.dataset.filter === filter));
  const labels = { all:"All Tasks", todo:"To Do", in_progress:"In Progress", done:"Done" };
  taskListTitle.textContent = labels[filter] || "Tasks";
  fetchTasks();
}

// ── Stats ─────────────────────────────────────────────────────────────────────
function updateStats(pageTasks, total) {
  statTotal.textContent      = total;
  statDone.textContent       = pageTasks.filter(t => t.status === "done").length;
  statInProgress.textContent = pageTasks.filter(t => t.status === "in_progress").length;
  statHigh.textContent       = pageTasks.filter(t => t.priority === "high").length;
  taskCountBadge.textContent = `${total} task${total !== 1 ? "s" : ""}`;

  countAll.textContent        = total;
  countTodo.textContent       = pageTasks.filter(t => t.status === "todo").length;
  countInProgress.textContent = pageTasks.filter(t => t.status === "in_progress").length;
  countDone.textContent       = pageTasks.filter(t => t.status === "done").length;
}

// ── Pagination ────────────────────────────────────────────────────────────────
function renderPagination(page, pages, total) {
  paginationContainer.innerHTML = "";
  if (pages <= 1) return;

  const prev = document.createElement("button");
  prev.className = "page-btn"; prev.textContent = "←";
  prev.disabled = page <= 1;
  prev.addEventListener("click", () => { currentPage = page - 1; fetchTasks(); });
  paginationContainer.appendChild(prev);

  // Show limited page numbers
  const range = [];
  for (let i = Math.max(1, page-2); i <= Math.min(pages, page+2); i++) range.push(i);

  if (range[0] > 1) {
    const dots = document.createElement("span");
    dots.className = "page-info"; dots.textContent = "…";
    paginationContainer.appendChild(dots);
  }

  range.forEach(p => {
    const btn = document.createElement("button");
    btn.className = `page-btn${p === page ? " active" : ""}`;
    btn.textContent = p;
    btn.addEventListener("click", () => { currentPage = p; fetchTasks(); });
    paginationContainer.appendChild(btn);
  });

  if (range[range.length-1] < pages) {
    const dots = document.createElement("span");
    dots.className = "page-info"; dots.textContent = "…";
    paginationContainer.appendChild(dots);
  }

  const next = document.createElement("button");
  next.className = "page-btn"; next.textContent = "→";
  next.disabled = page >= pages;
  next.addEventListener("click", () => { currentPage = page + 1; fetchTasks(); });
  paginationContainer.appendChild(next);

  const info = document.createElement("span");
  info.className   = "page-info";
  info.textContent = `Page ${page} of ${pages}`;
  paginationContainer.appendChild(info);
}

// ── Search ────────────────────────────────────────────────────────────────────
async function handleSearch() {
  const q = searchInput.value.trim();
  if (!q) { currentPage = 1; fetchTasks(); return; }
  const algo = algoSelect.value;
  showBanner(`Searching via ${algo} search…`, "info");
  try {
    const res = await apiFetch(`/tasks/search?title=${encodeURIComponent(q)}&algo=${algo}`);
    if (!res) return;
    if (res.status === 404) { renderTasks([], 1, 0); showBanner(`No task found: "${q}"`, "error"); return; }
    const task = await res.json();
    renderTasks([task], 1, 1);
    paginationContainer.innerHTML = "";
    showBanner(`Found via ${algo} search ✓`, "success");
  } catch { showBanner("Search error.", "error"); }
}

// ── Render Tasks ──────────────────────────────────────────────────────────────
function renderTasks(tasks, page, total) {
  taskListContainer.innerHTML = "";
  if (!tasks || !tasks.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const ico = document.createElement("div"); ico.className = "empty-icon"; ico.textContent = "📭";
    const msg = document.createElement("p");   msg.textContent = "No tasks found. Create one above!";
    empty.appendChild(ico); empty.appendChild(msg);
    taskListContainer.appendChild(empty);
    return;
  }
  tasks.forEach(task => {
    const card = document.createElement("div");
    card.className = `task-card${task.status === "done" ? " done" : ""}`;
    card.dataset.taskId = task.id;

    // Status toggle circle
    const statusBtn = document.createElement("button");
    statusBtn.className = `status-btn ${task.status}`;
    statusBtn.title = `Status: ${task.status} — click to advance`;
    statusBtn.textContent = task.status === "done" ? "✓" : task.status === "in_progress" ? "↻" : "";
    statusBtn.addEventListener("click", () => handleStatusToggle(task.id));

    const body = document.createElement("div"); body.className = "task-body";
    const title = document.createElement("div"); title.className = "task-title";
    title.textContent = task.title;             // XSS-safe textContent

    const meta = document.createElement("div"); meta.className = "task-meta";
    const priBadge = document.createElement("span");
    priBadge.className = `badge badge-${task.priority}`;
    priBadge.textContent = task.priority.toUpperCase();

    const stBadge = document.createElement("span");
    stBadge.className = `badge badge-${task.status}`;
    stBadge.textContent = task.status.replace("_"," ").toUpperCase();
    meta.appendChild(priBadge); meta.appendChild(stBadge);

    if (task.due_date) {
      const db = document.createElement("span");
      db.className = "badge badge-date"; db.textContent = "📅 " + task.due_date;
      meta.appendChild(db);
    }
    body.appendChild(title); body.appendChild(meta);

    const actions = document.createElement("div"); actions.className = "task-actions";
    const editBtn = document.createElement("button");
    editBtn.className = "btn-icon"; editBtn.title = "Edit"; editBtn.textContent = "✏️";
    editBtn.addEventListener("click", () => openEditModal(task));
    const delBtn = document.createElement("button");
    delBtn.className = "btn-icon"; delBtn.title = "Delete"; delBtn.textContent = "🗑️";
    delBtn.addEventListener("click", () => handleDelete(task.id));
    actions.appendChild(editBtn); actions.appendChild(delBtn);

    card.appendChild(statusBtn); card.appendChild(body); card.appendChild(actions);
    taskListContainer.appendChild(card);
  });
}

// ── Task CRUD ─────────────────────────────────────────────────────────────────
async function handleAddTask(e) {
  e.preventDefault();
  const title = taskTitleInput.value.trim();
  if (!title) { showFormError("Task title cannot be empty."); taskTitleInput.focus(); return; }
  const res = await apiFetch("/tasks", {
    method: "POST",
    body: JSON.stringify({
      title, priority: taskPrioritySelect.value,
      due_date: taskDueDateInput.value.trim() || null,
      project_id: parseInt(taskProjectSelect.value, 10), status: "todo",
    }),
  });
  if (!res) return;
  if (res.status === 201) {
    taskForm.reset(); showFormError("");
    showBanner("Task created ✓", "success");
    currentPage = 1; fetchTasks(); fetchUnreadCount();
  } else {
    const err = await res.json(); showFormError(err.detail || "Failed to create task.");
  }
}

async function handleQuickAdd() {
  const desc = taskTitleInput.value.trim();
  if (!desc) { showFormError("Enter a description for AI Quick-Add."); taskTitleInput.focus(); return; }
  showBanner("🤖 AI parsing…", "info");
  const res = await apiFetch("/tasks/quick-add", {
    method: "POST",
    body: JSON.stringify({ description: desc, project_id: parseInt(taskProjectSelect.value, 10) }),
  });
  if (!res) return;
  if (res.status === 201) {
    taskForm.reset(); showFormError("");
    showBanner("🤖 AI Quick-Add: task created ✓", "success");
    updateAiBadge(true);     // assume Groq was used if server configured it
    currentPage = 1; fetchTasks(); fetchUnreadCount();
  } else {
    const err = await res.json(); showFormError(err.detail || "AI Quick-Add failed."); hideBanner();
  }
}

async function handleStatusToggle(taskId) {
  const res = await apiFetch(`/tasks/${taskId}/complete`, { method: "PATCH" });
  if (res && res.ok) { fetchTasks(); fetchUnreadCount(); }
}

async function handleDelete(taskId) {
  if (!confirm(`Delete Task #${taskId}?`)) return;
  const res = await apiFetch(`/tasks/${taskId}`, { method: "DELETE" });
  if (res && res.ok) { showBanner("Task deleted.", "success"); fetchTasks(); }
}

function openEditModal(task) {
  editingTaskId = task.id;
  editTitle.value    = task.title;
  editPriority.value = task.priority;
  editStatus.value   = task.status;
  editDueDate.value  = task.due_date || "";
  editModal.classList.add("open"); editTitle.focus();
}
function closeEditModal() { editModal.classList.remove("open"); editingTaskId = null; }
async function handleEditSave() {
  if (!editingTaskId) return;
  const title = editTitle.value.trim();
  if (!title) { alert("Title cannot be blank."); return; }
  const res = await apiFetch(`/tasks/${editingTaskId}`, {
    method: "PUT",
    body: JSON.stringify({ title, priority: editPriority.value,
                           status: editStatus.value, due_date: editDueDate.value.trim() || null }),
  });
  if (res && res.ok) {
    closeEditModal(); showBanner("Task updated ✓", "success");
    fetchTasks(); fetchUnreadCount();
  }
}

// ── Admin Panel ───────────────────────────────────────────────────────────────
function showAdminPanel() {
  mainTaskView.style.display = "none";
  adminView.classList.add("active");
  loadAdminPanel();
}
function showDashboard() {
  adminView.classList.remove("active");
  mainTaskView.style.display = "";
}

async function loadAdminPanel() {
  try {
    const [statsRes, usersRes] = await Promise.all([
      apiFetch("/admin/stats"),
      apiFetch("/admin/users"),
    ]);
    if (statsRes && statsRes.ok) {
      const s = await statsRes.json();
      aStatUsers.textContent    = s.total_users;
      aStatProjects.textContent = s.total_projects;
      aStatTasks.textContent    = s.total_tasks;
      aStatHigh.textContent     = s.high_priority_count;
    }
    if (usersRes && usersRes.ok) {
      const users = await usersRes.json();
      renderAdminUsersTable(users);
    }
  } catch (_) {}
}

function renderAdminUsersTable(users) {
  adminUsersTbody.innerHTML = "";
  if (!users.length) {
    adminUsersTbody.innerHTML = "<tr><td colspan='5' style='text-align:center;padding:1rem;color:var(--text-muted)'>No users found</td></tr>";
    return;
  }
  const me = getUser();
  users.forEach(u => {
    const tr = document.createElement("tr");

    const tdId   = document.createElement("td"); tdId.textContent   = u.id;
    const tdName = document.createElement("td"); tdName.textContent = u.name || "—";
    const tdEmail= document.createElement("td"); tdEmail.textContent= u.email;

    const tdAdmin = document.createElement("td");
    const badge = document.createElement("span");
    badge.className   = `admin-badge ${u.is_admin ? "yes" : "no"}`;
    badge.textContent = u.is_admin ? "Admin" : "User";
    tdAdmin.appendChild(badge);

    const tdAction = document.createElement("td");
    if (u.id !== me?.user_id) {
      if (!u.is_admin) {
        const makeAdminBtn = document.createElement("button");
        makeAdminBtn.className   = "btn btn-ghost btn-sm";
        makeAdminBtn.textContent = "Make Admin";
        makeAdminBtn.style.marginRight = "0.4rem";
        makeAdminBtn.addEventListener("click", () => handleMakeAdmin(u.id));
        tdAction.appendChild(makeAdminBtn);
      }
      const delBtn = document.createElement("button");
      delBtn.className   = "btn btn-danger btn-sm";
      delBtn.textContent = "Delete";
      delBtn.addEventListener("click", () => handleAdminDeleteUser(u.id, u.email));
      tdAction.appendChild(delBtn);
    } else {
      tdAction.textContent = "(You)";
      tdAction.style.color = "var(--text-muted)";
    }

    tr.appendChild(tdId); tr.appendChild(tdName); tr.appendChild(tdEmail);
    tr.appendChild(tdAdmin); tr.appendChild(tdAction);
    adminUsersTbody.appendChild(tr);
  });
}

async function handleMakeAdmin(userId) {
  const res = await apiFetch(`/admin/make-admin/${userId}`, { method: "POST" });
  if (res && res.ok) { showBanner("User promoted to Admin ✓", "success"); loadAdminPanel(); }
}

async function handleAdminDeleteUser(userId, email) {
  if (!confirm(`Delete user ${email}? This cannot be undone.`)) return;
  const res = await apiFetch(`/admin/users/${userId}`, { method: "DELETE" });
  if (res && res.ok) { showBanner("User deleted.", "success"); loadAdminPanel(); }
}

// ── UI Helpers ────────────────────────────────────────────────────────────────
function showFormError(msg) {
  taskFormError.textContent   = msg;
  taskFormError.style.display = msg ? "block" : "none";
}

function showBanner(msg, type = "info") {
  statusBanner.textContent   = msg;
  statusBanner.className     = `status-banner ${type}`;
  statusBanner.style.display = "block";
  if (type === "success") setTimeout(hideBanner, 2500);
}
function hideBanner() {
  statusBanner.style.display = "none";
  statusBanner.textContent   = "";
}

function debounce(fn, delay) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}
