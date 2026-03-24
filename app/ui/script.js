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

const jarControls = document.getElementById("jarControls");
const jarTagFilter = document.getElementById("jarTagFilter");
const projectTagsList = document.getElementById("projectTagsList");
const subtaskProjectTagsList = document.getElementById("subtaskProjectTagsList");
const editTagsButton = document.getElementById("editTagsButton");

let currentSubtaskTaskIndex = null;
let availableTagsCache = [];
let selectedJarTag = "";
let messageTimeout = null;

function resizeToElement(element, extraWidth = 40, extraHeight = 70, minWidth = 240, minHeight = 240) {
    const width = Math.max(minWidth, Math.ceil(element.offsetWidth + extraWidth));
    const height = Math.max(minHeight, Math.ceil(element.offsetHeight + extraHeight));
    window.pywebview.api.resize_window(width, height);
}

function hideAllPanels() {
    taskPanel.classList.add("hidden");
    subtaskPanel.classList.add("hidden");
    completedPanel.classList.add("hidden");
}

function hideMessage() {
    messagePopup.classList.add("hidden");
    messageText.textContent = "";

    if (messageTimeout) {
        clearTimeout(messageTimeout);
        messageTimeout = null;
    }
}

function showMessage(text) {
    if (!text) return;

    messageText.textContent = text;
    messagePopup.classList.remove("hidden");

    if (messageTimeout) {
        clearTimeout(messageTimeout);
    }

    messageTimeout = setTimeout(() => {
        hideMessage();
    }, 10000);
}

function normalizeTag(tag) {
    if (tag === null || tag === undefined) return "";
    let value = String(tag).trim().toLowerCase();
    if (!value) return "";
    if (!value.startsWith("#")) {
        value = `#${value}`;
    }
    return value;
}

function parseTagsInput(rawText) {
    if (!rawText || !rawText.trim()) {
        return [];
    }

    const parts = rawText
        .split(",")
        .map((tag) => normalizeTag(tag))
        .filter(Boolean);

    return [...new Set(parts)];
}

function tagsToPromptText(tags) {
    return (tags || []).join(", ");
}

function updateAvailableTags(tags) {
    availableTagsCache = Array.isArray(tags) ? [...tags] : [];

    const previousValue = selectedJarTag || jarTagFilter.value || "";

    jarTagFilter.innerHTML = "";

    const allOption = document.createElement("option");
    allOption.value = "";
    allOption.textContent = "All Ideas";
    jarTagFilter.appendChild(allOption);

    availableTagsCache.forEach((tag) => {
        const option = document.createElement("option");
        option.value = tag;
        option.textContent = tag;
        jarTagFilter.appendChild(option);
    });

    if (availableTagsCache.includes(previousValue)) {
        jarTagFilter.value = previousValue;
        selectedJarTag = previousValue;
    } else {
        jarTagFilter.value = "";
        selectedJarTag = "";
    }
}

async function refreshJarTagsFromBackend() {
    try {
        const tagResponse = await window.pywebview.api.get_available_tags();
        const registryTags = Array.isArray(tagResponse?.tags) ? tagResponse.tags : [];
        const validTags = [];

        for (const rawTag of registryTags) {
            const tag = normalizeTag(rawTag);
            if (!tag) continue;

            try {
                const result = await window.pywebview.api.get_ideas_by_tag(tag);
                if (result && result.count > 0) {
                    validTags.push(tag);
                }
            } catch (error) {
                console.error(`Failed checking tag ${tag}:`, error);
            }
        }

        updateAvailableTags(validTags);
    } catch (error) {
        console.error("Failed to refresh tags:", error);
        updateAvailableTags([]);
    }
}

function renderTagList(container, tags) {
    container.innerHTML = "";

    if (!tags || tags.length === 0) {
        const empty = document.createElement("div");
        empty.className = "tagEmpty";
        empty.textContent = "No tags";
        container.appendChild(empty);
        return;
    }

    tags.forEach((tag) => {
        const chip = document.createElement("span");
        chip.className = "tagChip";
        chip.textContent = tag;
        container.appendChild(chip);
    });
}

function showJarModeLayout() {
    hideAllPanels();

    pickButton.classList.remove("hidden");
    pickButton.classList.remove("disabled");
    createIdeaButton.classList.remove("hidden");
    jarControls.classList.remove("hidden");
}

async function showJarMode(state = {}) {
    showJarModeLayout();

    await refreshJarTagsFromBackend();

    setTimeout(() => {
        resizeToElement(document.querySelector(".jarContainer"), 30, 30, 260, 270);
    }, 10);

    if (state.message) {
        showMessage(state.message);
    }
}

function createCheckbox(isChecked = false, ariaLabel = "Checkbox") {
    const checkbox = document.createElement("button");
    checkbox.className = "checkbox";
    checkbox.type = "button";
    checkbox.setAttribute("aria-label", ariaLabel);

    if (isChecked) {
        checkbox.classList.add("checked");
    }

    return checkbox;
}

function createDeleteButton(ariaLabel = "Delete") {
    const deleteButton = document.createElement("button");
    deleteButton.className = "deleteButton";
    deleteButton.type = "button";
    deleteButton.setAttribute("aria-label", ariaLabel);
    return deleteButton;
}

function createTaskToggleButton(isDone, labelText) {
    const checkbox = createCheckbox(isDone, labelText);

    checkbox.addEventListener("click", async (event) => {
        event.stopPropagation();
    });

    return checkbox;
}

function showTaskPanel(state) {
    hideAllPanels();

    pickButton.classList.add("hidden");
    createIdeaButton.classList.add("hidden");
    jarControls.classList.add("hidden");

    taskPanel.classList.remove("hidden");
    taskPanelTitle.textContent = state.projectName || "Project";
    taskList.innerHTML = "";
    renderTagList(projectTagsList, state.tags || []);

    (state.tasks || []).forEach((task, taskIndex) => {
        const taskItem = document.createElement("div");
        taskItem.className = "taskItem";

        const row = document.createElement("div");
        row.className = "taskRow";

        const statusButton = createTaskToggleButton(task.done, `Task status for ${task.name}`);

        if (state.highlightTask && state.highlightTask === task.name) {
            statusButton.classList.add("highlighted");
        }

        statusButton.addEventListener("click", async () => {
            const newState = await window.pywebview.api.toggle_task(taskIndex);
            await handleState(newState);
        });

        const openButton = document.createElement("button");
        openButton.className = "taskButton";
        openButton.type = "button";
        openButton.textContent = task.name;

        if (task.done) {
            openButton.classList.add("doneText");
        }

        if (state.highlightTask && state.highlightTask === task.name) {
            openButton.classList.add("highlighted");
        }

        openButton.addEventListener("click", async () => {
            const newState = await window.pywebview.api.open_task(taskIndex);
            await handleState(newState);
        });

        const deleteButton = createDeleteButton(`Delete task ${task.name}`);

        deleteButton.addEventListener("click", async () => {
            if (!confirm("Delete this task?")) return;
            const newState = await window.pywebview.api.delete_task(taskIndex);
            await handleState(newState);
        });

        row.appendChild(statusButton);
        row.appendChild(openButton);
        row.appendChild(deleteButton);

        taskItem.appendChild(row);
        taskList.appendChild(taskItem);
    });

    setTimeout(() => {
        resizeToElement(taskPanel, 40, 55, 340, 220);
    }, 10);

    if (state.message) {
        showMessage(state.message);
    }
}

function showSubtaskPanel(state) {
    hideAllPanels();

    pickButton.classList.add("hidden");
    createIdeaButton.classList.add("hidden");
    jarControls.classList.add("hidden");

    subtaskPanel.classList.remove("hidden");
    subtaskPanelTitle.textContent = state.taskName || "Subtasks";
    subtaskList.innerHTML = "";
    currentSubtaskTaskIndex = state.taskIndex;
    renderTagList(subtaskProjectTagsList, state.tags || []);

    (state.subtasks || []).forEach((subtask, subtaskIndex) => {
        const subtaskItem = document.createElement("div");
        subtaskItem.className = "taskItem";

        const row = document.createElement("div");
        row.className = "taskRow";

        const checkbox = createCheckbox(subtask.done, `Toggle subtask ${subtask.name}`);

        if (state.highlightSubtask && state.highlightSubtask === subtask.name) {
            checkbox.classList.add("highlighted");
        }

        checkbox.addEventListener("click", async () => {
            const newState = await window.pywebview.api.toggle_subtask(
                state.taskIndex,
                subtaskIndex
            );
            await handleState(newState);
        });

        const subtaskButton = document.createElement("button");
        subtaskButton.className = "taskButton";
        subtaskButton.type = "button";
        subtaskButton.textContent = subtask.name;

        if (subtask.done) {
            subtaskButton.classList.add("doneText");
        }

        if (state.highlightSubtask && state.highlightSubtask === subtask.name) {
            subtaskButton.classList.add("highlighted");
        }

        subtaskButton.addEventListener("click", async () => {
            const newState = await window.pywebview.api.toggle_subtask(
                state.taskIndex,
                subtaskIndex
            );
            await handleState(newState);
        });

        const deleteButton = createDeleteButton(`Delete subtask ${subtask.name}`);

        deleteButton.addEventListener("click", async () => {
            if (!confirm("Delete this subtask?")) return;
            const newState = await window.pywebview.api.delete_subtask(
                state.taskIndex,
                subtaskIndex
            );
            await handleState(newState);
        });

        row.appendChild(checkbox);
        row.appendChild(subtaskButton);
        row.appendChild(deleteButton);

        subtaskItem.appendChild(row);
        subtaskList.appendChild(subtaskItem);
    });

    setTimeout(() => {
        resizeToElement(subtaskPanel, 40, 55, 340, 220);
    }, 10);

    if (state.message) {
        showMessage(state.message);
    }
}

function showCompletedPanel(state) {
    hideAllPanels();

    pickButton.classList.add("hidden");
    createIdeaButton.classList.add("hidden");
    jarControls.classList.add("hidden");

    completedPanel.classList.remove("hidden");
    completedCount.textContent = `Completed projects: ${state.count}`;
    completedList.innerHTML = "";

    (state.projects || []).forEach((project) => {
        const item = document.createElement("div");
        item.className = "taskItem";

        const title = document.createElement("div");
        title.className = "completedProjectName";
        title.textContent = project.name || "Untitled";

        const tags = document.createElement("div");
        tags.className = "completedProjectTags";
        renderTagList(tags, project.tags || []);

        item.appendChild(title);
        item.appendChild(tags);

        completedList.appendChild(item);
    });

    setTimeout(() => {
        resizeToElement(completedPanel, 40, 55, 340, 220);
    }, 10);

    if (state.message) {
        showMessage(state.message);
    }
}

async function handleState(state) {
    if (!state) return;

    if (state.mode === "jar") {
        await showJarMode(state);
        return;
    }

    if (state.mode === "tasks") {
        showTaskPanel(state);
        return;
    }

    if (state.mode === "subtasks") {
        showSubtaskPanel(state);
        return;
    }

    if (state.mode === "completed") {
        showCompletedPanel(state);
    }
}

pickButton.addEventListener("click", async () => {
    const chosenTag = normalizeTag(jarTagFilter.value);
    selectedJarTag = chosenTag;

    const state = chosenTag
        ? await window.pywebview.api.pick_idea(chosenTag)
        : await window.pywebview.api.pick_idea();

    await handleState(state);
});

jarTagFilter.addEventListener("change", () => {
    selectedJarTag = normalizeTag(jarTagFilter.value);
});

createIdeaButton.addEventListener("click", async () => {
    const projectName = prompt("Project Name?");
    if (!projectName || !projectName.trim()) return;

    const tagInput = prompt(
        "Project tags? Use commas.\nExample: #game, #personal",
        ""
    );

    const tags = parseTagsInput(tagInput || "");
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

    for (const tag of tags) {
        await window.pywebview.api.create_tag(tag);
    }

    const response = await window.pywebview.api.create_project(projectName.trim(), tasks, tags);

    if (response.message) {
        showMessage(response.message);
    }

    await refreshJarTagsFromBackend();

    const startupState = await window.pywebview.api.get_startup_state();
    await handleState(startupState);
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
    await handleState(newState);
});

editTagsButton.addEventListener("click", async () => {
    const currentTags = Array.from(projectTagsList.querySelectorAll(".tagChip")).map((chip) => chip.textContent);

    const raw = prompt(
        "Edit project tags. Use commas.\nExample: #game, #personal",
        tagsToPromptText(currentTags)
    );

    if (raw === null) return;

    const tags = parseTagsInput(raw);

    for (const tag of tags) {
        await window.pywebview.api.create_tag(tag);
    }

    const newState = await window.pywebview.api.update_project_tags(tags);
    await refreshJarTagsFromBackend();
    await handleState(newState);
});

randomTaskButton.addEventListener("click", async () => {
    const state = await window.pywebview.api.pick_random_task();
    await handleState(state);
});

randomSubtaskButton.addEventListener("click", async () => {
    if (currentSubtaskTaskIndex === null) return;
    const state = await window.pywebview.api.pick_random_subtask(currentSubtaskTaskIndex);
    await handleState(state);
});

backButton.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_startup_state();
    await handleState(state);
});

completedBackButton.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_startup_state();
    await handleState(state);
});

closeButton.addEventListener("click", async () => {
    await window.pywebview.api.close_app();
});

messagePopup.addEventListener("click", () => {
    hideMessage();
});

tasksTab.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_startup_state();
    await handleState(state);
});

completedTab.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_completed_projects();
    await handleState(state);
});

subtasksTasksTab.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_startup_state();
    await handleState(state);
});

subtasksCompletedTab.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_completed_projects();
    await handleState(state);
});

completedTasksTab.addEventListener("click", async () => {
    const state = await window.pywebview.api.get_startup_state();
    await handleState(state);
});

window.addEventListener("pywebviewready", async () => {
    await refreshJarTagsFromBackend();

    const startupState = await window.pywebview.api.get_startup_state();
    await handleState(startupState);
});