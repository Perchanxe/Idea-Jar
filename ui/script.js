const pickButton = document.getElementById("pickButton");
const closeButton = document.getElementById("closeButton");
const createIdeaButton = document.getElementById("createIdeaButton");
const createTaskButton = document.getElementById("createTaskButton");
const backButton = document.getElementById("backButton");

const randomTaskButton = document.getElementById("randomTaskButton");
const randomSubtaskButton = document.getElementById("randomSubtaskButton");

const tasksTab = document.getElementById("tasksTab");
const completedTab = document.getElementById("completedTab");
const subtasksTasksTab = document.getElementById("subtasksTasksTab");
const subtasksCompletedTab = document.getElementById("subtasksCompletedTab");
const completedTasksTab = document.getElementById("completedTasksTab");
const completedBackButton = document.getElementById("completedBackButton");

const taskPanel = document.getElementById("taskPanel");
const subtaskPanel = document.getElementById("subtaskPanel");
const completedPanel = document.getElementById("completedPanel");

const taskPanelTitle = document.getElementById("taskPanelTitle");
const taskList = document.getElementById("taskList");

const subtaskPanelTitle = document.getElementById("subtaskPanelTitle");
const subtaskList = document.getElementById("subtaskList");

const completedCount = document.getElementById("completedCount");
const completedList = document.getElementById("completedList");

const messagePopup = document.getElementById("messagePopup");
const messageText = document.getElementById("messageText");

let currentSubtaskTaskIndex = null;

function resizeToElement(element, extraWidth = 40, extraHeight = 70, minWidth = 240, minHeight = 240) {
    const width = Math.max(minWidth, Math.ceil(element.offsetWidth + extraWidth));
    const height = Math.max(minHeight, Math.ceil(element.offsetHeight + extraHeight));
    window.pywebview.api.resize_window(width, height);
}

function hideAllPanels() {
    taskPanel.classList.add("hidden");
    subtaskPanel.classList.add("hidden");
    completedPanel.classList.add("hidden");
    messagePopup.classList.add("hidden");
}

function showMessage(text) {
    messageText.textContent = text;
    messagePopup.classList.remove("hidden");
}

function showJarMode() {
    hideAllPanels();

    pickButton.classList.remove("hidden");
    pickButton.classList.remove("disabled");
    createIdeaButton.classList.remove("hidden");

    setTimeout(() => {
        resizeToElement(document.querySelector(".jarContainer"), 30, 30, 240, 240);
    }, 10);
}

function showTaskPanel(state) {
    hideAllPanels();

    pickButton.classList.add("hidden");
    createIdeaButton.classList.add("hidden");

    taskPanel.classList.remove("hidden");
    taskPanelTitle.textContent = state.projectName || "Project";
    taskList.innerHTML = "";

    (state.tasks || []).forEach((task, taskIndex) => {
        const taskItem = document.createElement("div");
        taskItem.className = "taskItem";

        const row = document.createElement("div");
        row.className = "taskRow";

        const openButton = document.createElement("button");
        openButton.className = "taskButton";
        openButton.textContent = task.done ? `✅ ${task.name}` : `⬜ ${task.name}`;

        if (state.highlightTask && state.highlightTask === task.name) {
            openButton.classList.add("highlighted");
        }

        openButton.addEventListener("click", async () => {
            const newState = await window.pywebview.api.open_task(taskIndex);
            handleState(newState);
        });

        const deleteButton = document.createElement("button");
        deleteButton.className = "deleteButton";
        deleteButton.textContent = "✕";

        deleteButton.addEventListener("click", async () => {
            if (!confirm("Delete this task?")) return;
            const newState = await window.pywebview.api.delete_task(taskIndex);
            handleState(newState);
        });

        row.appendChild(openButton);
        row.appendChild(deleteButton);

        taskItem.appendChild(row);
        taskList.appendChild(taskItem);
    });

    setTimeout(() => {
        resizeToElement(taskPanel, 40, 55, 320, 180);
    }, 10);
}

function showSubtaskPanel(state) {
    hideAllPanels();

    pickButton.classList.add("hidden");
    createIdeaButton.classList.add("hidden");

    subtaskPanel.classList.remove("hidden");
    subtaskPanelTitle.textContent = state.taskName || "Subtasks";
    subtaskList.innerHTML = "";
    currentSubtaskTaskIndex = state.taskIndex;

    (state.subtasks || []).forEach((subtask, subtaskIndex) => {
        const subtaskItem = document.createElement("div");
        subtaskItem.className = "taskItem";

        const row = document.createElement("div");
        row.className = "taskRow";

        const subtaskButton = document.createElement("button");
        subtaskButton.className = "taskButton";
        subtaskButton.textContent = subtask.done ? `✅ ${subtask.name}` : `⬜ ${subtask.name}`;

        if (state.highlightSubtask && state.highlightSubtask === subtask.name) {
            subtaskButton.classList.add("highlighted");
        }

        subtaskButton.addEventListener("click", async () => {
            const newState = await window.pywebview.api.toggle_subtask(
                state.taskIndex,
                subtaskIndex
            );
            handleState(newState);
        });

        const deleteButton = document.createElement("button");
        deleteButton.className = "deleteButton";
        deleteButton.textContent = "✕";

        deleteButton.addEventListener("click", async () => {
            if (!confirm("Delete this subtask?")) return;
            const newState = await window.pywebview.api.delete_subtask(
                state.taskIndex,
                subtaskIndex
            );
            handleState(newState);
        });

        row.appendChild(subtaskButton);
        row.appendChild(deleteButton);

        subtaskItem.appendChild(row);
        subtaskList.appendChild(subtaskItem);
    });

    setTimeout(() => {
        resizeToElement(subtaskPanel, 40, 55, 320, 180);
    }, 10);
}

function showCompletedPanel(state) {
    hideAllPanels();

    pickButton.classList.add("hidden");
    createIdeaButton.classList.add("hidden");

    completedPanel.classList.remove("hidden");
    completedCount.textContent = `Completed projects: ${state.count}`;
    completedList.innerHTML = "";

    (state.projects || []).forEach(name => {
        const item = document.createElement("div");
        item.className = "taskItem";
        item.textContent = name;
        completedList.appendChild(item);
    });

    setTimeout(() => {
        resizeToElement(completedPanel, 40, 55, 320, 180);
    }, 10);
}

function handleState(state) {
    if (!state) return;

    if (state.mode === "jar") {
        showJarMode();
        if (state.message) showMessage(state.message);
        return;
    }

    if (state.mode === "tasks") {
        showTaskPanel(state);
        if (state.message) showMessage(state.message);
        return;
    }

    if (state.mode === "subtasks") {
        showSubtaskPanel(state);
        if (state.message) showMessage(state.message);
        return;
    }

    if (state.mode === "completed") {
        showCompletedPanel(state);
        if (state.message) showMessage(state.message);
    }
}

pickButton.addEventListener("click", async () => {
    const state = await window.pywebview.api.pick_idea();
    handleState(state);
});

createIdeaButton.addEventListener("click", async () => {
    const projectName = prompt("Project Name?");
    if (!projectName || !projectName.trim()) return;

    const tasks = [];

    while (true) {
        const taskName = prompt("Add Task");
        if (!taskName || !taskName.trim()) break;

        const subtasks = [];
        while (true) {
            const subtaskName = prompt(`Subtasks for "${taskName}" (Cancel to finish subtasks)`);
            if (!subtaskName || !subtaskName.trim()) break;
            subtasks.push(subtaskName.trim());
        }

        if (subtasks.length === 0) {
            showMessage(`Task "${taskName.trim()}" needs at least 1 subtask`);
            return;
        }

        tasks.push({
            name: taskName.trim(),
            subtasks: subtasks
        });
    }

    if (tasks.length === 0) {
        showMessage("You need at least 1 task");
        return;
    }

    const response = await window.pywebview.api.create_project(projectName.trim(), tasks);

    if (response.message) {
        showMessage(response.message);
    }
});

createTaskButton.addEventListener("click", async () => {
    const taskName = prompt("Task name?");
    if (!taskName || !taskName.trim()) return;

    const subtasks = [];
    while (true) {
        const subtaskName = prompt(`Subtasks for "${taskName}" (Cancel to finish subtasks)`);
        if (!subtaskName || !subtaskName.trim()) break;
        subtasks.push(subtaskName.trim());
    }

    if (subtasks.length === 0) {
        showMessage("A task needs at least 1 subtask");
        return;
    }

    const newState = await window.pywebview.api.create_task(taskName.trim(), subtasks);
    handleState(newState);
});

randomTaskButton.addEventListener("click", async () => {
    const state = await window.pywebview.api.pick_random_task();
    handleState(state);
});

randomSubtaskButton.addEventListener("click", async () => {
    if (currentSubtaskTaskIndex === null) return;
    const state = await window.pywebview.api.pick_random_subtask(currentSubtaskTaskIndex);
    handleState(state);
});

backButton.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_startup_state();
    handleState(state);
});

completedBackButton.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_startup_state();
    handleState(state);
});

closeButton.addEventListener("click", async () => {
    await window.pywebview.api.close_app();
});

tasksTab.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_startup_state();
    handleState(state);
});

completedTab.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_completed_projects();
    handleState(state);
});

subtasksTasksTab.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_startup_state();
    handleState(state);
});

subtasksCompletedTab.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_completed_projects();
    handleState(state);
});

completedTasksTab.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_startup_state();
    handleState(state);
});

window.addEventListener("pywebviewready", async () => {
    const startupState = await window.pywebview.api.get_startup_state();
    handleState(startupState);
});