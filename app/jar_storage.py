import json
import random
import shutil
from pathlib import Path

from app_paths import ensure_app_folders


class JarStorage:
    """
    Purpose:
        Handle all backend storage logic for jars, ideas, tasks, subtasks, and
        completed projects in the jar-first version of the app.

    Parameters:
        None

    Return:
        JarStorage: Storage manager instance.
    """

    def __init__(self):
        """
        Purpose:
            Initialize all core storage paths for the app.

        Parameters:
            None

        Return:
            None
        """
        folders = ensure_app_folders()
        self._app_root = folders["app_root"]
        self._base_folder = folders["base_folder"]
        self._jars_root = folders["jars_root"]
        self._jars_file = folders["jars_file"]

    def _safe_name(self, name: str) -> str:
        """
        Purpose:
            Convert a display name into a filesystem-safe name.

        Parameters:
            name (str): Raw name to sanitize.

        Return:
            str: Safe folder/file name.
        """
        bad_chars = '<>:"/\\|?*'
        cleaned = "".join("_" if c in bad_chars else c for c in str(name)).strip()
        return cleaned or "Untitled"

    def _normalize_text(self, value: str) -> str:
        """
        Purpose:
            Normalize simple user text input.

        Parameters:
            value (str): Input text.

        Return:
            str: Stripped text.
        """
        return str(value).strip()

    def _load_jar_registry(self) -> list:
        """
        Purpose:
            Load the saved jar registry.

        Parameters:
            None

        Return:
            list: List of jar metadata dictionaries.
        """
        if not self._jars_file.exists():
            return []

        try:
            data = json.loads(self._jars_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                cleaned = []
                seen = set()
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    name = self._normalize_text(entry.get("name", ""))
                    slug = self._normalize_text(entry.get("slug", ""))
                    if not name or not slug or slug in seen:
                        continue
                    seen.add(slug)
                    cleaned.append({
                        "name": name,
                        "slug": slug
                    })
                return cleaned
        except Exception:
            pass

        return []

    def _save_jar_registry(self, jars: list):
        """
        Purpose:
            Save the jar registry to disk.

        Parameters:
            jars (list): List of jar metadata dictionaries.

        Return:
            None
        """
        cleaned = []
        seen = set()

        for entry in jars:
            if not isinstance(entry, dict):
                continue

            name = self._normalize_text(entry.get("name", ""))
            slug = self._normalize_text(entry.get("slug", ""))

            if not name or not slug or slug in seen:
                continue

            seen.add(slug)
            cleaned.append({
                "name": name,
                "slug": slug
            })

        self._jars_file.write_text(
            json.dumps(cleaned, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _register_jar(self, jar_name: str, jar_slug: str):
        """
        Purpose:
            Add a jar to the registry if it is not already present.

        Parameters:
            jar_name (str): Display name of the jar.
            jar_slug (str): Filesystem-safe jar slug.

        Return:
            None
        """
        jars = self._load_jar_registry()

        if any(entry["slug"] == jar_slug for entry in jars):
            return

        jars.append({
            "name": jar_name,
            "slug": jar_slug
        })
        self._save_jar_registry(jars)

    def _jar_folder(self, jar_slug: str) -> Path:
        """
        Purpose:
            Return the root folder for a specific jar.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            Path: Jar root folder path.
        """
        return self._jars_root / jar_slug

    def _jar_ideas_folder(self, jar_slug: str) -> Path:
        """
        Purpose:
            Return the Ideas folder for a specific jar.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            Path: Ideas folder path.
        """
        return self._jar_folder(jar_slug) / "Ideas"

    def _jar_in_progress_folder(self, jar_slug: str) -> Path:
        """
        Purpose:
            Return the InProgress folder for a specific jar.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            Path: InProgress folder path.
        """
        return self._jar_folder(jar_slug) / "InProgress"

    def _jar_completed_folder(self, jar_slug: str) -> Path:
        """
        Purpose:
            Return the Completed folder for a specific jar.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            Path: Completed folder path.
        """
        return self._jar_folder(jar_slug) / "Completed"

    def _jar_info_path(self, jar_slug: str) -> Path:
        """
        Purpose:
            Return the jar.json path for a specific jar.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            Path: jar.json path.
        """
        return self._jar_folder(jar_slug) / "jar.json"

    def _project_json_path(self, project_folder: Path) -> Path:
        """
        Purpose:
            Return the project.json path for a project folder.

        Parameters:
            project_folder (Path): Project folder.

        Return:
            Path: project.json path.
        """
        return project_folder / "project.json"

    def _project_txt_path(self, project_folder: Path) -> Path:
        """
        Purpose:
            Return the project.txt path for a project folder.

        Parameters:
            project_folder (Path): Project folder.

        Return:
            Path: project.txt path.
        """
        return project_folder / "project.txt"

    def _notes_path(self, project_folder: Path) -> Path:
        """
        Purpose:
            Return the notes.txt path for a project folder.

        Parameters:
            project_folder (Path): Project folder.

        Return:
            Path: notes.txt path.
        """
        return project_folder / "notes.txt"

    def _ensure_jar_exists(self, jar_name: str) -> dict:
        """
        Purpose:
            Ensure a jar exists on disk and in the registry.

        Parameters:
            jar_name (str): Display name of the jar.

        Return:
            dict: Jar metadata dictionary.
        """
        jar_name = self._normalize_text(jar_name)
        jar_slug = self._safe_name(jar_name)

        jar_folder = self._jar_folder(jar_slug)
        ideas_folder = self._jar_ideas_folder(jar_slug)
        in_progress_folder = self._jar_in_progress_folder(jar_slug)
        completed_folder = self._jar_completed_folder(jar_slug)
        jar_info = self._jar_info_path(jar_slug)

        jar_folder.mkdir(parents=True, exist_ok=True)
        ideas_folder.mkdir(exist_ok=True)
        in_progress_folder.mkdir(exist_ok=True)
        completed_folder.mkdir(exist_ok=True)

        if not jar_info.exists():
            jar_info.write_text(
                json.dumps({
                    "name": jar_name,
                    "slug": jar_slug
                }, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

        self._register_jar(jar_name, jar_slug)

        return {
            "name": jar_name,
            "slug": jar_slug
        }

    def _load_jar_info(self, jar_slug: str) -> dict:
        """
        Purpose:
            Load jar metadata for a specific jar slug.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            dict: Jar metadata dictionary.
        """
        jar_info = self._jar_info_path(jar_slug)

        if jar_info.exists():
            try:
                data = json.loads(jar_info.read_text(encoding="utf-8"))
                name = self._normalize_text(data.get("name", ""))
                slug = self._normalize_text(data.get("slug", jar_slug))
                if name:
                    return {"name": name, "slug": slug}
            except Exception:
                pass

        for entry in self._load_jar_registry():
            if entry["slug"] == jar_slug:
                return entry

        return {
            "name": jar_slug,
            "slug": jar_slug
        }

    def _list_jars(self) -> list:
        """
        Purpose:
            Return all known jars with summary counts.

        Parameters:
            None

        Return:
            list: List of jar summary dictionaries.
        """
        jars = []

        for entry in self._load_jar_registry():
            jar_slug = entry["slug"]
            jar_name = entry["name"]

            self._ensure_jar_exists(jar_name)

            ideas_count = len([x for x in self._jar_ideas_folder(jar_slug).iterdir() if x.is_dir()])
            in_progress_count = len([x for x in self._jar_in_progress_folder(jar_slug).iterdir() if x.is_dir()])
            completed_count = len([x for x in self._jar_completed_folder(jar_slug).iterdir() if x.is_dir()])

            jars.append({
                "name": jar_name,
                "slug": jar_slug,
                "ideasCount": ideas_count,
                "inProgressCount": in_progress_count,
                "completedCount": completed_count
            })

        return jars

    def _get_active_project_folder(self, jar_slug: str):
        """
        Purpose:
            Return the active in-progress project folder for a jar if one exists.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            Path | None: Active project folder or None.
        """
        folder = self._jar_in_progress_folder(jar_slug)
        projects = [item for item in folder.iterdir() if item.is_dir()]

        if not projects:
            return None

        return projects[0]

    def _load_project_data(self, project_folder: Path) -> dict:
        """
        Purpose:
            Load structured project data from project.json.

        Parameters:
            project_folder (Path): Project folder.

        Return:
            dict: Project data dictionary.
        """
        json_path = self._project_json_path(project_folder)

        if not json_path.exists():
            project_name = project_folder.name
            txt_path = self._project_txt_path(project_folder)

            if txt_path.exists():
                raw = txt_path.read_text(encoding="utf-8").strip()
                if raw:
                    project_name = raw.splitlines()[0].replace("Project:", "").strip() or project_name

            project_data = {
                "name": project_name,
                "tasks": []
            }
            self._save_project_data(project_folder, project_data)
            return project_data

        try:
            project_data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            project_data = {"name": project_folder.name, "tasks": []}

        if "name" not in project_data or not self._normalize_text(project_data["name"]):
            project_data["name"] = project_folder.name

        if "tasks" not in project_data or not isinstance(project_data["tasks"], list):
            project_data["tasks"] = []

        normalized_tasks = []
        for task in project_data["tasks"]:
            if not isinstance(task, dict):
                continue

            task_name = self._normalize_text(task.get("name", ""))
            if not task_name:
                continue

            subtasks = []
            for subtask in task.get("subtasks", []):
                if not isinstance(subtask, dict):
                    continue
                sub_name = self._normalize_text(subtask.get("name", ""))
                if not sub_name:
                    continue
                subtasks.append({
                    "name": sub_name,
                    "done": bool(subtask.get("done", False))
                })

            normalized_tasks.append({
                "name": task_name,
                "done": bool(task.get("done", False)),
                "subtasks": subtasks
            })

        project_data["tasks"] = normalized_tasks
        return project_data

    def _build_project_txt(self, project_data: dict) -> str:
        """
        Purpose:
            Build the human-readable project.txt contents from project data.

        Parameters:
            project_data (dict): Structured project data.

        Return:
            str: project.txt contents.
        """
        lines = [
            f"Project: {project_data['name']}"
        ]

        tasks = project_data.get("tasks", [])

        for task in tasks:
            lines.extend([
                "",
                f"Task: {task['name']}",
                "",
                f"Completed: {'Yes' if task.get('done', False) else 'No'}",
                "",
                "Subtasks:"
            ])

            subtasks = task.get("subtasks", [])
            if subtasks:
                for subtask in subtasks:
                    mark = "[x]" if subtask.get("done", False) else "[ ]"
                    lines.append(f"{mark} {subtask['name']}")
            else:
                lines.append("(none)")

        return "\n".join(lines)

    def _save_project_data(self, project_folder: Path, project_data: dict):
        """
        Purpose:
            Save structured project data to project.json and mirror it to project.txt.

        Parameters:
            project_folder (Path): Project folder.
            project_data (dict): Structured project data.

        Return:
            None
        """
        project_folder.mkdir(parents=True, exist_ok=True)

        normalized = {
            "name": self._normalize_text(project_data.get("name", "")) or project_folder.name,
            "tasks": []
        }

        for task in project_data.get("tasks", []):
            task_name = self._normalize_text(task.get("name", ""))
            if not task_name:
                continue

            subtasks = []
            for subtask in task.get("subtasks", []):
                sub_name = self._normalize_text(subtask.get("name", ""))
                if not sub_name:
                    continue
                subtasks.append({
                    "name": sub_name,
                    "done": bool(subtask.get("done", False))
                })

            normalized["tasks"].append({
                "name": task_name,
                "done": bool(task.get("done", False)),
                "subtasks": subtasks
            })

        self._project_json_path(project_folder).write_text(
            json.dumps(normalized, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        self._project_txt_path(project_folder).write_text(
            self._build_project_txt(normalized),
            encoding="utf-8"
        )

        notes_path = self._notes_path(project_folder)
        if not notes_path.exists():
            notes_path.write_text("Describe what you built here...", encoding="utf-8")

        legacy_tasks_folder = project_folder / "tasks"
        if legacy_tasks_folder.exists() and legacy_tasks_folder.is_dir():
            shutil.rmtree(legacy_tasks_folder)

    def _all_tasks_complete(self, project_data: dict) -> bool:
        """
        Purpose:
            Check whether all tasks in a project are complete.

        Parameters:
            project_data (dict): Structured project data.

        Return:
            bool: True if all tasks are complete and at least one task exists.
        """
        tasks = project_data.get("tasks", [])
        return len(tasks) > 0 and all(task.get("done", False) for task in tasks)

    def _serialize_jar_picker_state(self) -> dict:
        """
        Purpose:
            Build the frontend state for the jar picker screen.

        Parameters:
            None

        Return:
            dict: State dictionary for jar picker mode.
        """
        return {
            "mode": "jarPicker",
            "jars": self._list_jars()
        }

    def _serialize_jar_state(self, jar_slug: str, message: str = "") -> dict:
        """
        Purpose:
            Build the frontend state for a jar screen with no active idea.

        Parameters:
            jar_slug (str): Jar slug.
            message (str): Optional user-facing message.

        Return:
            dict: State dictionary for jar mode.
        """
        jar_info = self._load_jar_info(jar_slug)
        ideas = []

        for folder in self._jar_ideas_folder(jar_slug).iterdir():
            if folder.is_dir():
                ideas.append(folder.name)

        return {
            "mode": "jar",
            "jarName": jar_info["name"],
            "jarSlug": jar_info["slug"],
            "ideasCount": len(ideas),
            "message": message
        }

    def _serialize_project_state(self, jar_slug: str, project_folder: Path, message: str = "") -> dict:
        """
        Purpose:
            Build the frontend state for the in-progress task screen.

        Parameters:
            jar_slug (str): Jar slug.
            project_folder (Path): Active project folder.
            message (str): Optional user-facing message.

        Return:
            dict: State dictionary for tasks mode.
        """
        jar_info = self._load_jar_info(jar_slug)
        project_data = self._load_project_data(project_folder)

        return {
            "mode": "tasks",
            "jarName": jar_info["name"],
            "jarSlug": jar_info["slug"],
            "projectName": project_data["name"],
            "tasks": project_data.get("tasks", []),
            "message": message
        }

    def _serialize_subtasks_state(self, jar_slug: str, project_folder: Path, task_index: int, message: str = "") -> dict:
        """
        Purpose:
            Build the frontend state for the subtasks screen.

        Parameters:
            jar_slug (str): Jar slug.
            project_folder (Path): Active project folder.
            task_index (int): Task index to open.
            message (str): Optional user-facing message.

        Return:
            dict: State dictionary for subtasks mode.
        """
        jar_info = self._load_jar_info(jar_slug)
        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(jar_slug, project_folder, message)

        task = tasks[task_index]

        return {
            "mode": "subtasks",
            "jarName": jar_info["name"],
            "jarSlug": jar_info["slug"],
            "projectName": project_data["name"],
            "taskIndex": task_index,
            "taskName": task["name"],
            "taskDone": task.get("done", False),
            "subtasks": task.get("subtasks", []),
            "message": message
        }

    def _serialize_completed_jar_state(self, jar_slug: str, message: str = "") -> dict:
        """
        Purpose:
            Build the frontend state for completed ideas within a single jar.

        Parameters:
            jar_slug (str): Jar slug.
            message (str): Optional user-facing message.

        Return:
            dict: State dictionary for jar-specific completed mode.
        """
        jar_info = self._load_jar_info(jar_slug)
        projects = []

        for folder in self._jar_completed_folder(jar_slug).iterdir():
            if folder.is_dir():
                try:
                    data = self._load_project_data(folder)
                    projects.append({
                        "name": data.get("name", folder.name)
                    })
                except Exception:
                    projects.append({
                        "name": folder.name
                    })

        return {
            "mode": "completedJar",
            "jarName": jar_info["name"],
            "jarSlug": jar_info["slug"],
            "projects": projects,
            "count": len(projects),
            "message": message
        }

    def _serialize_completed_all_state(self, message: str = "") -> dict:
        """
        Purpose:
            Build the frontend state for completed ideas across all jars.

        Parameters:
            message (str): Optional user-facing message.

        Return:
            dict: State dictionary for completed-all mode.
        """
        projects = []

        for jar in self._list_jars():
            jar_slug = jar["slug"]
            jar_name = jar["name"]

            for folder in self._jar_completed_folder(jar_slug).iterdir():
                if folder.is_dir():
                    try:
                        data = self._load_project_data(folder)
                        projects.append({
                            "jarName": jar_name,
                            "jarSlug": jar_slug,
                            "name": data.get("name", folder.name)
                        })
                    except Exception:
                        projects.append({
                            "jarName": jar_name,
                            "jarSlug": jar_slug,
                            "name": folder.name
                        })

        return {
            "mode": "completedAll",
            "projects": projects,
            "count": len(projects),
            "message": message
        }

    def get_startup_state(self):
        """
        Purpose:
            Decide what screen the app should show on startup.

        Parameters:
            None

        Return:
            dict: Frontend state dictionary for startup.
        """
        jars = self._list_jars()

        for jar in jars:
            active = self._get_active_project_folder(jar["slug"])
            if active is not None:
                return self._serialize_project_state(jar["slug"], active)

        return self._serialize_jar_picker_state()

    def get_jar_picker_state(self):
        """
        Purpose:
            Return the jar picker screen state directly, without redirecting
            into any active in-progress project.

        Parameters:
            None

        Return:
            dict: Frontend state dictionary for jar picker mode.
        """
        return self._serialize_jar_picker_state()

    def create_jar(self, jar_name: str):
        """
        Purpose:
            Create a new jar.

        Parameters:
            jar_name (str): Name of the new jar.

        Return:
            dict: Result dictionary with creation status.
        """
        jar_name = self._normalize_text(jar_name)
        if not jar_name:
            return {"ok": False, "message": "Jar name cannot be empty"}

        jar_slug = self._safe_name(jar_name)
        if self._jar_folder(jar_slug).exists():
            return {"ok": False, "message": "Jar already exists"}

        self._ensure_jar_exists(jar_name)
        return {
            "ok": True,
            "message": f"{jar_name} created",
            "jarName": jar_name,
            "jarSlug": jar_slug
        }

    def get_jars(self):
        """
        Purpose:
            Return all jars and summary counts.

        Parameters:
            None

        Return:
            dict: Result dictionary containing jar list.
        """
        jars = self._list_jars()
        return {
            "ok": True,
            "jars": jars,
            "count": len(jars)
        }

    def open_jar(self, jar_slug: str):
        """
        Purpose:
            Open a jar. If it has an active in-progress idea, open that.
            Otherwise show the jar screen.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            dict: Frontend state dictionary.
        """
        jar_info = self._load_jar_info(jar_slug)
        self._ensure_jar_exists(jar_info["name"])

        active = self._get_active_project_folder(jar_slug)
        if active is not None:
            return self._serialize_project_state(jar_slug, active)

        return self._serialize_jar_state(jar_slug)

    def get_completed_all_projects(self):
        """
        Purpose:
            Return completed ideas across all jars.

        Parameters:
            None

        Return:
            dict: Frontend state dictionary for completed-all mode.
        """
        return self._serialize_completed_all_state()

    def get_completed_projects_for_jar(self, jar_slug: str):
        """
        Purpose:
            Return completed ideas for a specific jar.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            dict: Frontend state dictionary for jar-specific completed mode.
        """
        return self._serialize_completed_jar_state(jar_slug)

    def pick_idea(self, jar_slug: str):
        """
        Purpose:
            Pick a random idea from a jar's Ideas folder and move it to InProgress.
            If an active idea already exists, open that instead.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            dict: Frontend state dictionary.
        """
        active = self._get_active_project_folder(jar_slug)
        if active is not None:
            return self._serialize_project_state(jar_slug, active)

        ideas = [folder for folder in self._jar_ideas_folder(jar_slug).iterdir() if folder.is_dir()]
        if not ideas:
            return self._serialize_jar_state(jar_slug, "There are no ideas")

        chosen = random.choice(ideas)
        destination = self._jar_in_progress_folder(jar_slug) / chosen.name

        if destination.exists():
            return self._serialize_jar_state(jar_slug, f"{chosen.name} is already in InProgress")

        shutil.move(str(chosen), str(destination))

        data = self._load_project_data(destination)
        self._save_project_data(destination, data)

        return self._serialize_project_state(jar_slug, destination)

    def create_project(self, jar_slug: str, project_name: str, tasks: list):
        """
        Purpose:
            Create a new idea inside a jar's Ideas folder.

        Parameters:
            jar_slug (str): Jar slug.
            project_name (str): Project display name.
            tasks (list): List of task dictionaries.

        Return:
            dict: Result dictionary with creation status.
        """
        project_name = self._normalize_text(project_name)
        if not project_name:
            return {"ok": False, "message": "Project name is empty"}

        cleaned_tasks = []
        for task in tasks or []:
            task_name = self._normalize_text(task.get("name", ""))
            subtasks = [self._normalize_text(x) for x in task.get("subtasks", []) if self._normalize_text(x)]

            if not task_name:
                continue

            if not subtasks:
                return {"ok": False, "message": f'Task "{task_name}" needs at least 1 subtask'}

            cleaned_tasks.append({
                "name": task_name,
                "done": False,
                "subtasks": [{"name": sub, "done": False} for sub in subtasks]
            })

        if not cleaned_tasks:
            return {"ok": False, "message": "You need at least 1 task"}

        safe_project_name = self._safe_name(project_name)
        project_folder = self._jar_ideas_folder(jar_slug) / safe_project_name

        if project_folder.exists():
            return {"ok": False, "message": "Project already exists"}

        project_folder.mkdir(parents=True, exist_ok=True)

        self._save_project_data(project_folder, {
            "name": project_name,
            "tasks": cleaned_tasks
        })

        return {"ok": True, "message": f"{project_name} created"}

    def open_task(self, jar_slug: str, task_index: int):
        """
        Purpose:
            Open a task inside the active project for a jar.

        Parameters:
            jar_slug (str): Jar slug.
            task_index (int): Index of the task to open.

        Return:
            dict: Frontend state dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return self._serialize_jar_state(jar_slug, "No active project")

        return self._serialize_subtasks_state(jar_slug, project_folder, task_index)

    def create_task(self, jar_slug: str, task_name: str, subtasks: list):
        """
        Purpose:
            Add a task to the active project in a jar.

        Parameters:
            jar_slug (str): Jar slug.
            task_name (str): Task name.
            subtasks (list): List of subtask names.

        Return:
            dict: Frontend state dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return self._serialize_jar_state(jar_slug, "No active project")

        task_name = self._normalize_text(task_name)
        if not task_name:
            return self._serialize_project_state(jar_slug, project_folder, "Task name cannot be empty")

        cleaned_subtasks = [self._normalize_text(x) for x in subtasks if self._normalize_text(x)]
        if not cleaned_subtasks:
            return self._serialize_project_state(jar_slug, project_folder, "A task needs at least 1 subtask")

        project_data = self._load_project_data(project_folder)
        project_data.setdefault("tasks", []).append({
            "name": task_name,
            "done": False,
            "subtasks": [{"name": sub, "done": False} for sub in cleaned_subtasks]
        })

        self._save_project_data(project_folder, project_data)
        return self._serialize_project_state(jar_slug, project_folder)

    def rename_task(self, jar_slug: str, task_index: int, new_name: str):
        """
        Purpose:
            Rename a task in the active project for a jar.

        Parameters:
            jar_slug (str): Jar slug.
            task_index (int): Task index.
            new_name (str): New task name.

        Return:
            dict: Frontend state dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return self._serialize_jar_state(jar_slug, "No active project")

        new_name = self._normalize_text(new_name)
        if not new_name:
            return self._serialize_project_state(jar_slug, project_folder, "Task name cannot be empty")

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(jar_slug, project_folder)

        tasks[task_index]["name"] = new_name
        self._save_project_data(project_folder, project_data)

        return self._serialize_project_state(jar_slug, project_folder)

    def delete_task(self, jar_slug: str, task_index: int):
        """
        Purpose:
            Delete a task from the active project if more than one task exists.

        Parameters:
            jar_slug (str): Jar slug.
            task_index (int): Task index.

        Return:
            dict: Frontend state dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return self._serialize_jar_state(jar_slug, "No active project")

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if len(tasks) <= 1:
            return self._serialize_project_state(jar_slug, project_folder, "A project must have at least 1 task")

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(jar_slug, project_folder)

        del tasks[task_index]
        self._save_project_data(project_folder, project_data)

        return self._serialize_project_state(jar_slug, project_folder)

    def toggle_task(self, jar_slug: str, task_index: int):
        """
        Purpose:
            Toggle a task and all of its subtasks in the active project.

        Parameters:
            jar_slug (str): Jar slug.
            task_index (int): Task index.

        Return:
            dict: Frontend state dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return self._serialize_jar_state(jar_slug, "No active project")

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(jar_slug, project_folder)

        task = tasks[task_index]
        new_state = not task.get("done", False)
        task["done"] = new_state

        for subtask in task.get("subtasks", []):
            subtask["done"] = new_state

        self._save_project_data(project_folder, project_data)

        if self._all_tasks_complete(project_data):
            destination = self._jar_completed_folder(jar_slug) / project_folder.name
            if destination.exists():
                destination = self._jar_completed_folder(jar_slug) / f"{project_folder.name}_completed"
            shutil.move(str(project_folder), str(destination))
            return self._serialize_jar_state(jar_slug, f"{project_data['name']} moved to Completed")

        return self._serialize_project_state(jar_slug, project_folder)

    def pick_random_task(self, jar_slug: str):
        """
        Purpose:
            Pick a random incomplete task and open its subtasks screen.

        Parameters:
            jar_slug (str): Jar slug.

        Return:
            dict: Frontend state dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return self._serialize_jar_state(jar_slug, "No active project")

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        candidates = [
            (index, task)
            for index, task in enumerate(tasks)
            if not task.get("done", False)
        ]

        if not candidates:
            return self._serialize_project_state(jar_slug, project_folder, "All tasks complete")

        task_index, _task = random.choice(candidates)
        return self._serialize_subtasks_state(jar_slug, project_folder, task_index)

    def rename_subtask(self, jar_slug: str, task_index: int, subtask_index: int, new_name: str):
        """
        Purpose:
            Rename a subtask in the active project.

        Parameters:
            jar_slug (str): Jar slug.
            task_index (int): Task index.
            subtask_index (int): Subtask index.
            new_name (str): New subtask name.

        Return:
            dict: Frontend state dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return self._serialize_jar_state(jar_slug, "No active project")

        new_name = self._normalize_text(new_name)
        if not new_name:
            return self._serialize_subtasks_state(jar_slug, project_folder, task_index, "Subtask name cannot be empty")

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(jar_slug, project_folder)

        subtasks = tasks[task_index].get("subtasks", [])
        if not (0 <= subtask_index < len(subtasks)):
            return self._serialize_subtasks_state(jar_slug, project_folder, task_index)

        subtasks[subtask_index]["name"] = new_name
        self._save_project_data(project_folder, project_data)

        return self._serialize_subtasks_state(jar_slug, project_folder, task_index)

    def delete_subtask(self, jar_slug: str, task_index: int, subtask_index: int):
        """
        Purpose:
            Delete a subtask if more than one subtask exists.

        Parameters:
            jar_slug (str): Jar slug.
            task_index (int): Task index.
            subtask_index (int): Subtask index.

        Return:
            dict: Frontend state dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return self._serialize_jar_state(jar_slug, "No active project")

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(jar_slug, project_folder)

        subtasks = tasks[task_index].get("subtasks", [])

        if len(subtasks) <= 1:
            return self._serialize_subtasks_state(jar_slug, project_folder, task_index, "A task must have at least 1 subtask")

        if not (0 <= subtask_index < len(subtasks)):
            return self._serialize_subtasks_state(jar_slug, project_folder, task_index)

        del subtasks[subtask_index]
        tasks[task_index]["done"] = all(st.get("done", False) for st in subtasks) if subtasks else False

        self._save_project_data(project_folder, project_data)
        return self._serialize_subtasks_state(jar_slug, project_folder, task_index)

    def toggle_subtask(self, jar_slug: str, task_index: int, subtask_index: int):
        """
        Purpose:
            Toggle a subtask in the active project.

        Parameters:
            jar_slug (str): Jar slug.
            task_index (int): Task index.
            subtask_index (int): Subtask index.

        Return:
            dict: Frontend state dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return self._serialize_jar_state(jar_slug, "No active project")

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(jar_slug, project_folder)

        task = tasks[task_index]
        subtasks = task.get("subtasks", [])

        if not (0 <= subtask_index < len(subtasks)):
            return self._serialize_subtasks_state(jar_slug, project_folder, task_index)

        subtasks[subtask_index]["done"] = not subtasks[subtask_index].get("done", False)
        task["done"] = all(st.get("done", False) for st in subtasks) if subtasks else False

        self._save_project_data(project_folder, project_data)

        if self._all_tasks_complete(project_data):
            destination = self._jar_completed_folder(jar_slug) / project_folder.name
            if destination.exists():
                destination = self._jar_completed_folder(jar_slug) / f"{project_folder.name}_completed"
            shutil.move(str(project_folder), str(destination))
            return self._serialize_jar_state(jar_slug, f"{project_data['name']} moved to Completed")

        return self._serialize_subtasks_state(jar_slug, project_folder, task_index)

    def pick_random_subtask(self, jar_slug: str, task_index: int):
        """
        Purpose:
            Highlight a random incomplete subtask by returning the subtasks screen
            with highlightSubtask set.

        Parameters:
            jar_slug (str): Jar slug.
            task_index (int): Task index.

        Return:
            dict: Frontend state dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return self._serialize_jar_state(jar_slug, "No active project")

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(jar_slug, project_folder)

        task = tasks[task_index]
        subtasks = [s for s in task.get("subtasks", []) if not s.get("done", False)]

        state = self._serialize_subtasks_state(jar_slug, project_folder, task_index)

        if not subtasks:
            return state

        chosen = random.choice(subtasks)
        state["highlightSubtask"] = chosen["name"]
        return state

    def save_notes(self, jar_slug: str, text: str):
        """
        Purpose:
            Save notes for the active project in a jar.

        Parameters:
            jar_slug (str): Jar slug.
            text (str): Notes text.

        Return:
            dict: Result dictionary.
        """
        project_folder = self._get_active_project_folder(jar_slug)
        if project_folder is None:
            return {"ok": False, "message": "No active project"}

        self._notes_path(project_folder).write_text(str(text), encoding="utf-8")
        return {"ok": True, "message": "Notes saved"}

    def get_project_notes(self, jar_slug: str, project_name: str):
        """
        Purpose:
            Load notes for a completed project in a jar.

        Parameters:
            jar_slug (str): Jar slug.
            project_name (str): Project folder name.

        Return:
            dict: Result dictionary including notes text.
        """
        folder = self._jar_completed_folder(jar_slug) / project_name
        notes_file = self._notes_path(folder)

        if not folder.exists():
            return {"ok": False, "message": "Project not found", "notes": ""}

        if not notes_file.exists():
            return {"ok": True, "notes": ""}

        return {
            "ok": True,
            "notes": notes_file.read_text(encoding="utf-8")
        }

    def import_legacy_project(self, jar_slug: str, legacy_project_folder_path: str):
        """
        Purpose:
            Import an old project folder that used project.txt plus tasks/*.txt
            into the new project.json + combined project.txt format.

        Parameters:
            jar_slug (str): Target jar slug.
            legacy_project_folder_path (str): Absolute or relative path to the old project folder.

        Return:
            dict: Result dictionary for the import operation.
        """
        legacy_folder = Path(legacy_project_folder_path).expanduser().resolve()

        if not legacy_folder.exists() or not legacy_folder.is_dir():
            return {"ok": False, "message": "Legacy project folder not found"}

        project_name = legacy_folder.name
        legacy_project_txt = legacy_folder / "project.txt"
        legacy_tasks_folder = legacy_folder / "tasks"

        if legacy_project_txt.exists():
            raw_name = legacy_project_txt.read_text(encoding="utf-8").strip()
            if raw_name:
                project_name = raw_name.splitlines()[0].replace("Project:", "").strip() or project_name

        tasks = []

        if legacy_tasks_folder.exists() and legacy_tasks_folder.is_dir():
            for task_file in sorted(legacy_tasks_folder.glob("*.txt")):
                lines = task_file.read_text(encoding="utf-8").splitlines()

                task_name = task_file.stem
                task_done = False
                subtasks = []

                in_subtasks = False

                for raw_line in lines:
                    line = raw_line.strip()

                    if line.startswith("Task:"):
                        task_name = line.replace("Task:", "", 1).strip() or task_name
                        continue

                    if line.startswith("Completed:"):
                        value = line.replace("Completed:", "", 1).strip().lower()
                        task_done = value == "yes"
                        continue

                    if line == "Subtasks:":
                        in_subtasks = True
                        continue

                    if in_subtasks and line:
                        if line.startswith("[x]"):
                            subtasks.append({
                                "name": line[3:].strip(),
                                "done": True
                            })
                        elif line.startswith("[ ]"):
                            subtasks.append({
                                "name": line[3:].strip(),
                                "done": False
                            })

                if subtasks:
                    tasks.append({
                        "name": task_name,
                        "done": task_done,
                        "subtasks": subtasks
                    })

        if not tasks:
            return {"ok": False, "message": "No legacy task files found to import"}

        safe_project_name = self._safe_name(project_name)
        destination = self._jar_ideas_folder(jar_slug) / safe_project_name

        if destination.exists():
            return {"ok": False, "message": "A project with that name already exists in this jar"}

        destination.mkdir(parents=True, exist_ok=True)
        self._save_project_data(destination, {
            "name": project_name,
            "tasks": tasks
        })

        legacy_notes = legacy_folder / "notes.txt"
        if legacy_notes.exists():
            shutil.copy2(legacy_notes, self._notes_path(destination))

        return {"ok": True, "message": f"{project_name} imported"}