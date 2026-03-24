import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import webview


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_ui_file() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "ui" / "index.html"
    return Path(__file__).resolve().parent / "ui" / "index.html"


def ensure_started_via_launcher() -> bool:
    if os.environ.get("IDEAJAR_STARTED_BY_LAUNCHER") == "1":
        return True

    app_root = get_app_root()
    launcher_path = app_root / "launcher"

    if not launcher_path.exists():
        return True

    try:
        subprocess.Popen([str(launcher_path)], cwd=str(app_root))
    except Exception as e:
        print(f"Failed to start launcher: {e}")
        return True

    return False


def ensure_app_folders():
    app_root = get_app_root()
    base_folder = app_root / "IdeaFolder"
    ideas_folder = base_folder / "Ideas"
    in_progress_folder = base_folder / "InProgress"
    completed_folder = base_folder / "Completed"
    tags_file = base_folder / "tags.json"

    base_folder.mkdir(parents=True, exist_ok=True)
    ideas_folder.mkdir(parents=True, exist_ok=True)
    in_progress_folder.mkdir(parents=True, exist_ok=True)
    completed_folder.mkdir(parents=True, exist_ok=True)

    if not tags_file.exists():
        tags_file.write_text("[]", encoding="utf-8")

    return {
        "app_root": app_root,
        "base_folder": base_folder,
        "ideas_folder": ideas_folder,
        "in_progress_folder": in_progress_folder,
        "completed_folder": completed_folder,
        "tags_file": tags_file,
    }


class Api:
    def __init__(self):
        folders = ensure_app_folders()
        self._base_folder = folders["base_folder"]
        self._ideas_folder = folders["ideas_folder"]
        self._in_progress_folder = folders["in_progress_folder"]
        self._completed_folder = folders["completed_folder"]
        self._tags_file = folders["tags_file"]

    def _safe_name(self, name: str) -> str:
        bad_chars = '<>:"/\\|?*'
        cleaned = "".join("_" if c in bad_chars else c for c in name).strip()
        return cleaned or "Untitled"

    def _normalize_tag(self, tag: str) -> str:
        tag = str(tag).strip()
        if not tag:
            return ""
        if not tag.startswith("#"):
            tag = f"#{tag}"
        return tag.lower()

    def _clean_tags(self, tags) -> list:
        if not tags:
            return []

        cleaned = []
        seen = set()

        for tag in tags:
            normalized = self._normalize_tag(tag)
            if normalized and normalized not in seen:
                seen.add(normalized)
                cleaned.append(normalized)

        return cleaned

    def _load_tag_registry(self) -> list:
        if not self._tags_file.exists():
            return []

        try:
            data = json.loads(self._tags_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return self._clean_tags(data)
        except Exception:
            pass

        return []

    def _save_tag_registry(self, tags: list):
        cleaned = self._clean_tags(tags)
        self._tags_file.write_text(
            json.dumps(cleaned, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _register_tags(self, tags: list):
        existing = self._load_tag_registry()
        combined = self._clean_tags(existing + (tags or []))
        self._save_tag_registry(combined)

    def _get_in_progress_projects(self):
        return [item for item in self._in_progress_folder.iterdir() if item.is_dir()]

    def _get_current_project_folder(self):
        projects = self._get_in_progress_projects()
        if not projects:
            return None
        return projects[0]

    def _project_json_path(self, project_folder: Path) -> Path:
        return project_folder / "project.json"

    def _project_txt_path(self, project_folder: Path) -> Path:
        return project_folder / "project.txt"

    def _tasks_folder_path(self, project_folder: Path) -> Path:
        return project_folder / "tasks"

    def _notes_path(self, project_folder: Path) -> Path:
        return project_folder / "notes.txt"

    def _load_project_data(self, project_folder: Path) -> dict:
        json_path = self._project_json_path(project_folder)

        if not json_path.exists():
            tasks_folder = self._tasks_folder_path(project_folder)
            tasks_folder.mkdir(exist_ok=True)

            tasks = []
            for task_file in tasks_folder.glob("*.txt"):
                tasks.append({
                    "name": task_file.stem,
                    "done": False,
                    "subtasks": []
                })

            project_data = {
                "name": project_folder.name,
                "tags": [],
                "tasks": tasks
            }
            self._save_project_data(project_folder, project_data)
            return project_data

        project_data = json.loads(json_path.read_text(encoding="utf-8"))

        if "name" not in project_data:
            project_data["name"] = project_folder.name

        if "tags" not in project_data or not isinstance(project_data["tags"], list):
            project_data["tags"] = []

        project_data["tags"] = self._clean_tags(project_data["tags"])

        if "tasks" not in project_data or not isinstance(project_data["tasks"], list):
            project_data["tasks"] = []

        return project_data

    def _save_project_data(self, project_folder: Path, project_data: dict):
        project_data = dict(project_data)
        project_data["tags"] = self._clean_tags(project_data.get("tags", []))

        json_path = self._project_json_path(project_folder)
        json_path.write_text(
            json.dumps(project_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        self._register_tags(project_data["tags"])

    def _rewrite_task_files(self, project_folder: Path, project_data: dict):
        tasks_folder = self._tasks_folder_path(project_folder)
        tasks_folder.mkdir(exist_ok=True)

        for old_file in tasks_folder.glob("*.txt"):
            old_file.unlink()

        for task in project_data.get("tasks", []):
            safe_task_name = self._safe_name(task["name"])
            task_file = tasks_folder / f"{safe_task_name}.txt"

            lines = [
                f"Task: {task['name']}",
                "",
                f"Completed: {'Yes' if task.get('done', False) else 'No'}",
                "",
                "Subtasks:"
            ]

            subtasks = task.get("subtasks", [])
            if subtasks:
                for subtask in subtasks:
                    mark = "[x]" if subtask.get("done", False) else "[ ]"
                    lines.append(f"{mark} {subtask['name']}")
            else:
                lines.append("(none)")

            task_file.write_text("\n".join(lines), encoding="utf-8")

    def _all_tasks_complete(self, project_data: dict) -> bool:
        tasks = project_data.get("tasks", [])
        return len(tasks) > 0 and all(task.get("done", False) for task in tasks)

    def _ensure_project_files_exist(self, project_folder: Path):
        project_folder.mkdir(parents=True, exist_ok=True)
        self._tasks_folder_path(project_folder).mkdir(exist_ok=True)

        project_txt = self._project_txt_path(project_folder)
        if not project_txt.exists():
            project_txt.write_text(project_folder.name, encoding="utf-8")

        notes_file = self._notes_path(project_folder)
        if not notes_file.exists():
            notes_file.write_text("Describe what you built here...", encoding="utf-8")

        json_path = self._project_json_path(project_folder)
        if not json_path.exists():
            self._save_project_data(project_folder, {
                "name": project_folder.name,
                "tags": [],
                "tasks": []
            })

    def _serialize_project_state(self, project_folder: Path) -> dict:
        project_data = self._load_project_data(project_folder)
        return {
            "mode": "tasks",
            "projectName": project_data["name"],
            "tags": project_data.get("tags", []),
            "availableTags": self._load_tag_registry(),
            "tasks": project_data.get("tasks", [])
        }

    def _serialize_subtasks_state(self, project_folder: Path, task_index: int) -> dict:
        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(project_folder)

        task = tasks[task_index]
        return {
            "mode": "subtasks",
            "projectName": project_data["name"],
            "tags": project_data.get("tags", []),
            "availableTags": self._load_tag_registry(),
            "taskIndex": task_index,
            "taskName": task["name"],
            "taskDone": task.get("done", False),
            "subtasks": task.get("subtasks", [])
        }

    def get_startup_state(self):
        current_project = self._get_current_project_folder()
        if current_project is None:
            return {
                "mode": "jar",
                "availableTags": self._load_tag_registry()
            }
        return self._serialize_project_state(current_project)

    def get_available_tags(self):
        tags = self._load_tag_registry()
        return {
            "ok": True,
            "tags": tags,
            "count": len(tags)
        }

    def create_tag(self, tag_name: str):
        normalized = self._normalize_tag(tag_name)

        if not normalized:
            return {"ok": False, "message": "Tag name cannot be empty"}

        tags = self._load_tag_registry()
        if normalized in tags:
            return {"ok": True, "message": "Tag already exists", "tag": normalized}

        tags.append(normalized)
        self._save_tag_registry(tags)

        return {"ok": True, "message": f"{normalized} created", "tag": normalized}

    def get_ideas_by_tag(self, tag: str):
        normalized = self._normalize_tag(tag)
        matching = []

        for folder in self._ideas_folder.iterdir():
            if not folder.is_dir():
                continue

            try:
                project_data = self._load_project_data(folder)
                if normalized in project_data.get("tags", []):
                    matching.append(project_data["name"])
            except Exception:
                continue

        return {
            "ok": True,
            "tag": normalized,
            "projects": matching,
            "count": len(matching)
        }

    def pick_idea(self, tag: str = None):
        current_project = self._get_current_project_folder()
        if current_project is not None:
            return self._serialize_project_state(current_project)

        idea_folders = [folder for folder in self._ideas_folder.iterdir() if folder.is_dir()]

        if tag:
            normalized_tag = self._normalize_tag(tag)
            filtered = []

            for folder in idea_folders:
                try:
                    project_data = self._load_project_data(folder)
                    if normalized_tag in project_data.get("tags", []):
                        filtered.append(folder)
                except Exception:
                    continue

            idea_folders = filtered

        if not idea_folders:
            return {"mode": "jar", "message": "No ideas found", "availableTags": self._load_tag_registry()}

        chosen_folder = random.choice(idea_folders)
        destination = self._in_progress_folder / chosen_folder.name

        if destination.exists():
            return {"mode": "jar", "message": f"{chosen_folder.name} is already in InProgress"}

        notes_file = chosen_folder / "notes.txt"
        if not notes_file.exists():
            notes_file.write_text("Describe what you built here...", encoding="utf-8")

        shutil.move(str(chosen_folder), str(destination))

        self._ensure_project_files_exist(destination)

        project_data = self._load_project_data(destination)
        self._rewrite_task_files(destination, project_data)

        return self._serialize_project_state(destination)

    def open_task(self, task_index: int):
        project_folder = self._get_current_project_folder()
        if project_folder is None:
            return {"mode": "jar", "message": "No active project", "availableTags": self._load_tag_registry()}

        return self._serialize_subtasks_state(project_folder, task_index)

    def save_notes(self, text: str):
        project_folder = self._get_current_project_folder()
        if project_folder is None:
            return {"ok": False, "message": "No active project"}

        notes_file = self._notes_path(project_folder)
        notes_file.write_text(text, encoding="utf-8")
        return {"ok": True, "message": "Notes saved"}

    def get_project_notes(self, project_name: str):
        folder = self._completed_folder / project_name
        notes_file = folder / "notes.txt"

        if not folder.exists():
            return {"ok": False, "message": "Project not found", "notes": ""}

        if not notes_file.exists():
            return {"ok": True, "notes": ""}

        return {
            "ok": True,
            "notes": notes_file.read_text(encoding="utf-8")
        }

    def update_project_tags(self, tags: list):
        project_folder = self._get_current_project_folder()
        if project_folder is None:
            return {"mode": "jar", "message": "No active project", "availableTags": self._load_tag_registry()}

        project_data = self._load_project_data(project_folder)
        project_data["tags"] = self._clean_tags(tags)

        self._save_project_data(project_folder, project_data)
        self._rewrite_task_files(project_folder, project_data)

        return self._serialize_project_state(project_folder)

    def toggle_task(self, task_index: int):
        project_folder = self._get_current_project_folder()
        if project_folder is None:
            return {"mode": "jar", "message": "No active project", "availableTags": self._load_tag_registry()}

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(project_folder)

        task = tasks[task_index]
        new_state = not task.get("done", False)
        task["done"] = new_state

        for subtask in task.get("subtasks", []):
            subtask["done"] = new_state

        self._save_project_data(project_folder, project_data)
        self._rewrite_task_files(project_folder, project_data)

        if self._all_tasks_complete(project_data):
            destination = self._completed_folder / project_folder.name
            if destination.exists():
                destination = self._completed_folder / f"{project_folder.name}_completed"
            shutil.move(str(project_folder), str(destination))
            return {"mode": "jar", "message": f"{project_data['name']} moved to Completed", "availableTags": self._load_tag_registry()}

        return self._serialize_project_state(project_folder)

    def toggle_subtask(self, task_index: int, subtask_index: int):
        project_folder = self._get_current_project_folder()
        if project_folder is None:
            return {"mode": "jar", "message": "No active project", "availableTags": self._load_tag_registry()}

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(project_folder)

        task = tasks[task_index]
        subtasks = task.get("subtasks", [])

        if not (0 <= subtask_index < len(subtasks)):
            return self._serialize_subtasks_state(project_folder, task_index)

        subtasks[subtask_index]["done"] = not subtasks[subtask_index].get("done", False)

        if subtasks:
            task["done"] = all(st.get("done", False) for st in subtasks)

        self._save_project_data(project_folder, project_data)
        self._rewrite_task_files(project_folder, project_data)

        if self._all_tasks_complete(project_data):
            destination = self._completed_folder / project_folder.name
            if destination.exists():
                destination = self._completed_folder / f"{project_folder.name}_completed"
            shutil.move(str(project_folder), str(destination))
            return {"mode": "jar", "message": f"{project_data['name']} moved to Completed", "availableTags": self._load_tag_registry()}

        return self._serialize_subtasks_state(project_folder, task_index)

    def create_task(self, task_name: str, subtasks: list):
        project_folder = self._get_current_project_folder()

        if project_folder is None:
            return {"mode": "jar", "message": "No active project", "availableTags": self._load_tag_registry()}

        project_data = self._load_project_data(project_folder)
        task_name = task_name.strip()

        if not task_name:
            return {
                "mode": "tasks",
                "projectName": project_data["name"],
                "tags": project_data.get("tags", []),
                "availableTags": self._load_tag_registry(),
                "tasks": project_data.get("tasks", []),
                "message": "Task name cannot be empty"
            }

        cleaned_subtasks = [sub.strip() for sub in subtasks if sub.strip()]
        if not cleaned_subtasks:
            return {
                "mode": "tasks",
                "projectName": project_data["name"],
                "tags": project_data.get("tags", []),
                "availableTags": self._load_tag_registry(),
                "tasks": project_data.get("tasks", []),
                "message": "A task needs at least 1 subtask"
            }

        task_entry = {
            "name": task_name,
            "done": False,
            "subtasks": [
                {"name": sub, "done": False}
                for sub in cleaned_subtasks
            ]
        }

        project_data.setdefault("tasks", []).append(task_entry)

        self._save_project_data(project_folder, project_data)
        self._rewrite_task_files(project_folder, project_data)

        return self._serialize_project_state(project_folder)

    def delete_task(self, task_index: int):
        project_folder = self._get_current_project_folder()

        if project_folder is None:
            return {"mode": "jar", "message": "No active project", "availableTags": self._load_tag_registry()}

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if len(tasks) <= 1:
            return {
                "mode": "tasks",
                "projectName": project_data["name"],
                "tags": project_data.get("tags", []),
                "availableTags": self._load_tag_registry(),
                "tasks": tasks,
                "message": "A project must have at least 1 task"
            }

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(project_folder)

        del tasks[task_index]

        self._save_project_data(project_folder, project_data)
        self._rewrite_task_files(project_folder, project_data)

        return self._serialize_project_state(project_folder)

    def delete_subtask(self, task_index: int, subtask_index: int):
        project_folder = self._get_current_project_folder()

        if project_folder is None:
            return {"mode": "jar", "message": "No active project", "availableTags": self._load_tag_registry()}

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(project_folder)

        subtasks = tasks[task_index].get("subtasks", [])

        if len(subtasks) <= 1:
            return {
                "mode": "subtasks",
                "projectName": project_data["name"],
                "tags": project_data.get("tags", []),
                "availableTags": self._load_tag_registry(),
                "taskIndex": task_index,
                "taskName": tasks[task_index]["name"],
                "taskDone": tasks[task_index].get("done", False),
                "subtasks": subtasks,
                "message": "A task must have at least 1 subtask"
            }

        if not (0 <= subtask_index < len(subtasks)):
            return self._serialize_subtasks_state(project_folder, task_index)

        del subtasks[subtask_index]

        if subtasks:
            tasks[task_index]["done"] = all(st.get("done", False) for st in subtasks)
        else:
            tasks[task_index]["done"] = False

        self._save_project_data(project_folder, project_data)
        self._rewrite_task_files(project_folder, project_data)

        return self._serialize_subtasks_state(project_folder, task_index)

    def create_project(self, project_name: str, tasks: list, tags: list = None):
        project_name = project_name.strip()
        if not project_name:
            return {"ok": False, "message": "Project name is empty"}

        if not tasks:
            return {"ok": False, "message": "You need at least 1 task"}

        cleaned_tasks = []
        for task in tasks:
            task_name = task.get("name", "").strip()
            subtasks = [sub.strip() for sub in task.get("subtasks", []) if sub.strip()]

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

        cleaned_tags = self._clean_tags(tags or [])

        safe_project_name = self._safe_name(project_name)
        project_folder = self._ideas_folder / safe_project_name

        if project_folder.exists():
            return {"ok": False, "message": "Project already exists"}

        project_folder.mkdir(parents=True, exist_ok=True)
        (project_folder / "tasks").mkdir(exist_ok=True)

        (project_folder / "project.txt").write_text(project_name, encoding="utf-8")
        (project_folder / "notes.txt").write_text("Describe what you built here...", encoding="utf-8")

        project_data = {
            "name": project_name,
            "tags": cleaned_tags,
            "tasks": cleaned_tasks
        }

        self._save_project_data(project_folder, project_data)
        self._rewrite_task_files(project_folder, project_data)

        return {"ok": True, "message": f"{project_name} created", "tags": cleaned_tags}

    def pick_random_task(self):
        project_folder = self._get_current_project_folder()
        if project_folder is None:
            return {"mode": "jar", "message": "No active project", "availableTags": self._load_tag_registry()}

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        incomplete_tasks = [t for t in tasks if not t.get("done", False)]

        if not incomplete_tasks:
            return {
                "mode": "tasks",
                "projectName": project_data["name"],
                "tags": project_data.get("tags", []),
                "availableTags": self._load_tag_registry(),
                "tasks": tasks,
                "message": "All tasks complete"
            }

        chosen = random.choice(incomplete_tasks)

        return {
            "mode": "tasks",
            "projectName": project_data["name"],
            "tags": project_data.get("tags", []),
            "availableTags": self._load_tag_registry(),
            "tasks": tasks,
            "highlightTask": chosen["name"]
        }

    def pick_random_subtask(self, task_index: int):
        project_folder = self._get_current_project_folder()
        if project_folder is None:
            return {"mode": "jar", "message": "No active project", "availableTags": self._load_tag_registry()}

        project_data = self._load_project_data(project_folder)
        tasks = project_data.get("tasks", [])

        if not (0 <= task_index < len(tasks)):
            return self._serialize_project_state(project_folder)

        task = tasks[task_index]
        subtasks = [s for s in task.get("subtasks", []) if not s.get("done", False)]

        if not subtasks:
            return self._serialize_subtasks_state(project_folder, task_index)

        chosen = random.choice(subtasks)

        return {
            "mode": "subtasks",
            "projectName": project_data["name"],
            "tags": project_data.get("tags", []),
            "availableTags": self._load_tag_registry(),
            "taskIndex": task_index,
            "taskName": task["name"],
            "taskDone": task.get("done", False),
            "highlightSubtask": chosen["name"],
            "subtasks": task.get("subtasks", [])
        }

    def resize_window(self, width: int, height: int):
        if webview.windows:
            webview.windows[0].resize(width, height)

    def get_completed_projects(self):
        projects = []

        for folder in self._completed_folder.iterdir():
            if folder.is_dir():
                try:
                    project_data = self._load_project_data(folder)
                    projects.append({
                        "name": project_data.get("name", folder.name),
                        "tags": project_data.get("tags", [])
                    })
                except Exception:
                    projects.append({
                        "name": folder.name,
                        "tags": []
                    })

        return {
            "mode": "completed",
            "projects": projects,
            "count": len(projects),
            "availableTags": self._load_tag_registry()
        }

    def close_app(self):
        if webview.windows:
            webview.windows[0].destroy()


if __name__ == "__main__":
    if not ensure_started_via_launcher():
        sys.exit(0)

    ensure_app_folders()

    ui_file = get_ui_file()

    webview.create_window(
        "Idea Jar",
        ui_file.as_uri(),
        js_api=Api(),
        frameless=True,
        transparent=True,
        width=240,
        height=240
    )

    webview.start()