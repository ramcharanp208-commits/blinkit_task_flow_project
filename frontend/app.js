/**
 * app.js — TaskFlow Frontend
 *
 * Sections covered:
 *  Task 11 — DOM rendering via createElement / appendChild / textContent
 *  Task 12 — add / edit / delete with addEventListener, event.preventDefault()
 *  Task 13 — client-side validation with live error clearing
 *  Task 14 — localStorage cache: render cached copy first, refresh from backend
 *  Task 15 — all data comes from / goes to the real FastAPI backend
 */

const API_BASE_URL = "http://127.0.0.1:8000";
const CACHE_KEY    = "taskflow_cached_tasks";

// ── DOM references ──────────────────────────────────────────────────────────
const taskForm          = document.getElementById("taskForm");
const taskTitleInput    = document.getElementById("taskTitle");
const taskPrioritySelect = document.getElementById("taskPriority");
const taskDueDateInput  = document.getElementById("taskDueDate");
const projectIdInput    = document.getElementById("projectId");
const titleError        = document.getElementById("titleError");
const taskListContainer = document.getElementById("taskListContainer");
const sortPriorityBtn   = document.getElementById("sortPriorityBtn");
const quickAddBtn       = document.getElementById("quickAddBtn");
const refreshBtn        = document.getElementById("refreshBtn");
const statusBanner      = document.getElementById("statusBanner");

// ── Initialisation ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Task 14: show cached copy immediately so the page is never blank
  loadCachedTasks();

  // Task 15: fetch live data from backend
  fetchTasksFromBackend();

  // Task 12: event listeners — no inline onclick anywhere
  taskForm.addEventListener("submit", handleFormSubmit);
  quickAddBtn.addEventListener("click", handleQuickAdd);
  sortPriorityBtn.addEventListener("click", () => fetchTasksFromBackend("priority"));
  refreshBtn.addEventListener("click", () => fetchTasksFromBackend());

  // Task 13: clear error as soon as the user starts typing
  taskTitleInput.addEventListener("input", clearValidationError);
});

// ── localStorage cache ──────────────────────────────────────────────────────
function loadCachedTasks() {
  const raw = localStorage.getItem(CACHE_KEY);
  if (!raw) return;
  try {
    const tasks = JSON.parse(raw);          // Task 14: JSON.parse on load
    renderTaskList(tasks);
  } catch (e) {
    console.warn("Cache parse failed — ignoring stale data", e);
  }
}

function saveCache(tasks) {
  localStorage.setItem(CACHE_KEY, JSON.stringify(tasks));  // Task 14: JSON.stringify on save
}

// ── Backend API calls ────────────────────────────────────────────────────────
async function fetchTasksFromBackend(sortParam = null) {
  showBanner("Loading tasks…", "info");
  try {
    let url = `${API_BASE_URL}/tasks`;
    if (sortParam) url += `?sort=${encodeURIComponent(sortParam)}`;

    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const tasks = await response.json();
    renderTaskList(tasks);
    saveCache(tasks);
    hideBanner();
  } catch (err) {
    console.error("Error fetching tasks:", err);
    showBanner("Could not reach backend — showing cached data.", "error");
  }
}

// ── Validation helpers ───────────────────────────────────────────────────────
function clearValidationError() {
  titleError.style.display = "none";
  titleError.textContent   = "";
}

function showValidationError(msg) {
  titleError.textContent   = msg;
  titleError.style.display = "block";
}

// ── Form submit — add task ───────────────────────────────────────────────────
async function handleFormSubmit(event) {
  event.preventDefault();                          // Task 12: intercept submit

  const trimmedTitle = taskTitleInput.value.trim();

  // Task 13: client-side validation
  if (!trimmedTitle) {
    showValidationError("Task title cannot be empty or whitespace only.");
    taskTitleInput.focus();
    return;
  }

  const payload = {
    title:      trimmedTitle,
    priority:   taskPrioritySelect.value,
    due_date:   taskDueDateInput.value.trim() || null,
    project_id: parseInt(projectIdInput.value, 10) || 1,
  };

  try {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });

    if (response.status === 201) {
      taskForm.reset();
      clearValidationError();
      fetchTasksFromBackend();
    } else {
      const err = await response.json();
      showValidationError(err.detail || "Failed to create task.");
    }
  } catch (err) {
    console.error("Network error creating task:", err);
    showValidationError("Unable to reach the backend server.");
  }
}

// ── AI Quick-Add ─────────────────────────────────────────────────────────────
async function handleQuickAdd() {
  const rawInput = taskTitleInput.value.trim();
  if (!rawInput) {
    showValidationError("Enter a plain-English description in the title field for AI Quick-Add.");
    taskTitleInput.focus();
    return;
  }

  const payload = {
    description: rawInput,
    project_id:  parseInt(projectIdInput.value, 10) || 1,
  };

  showBanner("AI Quick-Add parsing…", "info");
  try {
    const response = await fetch(`${API_BASE_URL}/tasks/quick-add`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });

    if (response.status === 201) {
      taskForm.reset();
      clearValidationError();
      fetchTasksFromBackend();
    } else {
      const err = await response.json();
      showValidationError(err.detail || "AI Quick-Add failed.");
      hideBanner();
    }
  } catch (err) {
    console.error("Network error on Quick-Add:", err);
    showValidationError("Unable to connect to the AI Quick-Add endpoint.");
    hideBanner();
  }
}

// ── DOM rendering — XSS-safe (Task 11) ──────────────────────────────────────
function renderTaskList(tasks) {
  taskListContainer.innerHTML = "";   // clear previous list

  if (!tasks || tasks.length === 0) {
    const empty = document.createElement("p");
    empty.className   = "empty-message";
    empty.textContent = "No tasks found. Create one above!";
    taskListContainer.appendChild(empty);
    return;
  }

  tasks.forEach(task => {
    // Card wrapper
    const card = document.createElement("div");
    card.className = `task-card priority-${task.priority}`;
    card.dataset.taskId = task.id;

    // Info section
    const infoDiv = document.createElement("div");
    infoDiv.className = "task-info";

    const titleElem = document.createElement("div");
    titleElem.className   = "task-title";
    titleElem.textContent = task.title;         // textContent — never innerHTML for user data

    const metaElem = document.createElement("div");
    metaElem.className   = "task-meta";
    metaElem.textContent =
      `Priority: ${task.priority.toUpperCase()} | ` +
      `Due: ${task.due_date || "—"} | ` +
      `Project ID: ${task.project_id}`;

    infoDiv.appendChild(titleElem);
    infoDiv.appendChild(metaElem);

    // Actions section
    const actionsDiv = document.createElement("div");
    actionsDiv.className = "task-actions";

    const editBtn = document.createElement("button");
    editBtn.className   = "btn btn-small btn-secondary";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", () => handleEditTask(task));  // Task 12

    const deleteBtn = document.createElement("button");
    deleteBtn.className   = "btn btn-small btn-danger";
    deleteBtn.textContent = "Delete";
    deleteBtn.addEventListener("click", () => handleDeleteTask(task.id));  // Task 12

    actionsDiv.appendChild(editBtn);
    actionsDiv.appendChild(deleteBtn);

    card.appendChild(infoDiv);
    card.appendChild(actionsDiv);
    taskListContainer.appendChild(card);
  });
}

// ── Delete ────────────────────────────────────────────────────────────────────
async function handleDeleteTask(taskId) {
  if (!confirm(`Delete Task #${taskId}?`)) return;

  try {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
      method: "DELETE",
    });
    if (response.ok) {
      fetchTasksFromBackend();
    } else {
      alert("Failed to delete task.");
    }
  } catch (err) {
    console.error("Error deleting task:", err);
    alert("Network error — could not delete task.");
  }
}

// ── Edit ──────────────────────────────────────────────────────────────────────
async function handleEditTask(task) {
  const newTitle = prompt("Update task title:", task.title);
  if (newTitle === null) return;          // user cancelled

  const trimmed = newTitle.trim();
  if (!trimmed) {
    alert("Title cannot be blank.");
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/tasks/${task.id}`, {
      method:  "PUT",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ title: trimmed }),
    });
    if (response.ok) {
      fetchTasksFromBackend();
    } else {
      alert("Failed to update task.");
    }
  } catch (err) {
    console.error("Error updating task:", err);
    alert("Network error — could not update task.");
  }
}

// ── Status banner helpers ─────────────────────────────────────────────────────
function showBanner(msg, type = "info") {
  statusBanner.textContent   = msg;
  statusBanner.className     = `status-banner ${type}`;
  statusBanner.style.display = "block";
}

function hideBanner() {
  statusBanner.style.display = "none";
  statusBanner.textContent   = "";
}
