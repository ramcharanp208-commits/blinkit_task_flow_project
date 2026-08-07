/**
 * app.js — TaskFlow v2
 * Features: JWT auth, dark/light mode, search (binary/linear),
 *           filters, status toggle, edit modal, AI quick-add,
 *           localStorage cache, XSS-safe DOM rendering.
 */

const API  = "http://127.0.0.1:8000";
const CACHE_KEY = "tf_tasks_v2";
const TOKEN_KEY = "tf_token";
const USER_KEY  = "tf_user";

// ── State ─────────────────────────────────────────────────────────────────────
let currentFilter   = "all";   // all | todo | in_progress | done
let currentProject  = null;    // null = all projects
let allTasks        = [];
let allProjects     = [];
let editingTaskId   = null;
let sortedByPriority = false;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const authView       = document.getElementById("authView");
const appView        = document.getElementById("appView");
const loginForm      = document.getElementById("loginForm");
const registerForm   = document.getElementById("registerForm");
const tabLogin       = document.getElementById("tabLogin");
const tabRegister    = document.getElementById("tabRegister");
const loginError     = document.getElementById("loginError");
const registerError  = document.getElementById("registerError");

const userAvatar     = document.getElementById("userAvatar");
const userNameDisplay= document.getElementById("userNameDisplay");
const logoutBtn      = document.getElementById("logoutBtn");
const themeToggle    = document.getElementById("themeToggle");

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

const statTotal      = document.getElementById("statTotal");
const statDone       = document.getElementById("statDone");
const statInProgress = document.getElementById("statInProgress");
const statHigh       = document.getElementById("statHigh");

const projectList      = document.getElementById("projectList");
const showProjectFormBtn = document.getElementById("showProjectFormBtn");
const projectFormInline  = document.getElementById("projectFormInline");
const newProjectName     = document.getElementById("newProjectName");
const saveProjectBtn     = document.getElementById("saveProjectBtn");

const countAll        = document.getElementById("countAll");
const countTodo       = document.getElementById("countTodo");
const countInProgress = document.getElementById("countInProgress");
const countDone       = document.getElementById("countDone");

const editModal    = document.getElementById("editModal");
const editTitle    = document.getElementById("editTitle");
const editPriority = document.getElementById("editPriority");
const editStatus   = document.getElementById("editStatus");
const editDueDate  = document.getElementById("editDueDate");
const editSaveBtn  = document.getElementById("editSaveBtn");
const editCancelBtn= document.getElementById("editCancelBtn");

// ── Token helpers ─────────────────────────────────────────────────────────────
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

  if (getToken()) {
    showApp();
  } else {
    showAuth();
  }

  // Auth tabs
  tabLogin.addEventListener("click", () => switchAuthTab("login"));
  tabRegister.addEventListener("click", () => switchAuthTab("register"));

  // Auth forms
  loginForm.addEventListener("submit", handleLogin);
  registerForm.addEventListener("submit", handleRegister);

  // Logout & theme
  logoutBtn.addEventListener("click", logout);
  themeToggle.addEventListener("click", toggleTheme);

  // Task form
  taskForm.addEventListener("submit", handleAddTask);
  quickAddBtn.addEventListener("click", handleQuickAdd);
  taskTitleInput.addEventListener("input", () => showFormError(""));

  // Search (debounced)
  searchInput.addEventListener("input", debounce(handleSearch, 400));

  // Filters & sort
  filterPriority.addEventListener("change", () => fetchTasks());
  sortPriorityBtn.addEventListener("click", () => {
    sortedByPriority = !sortedByPriority;
    sortPriorityBtn.textContent = sortedByPriority ? "↕ Sorted ✓" : "↕ Sort Priority";
    fetchTasks();
  });
  refreshBtn.addEventListener("click", () => fetchTasks());

  // Sidebar filter buttons
  document.getElementById("sidebarAllTasks")  .addEventListener("click", () => setSidebarFilter("all"));
  document.getElementById("sidebarTodo")       .addEventListener("click", () => setSidebarFilter("todo"));
  document.getElementById("sidebarInProgress") .addEventListener("click", () => setSidebarFilter("in_progress"));
  document.getElementById("sidebarDone")        .addEventListener("click", () => setSidebarFilter("done"));

  // Project form
  showProjectFormBtn.addEventListener("click", () => {
    projectFormInline.style.display =
      projectFormInline.style.display === "none" ? "block" : "none";
  });
  saveProjectBtn.addEventListener("click", handleAddProject);

  // Edit modal
  editCancelBtn.addEventListener("click", closeEditModal);
  editSaveBtn.addEventListener("click", handleEditSave);
  editModal.addEventListener("click", e => { if (e.target === editModal) closeEditModal(); });
});

// ── Theme ─────────────────────────────────────────────────────────────────────
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  themeToggle.textContent = theme === "dark" ? "🌙" : "☀️";
  localStorage.setItem("tf_theme", theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme");
  applyTheme(current === "dark" ? "light" : "dark");
}

// ── Auth tab switch ───────────────────────────────────────────────────────────
function switchAuthTab(tab) {
  if (tab === "login") {
    tabLogin.classList.add("active");
    tabRegister.classList.remove("active");
    loginForm.style.display = "";
    registerForm.style.display = "none";
  } else {
    tabRegister.classList.add("active");
    tabLogin.classList.remove("active");
    registerForm.style.display = "";
    loginForm.style.display = "none";
  }
}

function showAuth() {
  authView.style.display = "flex";
  appView.classList.remove("visible");
}

function showApp() {
  authView.style.display = "none";
  appView.classList.add("visible");
  const user = getUser();
  if (user) {
    userNameDisplay.textContent = user.user_name || user.email.split("@")[0];
    userAvatar.textContent = (user.user_name || user.email)[0].toUpperCase();
  }
  // Render cached tasks immediately then fetch live
  const cached = localStorage.getItem(CACHE_KEY);
  if (cached) { try { renderTasks(JSON.parse(cached)); } catch(_) {} }
  fetchProjects();
  fetchTasks();
}

function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  allTasks = [];
  allProjects = [];
  showAuth();
}

// ── Login ─────────────────────────────────────────────────────────────────────
async function handleLogin(e) {
  e.preventDefault();
  const email    = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  if (!email || !password) { setAuthError(loginError, "Email and password required."); return; }

  try {
    const res = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (res.ok) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(data));
      setAuthError(loginError, "");
      showApp();
    } else {
      setAuthError(loginError, data.detail || "Login failed.");
    }
  } catch {
    setAuthError(loginError, "Cannot connect to server.");
  }
}

// ── Register ──────────────────────────────────────────────────────────────────
async function handleRegister(e) {
  e.preventDefault();
  const name     = document.getElementById("regName").value.trim();
  const email    = document.getElementById("regEmail").value.trim();
  const password = document.getElementById("regPassword").value;
  if (!email || !password) { setAuthError(registerError, "Email and password required."); return; }
  if (password.length < 6)  { setAuthError(registerError, "Password must be at least 6 characters."); return; }

  try {
    const res = await fetch(`${API}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json();
    if (res.ok) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(data));
      setAuthError(registerError, "");
      showApp();
    } else {
      setAuthError(registerError, data.detail || "Registration failed.");
    }
  } catch {
    setAuthError(registerError, "Cannot connect to server.");
  }
}

function setAuthError(el, msg) {
  el.textContent = msg;
  el.style.display = msg ? "block" : "none";
}

// ── Projects ──────────────────────────────────────────────────────────────────
async function fetchProjects() {
  try {
    const res = await apiFetch("/projects");
    if (!res || !res.ok) return;
    allProjects = await res.json();
    renderProjectSidebar();
    populateProjectDropdown();
  } catch { /* silent */ }
}

function renderProjectSidebar() {
  projectList.innerHTML = "";
  allProjects.forEach(p => {
    const btn = document.createElement("button");
    btn.className = "sidebar-item" + (currentProject === p.id ? " active" : "");
    btn.innerHTML = "";
    const icon = document.createElement("span");
    icon.className = "item-icon";
    icon.textContent = "📁";
    const label = document.createElement("span");
    label.textContent = p.title;
    btn.appendChild(icon);
    btn.appendChild(label);
    btn.addEventListener("click", () => {
      currentProject = currentProject === p.id ? null : p.id;
      document.getElementById("sidebarAllTasks").classList.toggle("active", !currentProject);
      fetchTasks();
      renderProjectSidebar();
    });
    projectList.appendChild(btn);
  });
}

function populateProjectDropdown() {
  taskProjectSelect.innerHTML = "";
  allProjects.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.title;
    taskProjectSelect.appendChild(opt);
  });
  if (allProjects.length === 0) {
    const opt = document.createElement("option");
    opt.value = "1";
    opt.textContent = "Project #1";
    taskProjectSelect.appendChild(opt);
  }
}

async function handleAddProject() {
  const name = newProjectName.value.trim();
  if (!name) return;
  const user = getUser();
  if (!user) return;
  try {
    const res = await apiFetch("/projects", {
      method: "POST",
      body: JSON.stringify({ title: name, owner_id: user.user_id }),
    });
    if (res && res.ok) {
      newProjectName.value = "";
      projectFormInline.style.display = "none";
      fetchProjects();
    }
  } catch { /* silent */ }
}

// ── Fetch Tasks ───────────────────────────────────────────────────────────────
async function fetchTasks() {
  showBanner("Loading…", "info");
  try {
    const params = new URLSearchParams();
    if (sortedByPriority)                     params.set("sort", "priority");
    if (currentProject)                        params.set("project_id", currentProject);
    if (filterPriority.value)                  params.set("priority", filterPriority.value);
    if (currentFilter !== "all")               params.set("status", currentFilter);

    const res = await apiFetch(`/tasks?${params.toString()}`);
    if (!res) return;
    if (!res.ok) { showBanner("Failed to load tasks.", "error"); return; }

    allTasks = await res.json();
    localStorage.setItem(CACHE_KEY, JSON.stringify(allTasks));
    renderTasks(allTasks);
    updateStats(allTasks);
    updateSidebarCounts(allTasks);
    hideBanner();
  } catch (err) {
    showBanner("Backend unreachable — showing cached data.", "error");
  }
}

// ── Sidebar filter ────────────────────────────────────────────────────────────
function setSidebarFilter(filter) {
  currentFilter  = filter;
  currentProject = null;
  document.querySelectorAll(".sidebar-item[data-filter]").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.filter === filter);
  });
  const labels = { all: "All Tasks", todo: "To Do", in_progress: "In Progress", done: "Done" };
  taskListTitle.textContent = labels[filter] || "Tasks";
  fetchTasks();
}

// ── Search ────────────────────────────────────────────────────────────────────
async function handleSearch() {
  const q = searchInput.value.trim();
  if (!q) { fetchTasks(); return; }

  const algo = algoSelect.value;
  showBanner(`Searching with ${algo} search…`, "info");
  try {
    const res = await apiFetch(`/tasks/search?title=${encodeURIComponent(q)}&algo=${algo}`);
    if (!res) return;
    if (res.status === 404) {
      renderTasks([]);
      showBanner(`No task found with title "${q}"`, "error");
      return;
    }
    const task = await res.json();
    renderTasks([task]);
    showBanner(`Found via ${algo} search ✓`, "success");
  } catch {
    showBanner("Search error.", "error");
  }
}

// ── Stats ─────────────────────────────────────────────────────────────────────
function updateStats(tasks) {
  statTotal.textContent      = tasks.length;
  statDone.textContent       = tasks.filter(t => t.status === "done").length;
  statInProgress.textContent = tasks.filter(t => t.status === "in_progress").length;
  statHigh.textContent       = tasks.filter(t => t.priority === "high").length;
}

function updateSidebarCounts(tasks) {
  countAll.textContent        = tasks.length;
  countTodo.textContent       = tasks.filter(t => t.status === "todo").length;
  countInProgress.textContent = tasks.filter(t => t.status === "in_progress").length;
  countDone.textContent       = tasks.filter(t => t.status === "done").length;
  taskCountBadge.textContent  = `${tasks.length} task${tasks.length !== 1 ? "s" : ""}`;
}

// ── Render Tasks ──────────────────────────────────────────────────────────────
function renderTasks(tasks) {
  taskListContainer.innerHTML = "";

  if (!tasks || tasks.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const icon = document.createElement("div");
    icon.className = "empty-icon";
    icon.textContent = "📭";
    const msg = document.createElement("p");
    msg.textContent = "No tasks found. Create one above!";
    empty.appendChild(icon);
    empty.appendChild(msg);
    taskListContainer.appendChild(empty);
    return;
  }

  tasks.forEach(task => {
    const card = document.createElement("div");
    card.className = `task-card${task.status === "done" ? " done" : ""}`;
    card.dataset.taskId = task.id;

    // Status toggle button
    const statusBtn = document.createElement("button");
    statusBtn.className = `status-btn ${task.status}`;
    statusBtn.title = `Status: ${task.status} — click to advance`;
    statusBtn.textContent = task.status === "done" ? "✓" : task.status === "in_progress" ? "↻" : "";
    statusBtn.addEventListener("click", () => handleStatusToggle(task.id));

    // Task body
    const body = document.createElement("div");
    body.className = "task-body";

    const title = document.createElement("div");
    title.className = "task-title";
    title.textContent = task.title;  // textContent — XSS safe

    const meta = document.createElement("div");
    meta.className = "task-meta";

    const priBadge = document.createElement("span");
    priBadge.className = `badge badge-${task.priority}`;
    priBadge.textContent = task.priority.toUpperCase();

    const statusBadge = document.createElement("span");
    statusBadge.className = `badge badge-${task.status}`;
    statusBadge.textContent = task.status.replace("_", " ").toUpperCase();

    meta.appendChild(priBadge);
    meta.appendChild(statusBadge);

    if (task.due_date) {
      const dateBadge = document.createElement("span");
      dateBadge.className = "badge badge-date";
      dateBadge.textContent = "📅 " + task.due_date;
      meta.appendChild(dateBadge);
    }

    body.appendChild(title);
    body.appendChild(meta);

    // Actions
    const actions = document.createElement("div");
    actions.className = "task-actions";

    const editBtn = document.createElement("button");
    editBtn.className = "btn-icon";
    editBtn.title = "Edit task";
    editBtn.textContent = "✏️";
    editBtn.addEventListener("click", () => openEditModal(task));

    const delBtn = document.createElement("button");
    delBtn.className = "btn-icon";
    delBtn.title = "Delete task";
    delBtn.textContent = "🗑️";
    delBtn.addEventListener("click", () => handleDelete(task.id));

    actions.appendChild(editBtn);
    actions.appendChild(delBtn);

    card.appendChild(statusBtn);
    card.appendChild(body);
    card.appendChild(actions);
    taskListContainer.appendChild(card);
  });
}

// ── Add Task ──────────────────────────────────────────────────────────────────
async function handleAddTask(e) {
  e.preventDefault();
  const title = taskTitleInput.value.trim();
  if (!title) { showFormError("Task title cannot be empty."); taskTitleInput.focus(); return; }

  const payload = {
    title,
    priority:   taskPrioritySelect.value,
    due_date:   taskDueDateInput.value.trim() || null,
    project_id: parseInt(taskProjectSelect.value, 10),
    status:     "todo",
  };

  try {
    const res = await apiFetch("/tasks", { method: "POST", body: JSON.stringify(payload) });
    if (!res) return;
    if (res.status === 201) {
      taskForm.reset();
      showFormError("");
      showBanner("Task created ✓", "success");
      fetchTasks();
    } else {
      const err = await res.json();
      showFormError(err.detail || "Failed to create task.");
    }
  } catch {
    showFormError("Network error — cannot reach backend.");
  }
}

// ── AI Quick-Add ──────────────────────────────────────────────────────────────
async function handleQuickAdd() {
  const desc = taskTitleInput.value.trim();
  if (!desc) { showFormError("Enter a plain-English description for AI Quick-Add."); taskTitleInput.focus(); return; }

  const projectId = parseInt(taskProjectSelect.value, 10);
  showBanner("🤖 AI parsing description…", "info");

  try {
    const res = await apiFetch("/tasks/quick-add", {
      method: "POST",
      body: JSON.stringify({ description: desc, project_id: projectId }),
    });
    if (!res) return;
    if (res.status === 201) {
      taskForm.reset();
      showFormError("");
      showBanner("🤖 AI Quick-Add: task created ✓", "success");
      fetchTasks();
    } else {
      const err = await res.json();
      showFormError(err.detail || "AI Quick-Add failed.");
      hideBanner();
    }
  } catch {
    showFormError("Network error on AI Quick-Add.");
    hideBanner();
  }
}

// ── Status Toggle (PATCH) ─────────────────────────────────────────────────────
async function handleStatusToggle(taskId) {
  try {
    const res = await apiFetch(`/tasks/${taskId}/complete`, { method: "PATCH" });
    if (res && res.ok) fetchTasks();
  } catch { /* silent */ }
}

// ── Delete ────────────────────────────────────────────────────────────────────
async function handleDelete(taskId) {
  if (!confirm(`Delete Task #${taskId}?`)) return;
  try {
    const res = await apiFetch(`/tasks/${taskId}`, { method: "DELETE" });
    if (res && res.ok) {
      showBanner("Task deleted.", "success");
      fetchTasks();
    }
  } catch { /* silent */ }
}

// ── Edit Modal ────────────────────────────────────────────────────────────────
function openEditModal(task) {
  editingTaskId       = task.id;
  editTitle.value     = task.title;
  editPriority.value  = task.priority;
  editStatus.value    = task.status;
  editDueDate.value   = task.due_date || "";
  editModal.classList.add("open");
  editTitle.focus();
}

function closeEditModal() {
  editModal.classList.remove("open");
  editingTaskId = null;
}

async function handleEditSave() {
  if (!editingTaskId) return;
  const title = editTitle.value.trim();
  if (!title) { alert("Title cannot be blank."); return; }

  try {
    const res = await apiFetch(`/tasks/${editingTaskId}`, {
      method: "PUT",
      body: JSON.stringify({
        title,
        priority: editPriority.value,
        status:   editStatus.value,
        due_date: editDueDate.value.trim() || null,
      }),
    });
    if (res && res.ok) {
      closeEditModal();
      showBanner("Task updated ✓", "success");
      fetchTasks();
    }
  } catch { /* silent */ }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
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
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}
