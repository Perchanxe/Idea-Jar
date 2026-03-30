/**
 * Purpose:
 *     Main frontend controller for the jar-first Idea Jar app.
 *     This single file handles:
 *     - DOM lookups
 *     - shared frontend state
 *     - panel rendering
 *     - button wiring
 *     - pywebview startup flow
 *     - debug logging
 *
 * Parameters:
 *     None
 *
 * Return:
 *     None
 */

console.log("[IdeaJar] script.js loaded");

/* =========================
   DOM REFERENCES
========================= */

/**
 * Purpose:
 *     Store all DOM references in one object so the app can safely access them.
 *
 * Parameters:
 *     None
 *
 * Return:
 *     object: DOM reference map.
 */
const DOM = {
    jarPickerPanel: document.getElementById("jarPickerPanel"),
    jarPickerList: document.getElementById("jarPickerList"),
    createJarButton: document.getElementById("createJarButton"),
    completedIdeasButton: document.getElementById("completedIdeasButton"),

    jarPanel: document.getElementById("jarPanel"),
    jarPanelTitle: document.getElementById("jarPanelTitle"),
    jarMessage: document.getElementById("jarMessage"),
    pickButton: document.getElementById("pickButton"),
    createIdeaButton: document.getElementById("createIdeaButton"),
    jarExploreJarsButton: document.getElementById("jarExploreJarsButton"),

    taskPanel: document.getElementById("taskPanel"),
    taskPanelTitle: document.getElementById("taskPanelTitle"),
    taskList: document.getElementById("taskList"),

    subtaskPanel: document.getElementById("subtaskPanel"),
    subtaskPanelTitle: document.getElementById("subtaskPanelTitle"),
    subtaskList: document.getElementById("subtaskList"),

    completedJarPanel: document.getElementById("completedJarPanel"),
    completedJarTitle: document.getElementById("completedJarTitle"),
    completedJarCount: document.getElementById("completedJarCount"),
    completedJarList: document.getElementById("completedJarList"),

    completedAllPanel: document.getElementById("completedAllPanel"),
    completedAllCount: document.getElementById("completedAllCount"),
    completedAllList: document.getElementById("completedAllList"),

    tasksTab: document.getElementById("tasksTab"),
    completedTab: document.getElementById("completedTab"),
    createIdeaTopButton: document.getElementById("createIdeaTopButton"),
    exploreJarsButton: document.getElementById("exploreJarsButton"),

    subtasksBackButton: document.getElementById("subtasksBackButton"),
    randomTaskButton: document.getElementById("randomTaskButton"),
    randomSubtaskButton: document.getElementById("randomSubtaskButton"),
    createTaskButton: document.getElementById("createTaskButton"),

    completedJarBackButton: document.getElementById("completedJarBackButton"),
    completedAllBackButton: document.getElementById("completedAllBackButton"),
    closeButton: document.getElementById("closeButton"),

    messagePopup: document.getElementById("messagePopup"),
    messageText: document.getElementById("messageText")
};

console.log("[IdeaJar] DOM refs:", DOM);

/* =========================
   SHARED FRONTEND STATE
========================= */

/**
 * Purpose:
 *     Hold shared UI state between renders.
 *
 * Parameters:
 *     None
 *
 * Return:
 *     object: Mutable frontend state.
 */
const STATE = {
    currentJarSlug: "",
    currentTaskIndex: null,
    currentMode: "",
    currentProjectName: "",
    messageTimeout: null
};

/* =========================
   GENERAL HELPERS
========================= */

/**
 * Purpose:
 *     Print debug logs with a consistent prefix.
 *
 * Parameters:
 *     ...args (any): Values to log.
 *
 * Return:
 *     None
 */
function debugLog(...args) {
    console.log("[IdeaJar]", ...args);
}

/**
 * Purpose:
 *     Print debug errors with a consistent prefix.
 *
 * Parameters:
 *     ...args (any): Values to log.
 *
 * Return:
 *     None
 */
function debugError(...args) {
    console.error("[IdeaJar]", ...args);
}

/**
 * Purpose:
 *     Resize the pywebview window around a target element.
 *
 * Parameters:
 *     element (HTMLElement): The element to size around.
 *     extraWidth (number): Extra width padding.
 *     extraHeight (number): Extra height padding.
 *     minWidth (number): Minimum width.
 *     minHeight (number): Minimum height.
 *
 * Return:
 *     None
 */
function resizeToElement(element, extraWidth = 40, extraHeight = 70, minWidth = 260, minHeight = 270) {
    if (!element) {
        debugError("resizeToElement called with missing element");
        return;
    }

    if (!window.pywebview?.api?.resize_window) {
        debugError("pywebview resize_window API missing");
        return;
    }

    const width = Math.max(minWidth, Math.ceil(element.offsetWidth + extraWidth));
    const height = Math.max(minHeight, Math.ceil(element.offsetHeight + extraHeight));

    debugLog("Resizing window", { width, height });
    window.pywebview.api.resize_window(width, height);
}

/**
 * Purpose:
 *     Hide all main content panels.
 *
 * Parameters:
 *     None
 *
 * Return:
 *     None
 */
function hideAllPanels() {
    [
        DOM.jarPickerPanel,
        DOM.jarPanel,
        DOM.taskPanel,
        DOM.subtaskPanel,
        DOM.completedJarPanel,
        DOM.completedAllPanel
    ].forEach((panel) => {
        if (panel) {
            panel.classList.add("hidden");
        }
    });
}

/**
 * Purpose:
 *     Hide the floating message popup.
 *
 * Parameters:
 *     None
 *
 * Return:
 *     None
 */
function hideMessage() {
    if (DOM.messagePopup) {
        DOM.messagePopup.classList.add("hidden");
    }

    if (DOM.messageText) {
        DOM.messageText.textContent = "";
    }

    if (STATE.messageTimeout) {
        clearTimeout(STATE.messageTimeout);
        STATE.messageTimeout = null;
    }
}

/**
 * Purpose:
 *     Show the floating message popup with temporary text.
 *
 * Parameters:
 *     text (string): Message text.
 *
 * Return:
 *     None
 */
function showMessage(text) {
    if (!text || !DOM.messagePopup || !DOM.messageText) return;

    debugLog("Message:", text);

    DOM.messageText.textContent = text;
    DOM.messagePopup.classList.remove("hidden");

    if (STATE.messageTimeout) {
        clearTimeout(STATE.messageTimeout);
    }

    STATE.messageTimeout = setTimeout(() => {
        hideMessage();
    }, 10000);
}

/**
 * Purpose:
 *     Normalize freeform user text into a trimmed string.
 *
 * Parameters:
 *     value (any): Input value.
 *
 * Return:
 *     string: Trimmed string.
 */
function normalizeText(value) {
    return String(value ?? "").trim();
}

/**
 * Purpose:
 *     Prompt for a non-empty string.
 *
 * Parameters:
 *     message (string): Prompt message.
 *     defaultValue (string): Default prompt value.
 *
 * Return:
 *     string | null: Cleaned text or null.
 */
function promptNonEmpty(message, defaultValue = "") {
    const raw = prompt(message, defaultValue);
    if (raw === null) return null;

    const cleaned = normalizeText(raw);
    if (!cleaned) return null;

    return cleaned;
}

/**
 * Purpose:
 *     Create a text button element.
 *
 * Parameters:
 *     text (string): Button label.
 *     className (string): CSS class string.
 *     ariaLabel (string): Accessible label.
 *
 * Return:
 *     HTMLButtonElement: Created button.
 */
function createTextButton(text, className = "", ariaLabel = "") {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = text;

    if (className) {
        button.className = className;
    }

    if (ariaLabel) {
        button.setAttribute("aria-label", ariaLabel);
    }

    return button;
}

/**
 * Purpose:
 *     Create a checkbox-style button.
 *
 * Parameters:
 *     isChecked (boolean): Whether the box is checked.
 *     ariaLabel (string): Accessible label.
 *
 * Return:
 *     HTMLButtonElement: Created checkbox button.
 */
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

/**
 * Purpose:
 *     Create a delete button.
 *
 * Parameters:
 *     ariaLabel (string): Accessible label.
 *
 * Return:
 *     HTMLButtonElement: Created delete button.
 */
function createDeleteButton(ariaLabel = "Delete") {
    const button = document.createElement("button");
    button.className = "deleteButton";
    button.type = "button";
    button.setAttribute("aria-label", ariaLabel);
    button.textContent = "✕";
    return button;
}

/* =========================
   INPUT FLOWS
========================= */

/**
 * Purpose:
 *     Prompt the user for a new jar name.
 *
 * Parameters:
 *     None
 *
 * Return:
 *     Promise<string | null>: Jar name or null.
 */
async function promptForJarName() {
    return promptNonEmpty("Jar name?");
}

/**
 * Purpose:
 *     Prompt the user for a new idea plus its initial tasks/subtasks.
 *
 * Parameters:
 *     None
 *
 * Return:
 *     Promise<object | null>:
 *         { projectName, tasks } or null.
 */
async function promptForIdeaData() {
    const projectName = promptNonEmpty("Project Name?");
    if (!projectName) return null;

    const tasks = [];

    while (true) {
        const taskName = promptNonEmpty("Add Task");
        if (!taskName) break;

        const subtasks = [];

        while (true) {
            const subtaskName = promptNonEmpty(`Subtasks for "${taskName}" (Cancel to finish subtasks)`);
            if (!subtaskName) break;
            subtasks.push(subtaskName);
        }

        if (subtasks.length === 0) {
            showMessage(`Task "${taskName}" needs at least 1 subtask`);
            return null;
        }

        tasks.push({
            name: taskName,
            subtasks
        });
    }

    if (tasks.length === 0) {
        showMessage("You need at least 1 task");
        return null;
    }

    return {
        projectName,
        tasks
    };
}

/**
 * Purpose:
 *     Prompt the user for a new task plus its subtasks.
 *
 * Parameters:
 *     None
 *
 * Return:
 *     Promise<object | null>:
 *         { taskName, subtasks } or null.
 */
async function promptForTaskData() {
    const taskName = promptNonEmpty("Task name?");
    if (!taskName) return null;

    const subtasks = [];

    while (true) {
        const subtaskName = promptNonEmpty(`Subtasks for "${taskName}" (Cancel to finish subtasks)`);
        if (!subtaskName) break;
        subtasks.push(subtaskName);
    }

    if (subtasks.length === 0) {
        showMessage("A task needs at least 1 subtask");
        return null;
    }

    return {
        taskName,
        subtasks
    };
}

/* =========================
   PANEL RENDERERS
========================= */

/**
 * Purpose:
 *     Render the jar picker screen.
 *
 * Parameters:
 *     state (object): Backend state for jarPicker mode.
 *
 * Return:
 *     None
 */
function showJarPickerPanel(state) {
    debugLog("Rendering jarPicker", state);

    hideAllPanels();

    STATE.currentMode = "jarPicker";
    STATE.currentJarSlug = "";
    STATE.currentTaskIndex = null;
    STATE.currentProjectName = "";

    if (!DOM.jarPickerPanel || !DOM.jarPickerList) {
        debugError("jarPickerPanel or jarPickerList missing");
        return;
    }

    DOM.jarPickerPanel.classList.remove("hidden");
    DOM.jarPickerList.innerHTML = "";

    (state.jars || []).forEach((jar) => {
        const item = document.createElement("div");
        item.className = "jarPickerItem";

        const openButton = createTextButton(
            `${jar.name} (${jar.ideasCount} ideas / ${jar.inProgressCount} active / ${jar.completedCount} completed)`,
            "jarPickerButton",
            `Open jar ${jar.name}`
        );

        openButton.addEventListener("click", async () => {
            debugLog("Opening jar", jar.slug);
            const newState = await window.pywebview.api.open_jar(jar.slug);
            await handleState(newState);
        });

        item.appendChild(openButton);
        DOM.jarPickerList.appendChild(item);
    });

    setTimeout(() => {
        resizeToElement(DOM.jarPickerPanel, 40, 55, 360, 260);
    }, 10);

    if (state.message) {
        showMessage(state.message);
    }
}

/**
 * Purpose:
 *     Render the jar screen for a selected jar.
 *
 * Parameters:
 *     state (object): Backend state for jar mode.
 *
 * Return:
 *     None
 */
function showJarPanel(state) {
    debugLog("Rendering jar", state);

    hideAllPanels();

    STATE.currentMode = "jar";
    STATE.currentJarSlug = state.jarSlug || "";
    STATE.currentTaskIndex = null;
    STATE.currentProjectName = "";

    if (!DOM.jarPanel) {
        debugError("jarPanel missing");
        return;
    }

    DOM.jarPanel.classList.remove("hidden");

    if (DOM.jarPanelTitle) {
        DOM.jarPanelTitle.textContent = state.jarName || "Jar";
    }

    if (DOM.jarMessage) {
        DOM.jarMessage.textContent = state.ideasCount > 0
            ? `${state.ideasCount} idea(s) available`
            : "There are no ideas";
    }

    setTimeout(() => {
        resizeToElement(DOM.jarPanel, 40, 55, 320, 240);
    }, 10);

    if (state.message) {
        showMessage(state.message);
    }
}

/**
 * Purpose:
 *     Render the active project task screen.
 *
 * Parameters:
 *     state (object): Backend state for tasks mode.
 *
 * Return:
 *     None
 */
function showTaskPanel(state) {
    debugLog("Rendering tasks", state);

    hideAllPanels();

    STATE.currentMode = "tasks";
    STATE.currentJarSlug = state.jarSlug || "";
    STATE.currentTaskIndex = null;
    STATE.currentProjectName = state.projectName || "";

    if (!DOM.taskPanel || !DOM.taskList) {
        debugError("taskPanel or taskList missing");
        return;
    }

    DOM.taskPanel.classList.remove("hidden");
    DOM.taskList.innerHTML = "";

    if (DOM.taskPanelTitle) {
        DOM.taskPanelTitle.textContent = state.projectName || "Project";
    }

    (state.tasks || []).forEach((task, taskIndex) => {
        const taskItem = document.createElement("div");
        taskItem.className = "taskItem";

        const row = document.createElement("div");
        row.className = "taskRow";

        const checkbox = createCheckbox(task.done, `Toggle task ${task.name}`);
        checkbox.addEventListener("click", async () => {
            debugLog("Toggling task", { jarSlug: state.jarSlug, taskIndex });
            const newState = await window.pywebview.api.toggle_task(state.jarSlug, taskIndex);
            await handleState(newState);
        });

        const openButton = createTextButton(task.name, "taskButton", `Open task ${task.name}`);
        if (task.done) {
            openButton.classList.add("doneText");
        }

        openButton.addEventListener("click", async () => {
            debugLog("Opening task", { jarSlug: state.jarSlug, taskIndex });
            const newState = await window.pywebview.api.open_task(state.jarSlug, taskIndex);
            await handleState(newState);
        });

        const renameButton = createTextButton("Rename", "renameButton", `Rename task ${task.name}`);
        renameButton.addEventListener("click", async () => {
            const newName = promptNonEmpty("Rename task", task.name);
            if (!newName) return;

            debugLog("Renaming task", { jarSlug: state.jarSlug, taskIndex, newName });
            const newState = await window.pywebview.api.rename_task(state.jarSlug, taskIndex, newName);
            await handleState(newState);
        });

        row.appendChild(checkbox);
        row.appendChild(openButton);
        row.appendChild(renameButton);

        if ((state.tasks || []).length > 1) {
            const deleteButton = createDeleteButton(`Delete task ${task.name}`);
            deleteButton.addEventListener("click", async () => {
                if (!confirm("Delete this task?")) return;

                debugLog("Deleting task", { jarSlug: state.jarSlug, taskIndex });
                const newState = await window.pywebview.api.delete_task(state.jarSlug, taskIndex);
                await handleState(newState);
            });

            row.appendChild(deleteButton);
        }

        taskItem.appendChild(row);
        DOM.taskList.appendChild(taskItem);
    });

    setTimeout(() => {
        resizeToElement(DOM.taskPanel, 40, 55, 420, 260);
    }, 10);

    if (state.message) {
        showMessage(state.message);
    }
}

/**
 * Purpose:
 *     Render the subtasks screen for a selected task.
 *
 * Parameters:
 *     state (object): Backend state for subtasks mode.
 *
 * Return:
 *     None
 */
function showSubtaskPanel(state) {
    debugLog("Rendering subtasks", state);

    hideAllPanels();

    STATE.currentMode = "subtasks";
    STATE.currentJarSlug = state.jarSlug || "";
    STATE.currentTaskIndex = state.taskIndex ?? null;
    STATE.currentProjectName = state.projectName || "";

    if (!DOM.subtaskPanel || !DOM.subtaskList) {
        debugError("subtaskPanel or subtaskList missing");
        return;
    }

    DOM.subtaskPanel.classList.remove("hidden");
    DOM.subtaskList.innerHTML = "";

    if (DOM.subtaskPanelTitle) {
        DOM.subtaskPanelTitle.textContent = state.taskName || "Subtasks";
    }

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
            debugLog("Toggling subtask", {
                jarSlug: state.jarSlug,
                taskIndex: state.taskIndex,
                subtaskIndex
            });

            const newState = await window.pywebview.api.toggle_subtask(
                state.jarSlug,
                state.taskIndex,
                subtaskIndex
            );

            await handleState(newState);
        });

        const nameButton = createTextButton(subtask.name, "taskButton", `Toggle subtask ${subtask.name}`);
        if (subtask.done) {
            nameButton.classList.add("doneText");
        }
        if (state.highlightSubtask && state.highlightSubtask === subtask.name) {
            nameButton.classList.add("highlighted");
        }

        nameButton.addEventListener("click", async () => {
            debugLog("Toggling subtask through text button", {
                jarSlug: state.jarSlug,
                taskIndex: state.taskIndex,
                subtaskIndex
            });

            const newState = await window.pywebview.api.toggle_subtask(
                state.jarSlug,
                state.taskIndex,
                subtaskIndex
            );

            await handleState(newState);
        });

        const renameButton = createTextButton("Rename", "renameButton", `Rename subtask ${subtask.name}`);
        renameButton.addEventListener("click", async () => {
            const newName = promptNonEmpty("Rename subtask", subtask.name);
            if (!newName) return;

            debugLog("Renaming subtask", {
                jarSlug: state.jarSlug,
                taskIndex: state.taskIndex,
                subtaskIndex,
                newName
            });

            const newState = await window.pywebview.api.rename_subtask(
                state.jarSlug,
                state.taskIndex,
                subtaskIndex,
                newName
            );

            await handleState(newState);
        });

        row.appendChild(checkbox);
        row.appendChild(nameButton);
        row.appendChild(renameButton);

        if ((state.subtasks || []).length > 1) {
            const deleteButton = createDeleteButton(`Delete subtask ${subtask.name}`);
            deleteButton.addEventListener("click", async () => {
                if (!confirm("Delete this subtask?")) return;

                debugLog("Deleting subtask", {
                    jarSlug: state.jarSlug,
                    taskIndex: state.taskIndex,
                    subtaskIndex
                });

                const newState = await window.pywebview.api.delete_subtask(
                    state.jarSlug,
                    state.taskIndex,
                    subtaskIndex
                );

                await handleState(newState);
            });

            row.appendChild(deleteButton);
        }

        subtaskItem.appendChild(row);
        DOM.subtaskList.appendChild(subtaskItem);
    });

    setTimeout(() => {
        resizeToElement(DOM.subtaskPanel, 40, 55, 420, 260);
    }, 10);

    if (state.message) {
        showMessage(state.message);
    }
}

/**
 * Purpose:
 *     Render completed ideas for the current jar.
 *
 * Parameters:
 *     state (object): Backend state for completedJar mode.
 *
 * Return:
 *     None
 */
function showCompletedJarPanel(state) {
    debugLog("Rendering completedJar", state);

    hideAllPanels();

    STATE.currentMode = "completedJar";
    STATE.currentJarSlug = state.jarSlug || "";

    if (!DOM.completedJarPanel || !DOM.completedJarList) {
        debugError("completedJarPanel or completedJarList missing");
        return;
    }

    DOM.completedJarPanel.classList.remove("hidden");
    DOM.completedJarList.innerHTML = "";

    if (DOM.completedJarTitle) {
        DOM.completedJarTitle.textContent = state.jarName || "Completed";
    }

    if (DOM.completedJarCount) {
        DOM.completedJarCount.textContent = `Completed ideas: ${state.count || 0}`;
    }

    (state.projects || []).forEach((project) => {
        const item = document.createElement("div");
        item.className = "taskItem";

        const title = document.createElement("div");
        title.className = "completedProjectName";
        title.textContent = project.name || "Untitled";

        item.appendChild(title);
        DOM.completedJarList.appendChild(item);
    });

    setTimeout(() => {
        resizeToElement(DOM.completedJarPanel, 40, 55, 380, 250);
    }, 10);

    if (state.message) {
        showMessage(state.message);
    }
}

/**
 * Purpose:
 *     Render completed ideas across all jars.
 *
 * Parameters:
 *     state (object): Backend state for completedAll mode.
 *
 * Return:
 *     None
 */
function showCompletedAllPanel(state) {
    debugLog("Rendering completedAll", state);

    hideAllPanels();

    STATE.currentMode = "completedAll";

    if (!DOM.completedAllPanel || !DOM.completedAllList) {
        debugError("completedAllPanel or completedAllList missing");
        return;
    }

    DOM.completedAllPanel.classList.remove("hidden");
    DOM.completedAllList.innerHTML = "";

    if (DOM.completedAllCount) {
        DOM.completedAllCount.textContent = `Completed ideas: ${state.count || 0}`;
    }

    (state.projects || []).forEach((project) => {
        const item = document.createElement("div");
        item.className = "taskItem";

        const title = document.createElement("div");
        title.className = "completedProjectName";
        title.textContent = `${project.name || "Untitled"} — ${project.jarName || "Unknown Jar"}`;

        item.appendChild(title);
        DOM.completedAllList.appendChild(item);
    });

    setTimeout(() => {
        resizeToElement(DOM.completedAllPanel, 40, 55, 420, 260);
    }, 10);

    if (state.message) {
        showMessage(state.message);
    }
}

/**
 * Purpose:
 *     Route backend state into the correct UI renderer.
 *
 * Parameters:
 *     state (object): Backend state object.
 *
 * Return:
 *     Promise<void>
 */
async function handleState(state) {
    debugLog("handleState called", state);

    if (!state) {
        debugError("handleState received empty state");
        return;
    }

    if (state.mode === "jarPicker") {
        showJarPickerPanel(state);
        return;
    }

    if (state.mode === "jar") {
        showJarPanel(state);
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

    if (state.mode === "completedJar") {
        showCompletedJarPanel(state);
        return;
    }

    if (state.mode === "completedAll") {
        showCompletedAllPanel(state);
        return;
    }

    debugError("Unknown state mode:", state.mode, state);
}

/* =========================
   EVENT WIRING
========================= */

/**
 * Purpose:
 *     Attach all event listeners safely.
 *
 * Parameters:
 *     None
 *
 * Return:
 *     None
 */
function bindEvents() {
    debugLog("Binding events");

    DOM.createJarButton?.addEventListener("click", async () => {
        const jarName = await promptForJarName();
        if (!jarName) return;

        debugLog("Creating jar", jarName);
        const result = await window.pywebview.api.create_jar(jarName);

        if (result?.message) {
            showMessage(result.message);
        }

        const state = await window.pywebview.api.get_startup_state();
        await handleState(state);
    });

    DOM.completedIdeasButton?.addEventListener("click", async () => {
        debugLog("Opening completed ideas across all jars");
        const state = await window.pywebview.api.get_completed_all_projects();
        await handleState(state);
    });

    DOM.pickButton?.addEventListener("click", async () => {
        if (!STATE.currentJarSlug) return;

        debugLog("Picking idea from jar", STATE.currentJarSlug);
        const state = await window.pywebview.api.pick_idea(STATE.currentJarSlug);
        await handleState(state);
    });

    DOM.createIdeaButton?.addEventListener("click", async () => {
        if (!STATE.currentJarSlug) return;

        const data = await promptForIdeaData();
        if (!data) return;

        debugLog("Creating idea", data);
        const result = await window.pywebview.api.create_project(
            STATE.currentJarSlug,
            data.projectName,
            data.tasks
        );

        if (result?.message) {
            showMessage(result.message);
        }

        const state = await window.pywebview.api.open_jar(STATE.currentJarSlug);
        await handleState(state);
    });

    DOM.jarExploreJarsButton?.addEventListener("click", async () => {
        debugLog("Exploring other jars from jar screen");
        const state = await window.pywebview.api.get_jar_picker_state();
        await handleState(state);
    });

    DOM.createIdeaTopButton?.addEventListener("click", async () => {
        if (!STATE.currentJarSlug) return;

        const data = await promptForIdeaData();
        if (!data) return;

        debugLog("Creating idea from top button", data);
        const result = await window.pywebview.api.create_project(
            STATE.currentJarSlug,
            data.projectName,
            data.tasks
        );

        if (result?.message) {
            showMessage(result.message);
        }

        const state = await window.pywebview.api.open_jar(STATE.currentJarSlug);
        await handleState(state);
    });

    DOM.createTaskButton?.addEventListener("click", async () => {
        if (!STATE.currentJarSlug) return;

        const data = await promptForTaskData();
        if (!data) return;

        debugLog("Creating task", data);
        const state = await window.pywebview.api.create_task(
            STATE.currentJarSlug,
            data.taskName,
            data.subtasks
        );

        await handleState(state);
    });

    DOM.randomTaskButton?.addEventListener("click", async () => {
        if (!STATE.currentJarSlug) return;

        debugLog("Picking random task", STATE.currentJarSlug);
        const state = await window.pywebview.api.pick_random_task(STATE.currentJarSlug);
        await handleState(state);
    });

    DOM.randomSubtaskButton?.addEventListener("click", async () => {
        if (!STATE.currentJarSlug || STATE.currentTaskIndex === null) return;

        debugLog("Picking random subtask", {
            jarSlug: STATE.currentJarSlug,
            taskIndex: STATE.currentTaskIndex
        });

        const state = await window.pywebview.api.pick_random_subtask(
            STATE.currentJarSlug,
            STATE.currentTaskIndex
        );

        await handleState(state);
    });

    DOM.tasksTab?.addEventListener("click", async () => {
        if (!STATE.currentJarSlug) return;

        debugLog("Opening tasks tab", STATE.currentJarSlug);
        const state = await window.pywebview.api.open_jar(STATE.currentJarSlug);
        await handleState(state);
    });

    DOM.completedTab?.addEventListener("click", async () => {
        if (!STATE.currentJarSlug) return;

        debugLog("Opening completed tab for jar", STATE.currentJarSlug);
        const state = await window.pywebview.api.get_completed_projects_for_jar(STATE.currentJarSlug);
        await handleState(state);
    });

    DOM.exploreJarsButton?.addEventListener("click", async () => {
        debugLog("Exploring other jars");
        const state = await window.pywebview.api.get_jar_picker_state();
        await handleState(state);
    });

    DOM.subtasksBackButton?.addEventListener("click", async () => {
        if (!STATE.currentJarSlug) return;

        debugLog("Returning from subtasks to jar open state", STATE.currentJarSlug);
        const state = await window.pywebview.api.open_jar(STATE.currentJarSlug);
        await handleState(state);
    });

    DOM.completedJarBackButton?.addEventListener("click", async () => {
        if (!STATE.currentJarSlug) {
            const state = await window.pywebview.api.get_startup_state();
            await handleState(state);
            return;
        }

        debugLog("Returning from completedJar to current jar", STATE.currentJarSlug);
        const state = await window.pywebview.api.open_jar(STATE.currentJarSlug);
        await handleState(state);
    });

    DOM.completedAllBackButton?.addEventListener("click", async () => {
        debugLog("Returning from completedAll to startup");
        const state = await window.pywebview.api.get_startup_state();
        await handleState(state);
    });

    DOM.closeButton?.addEventListener("click", async () => {
        debugLog("Closing app");
        await window.pywebview.api.close_app();
    });

    DOM.messagePopup?.addEventListener("click", () => {
        hideMessage();
    });
}

/* =========================
   STARTUP
========================= */

window.addEventListener("pywebviewready", async () => {
    /**
     * Purpose:
     *     Start the frontend once pywebview is ready.
     *
     * Parameters:
     *     None
     *
     * Return:
     *     Promise<void>
     */
    debugLog("pywebviewready fired");

    try {
        bindEvents();

        const startupState = await window.pywebview.api.get_startup_state();
        debugLog("Startup state received", startupState);

        await handleState(startupState);
    } catch (error) {
        debugError("Startup failure", error);
        showMessage(`Startup error: ${error}`);
    }
});