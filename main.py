import json
import random
import shutil
from pathlib import Path

import webview

programVersion = "0.0.1"


def ensure_app_folders():
    app_root = Path(__file__).resolve().parent
    base_folder = app_root / "IdeaFolder"
    ideas_folder = base_folder / "Ideas"
    in_progress_folder = base_folder / "InProgress"
    completed_folder = base_folder / "Completed"

    base_folder.mkdir(parents=True, exist_ok=True)
    ideas_folder.mkdir(parents=True, exist_ok=True)
    in_progress_folder.mkdir(parents=True, exist_ok=True)
    completed_folder.mkdir(parents=True, exist_ok=True)

    return {
        "app_root": app_root,
        "base_folder": base_folder,
        "ideas_folder": ideas_folder,
        "in_progress_folder": in_progress_folder,
        "completed_folder": completed_folder
    }


class Api:
    def __init__(self):
        folders = ensure_app_folders()
        self.base_folder = folders["base_folder"]
        self.ideas_folder = folders["ideas_folder"]
        self.in_progress_folder = folders["in_progress_folder"]
        self.completed_folder = folders["completed_folder"]

    def _safe_name(self, name: str) -> str:
        bad_chars = '<>:"/\\|?*'
        cleaned = "".join("_" if c in bad_chars else c for c in name).strip()
        return cleaned or "Untitled"

    def _get_in_progress_projects(self):
        return [item for item in self.in_progress_folder.iterdir() if item.is_dir()]

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
                "tasks": tasks
            }
            self._save_project_data(project_folder, project_data)
            return project_data

        return json.loads(json_path.read_text(encoding="utf-8"))

    def _save_project_data(self, project_folder: Path, project_data: dict):
        json_path = self._project_json_path(project_folder)
        json_path.write_text(
            json.dumps(project_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

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
                f"Completed: {'Yes' if task.get("done", False) else 'No'}",
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
                "tasks": []
            })

    def _serialize_project_state(self, project_folder: Path) -> dict:
        project_data = self._load_project_data(project_folder)
        return {
            "mode": "tasks",
            "projectName": project_data["name"],
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
            "taskIndex": task_index,
            "taskName": task["name"],
            "taskDone": task.get("done", False),
            "subtasks": task.get("subtasks", [])
        }

    def get_startup_state(self):
        current_project = self._get_current_project_folder()
        if current_project is None:
            return {"mode": "jar"}
        return self._serialize_project_state(current_project)

    def pick_idea(self):
        current_project = self._get_current_project_folder()
        if current_project is not None:
            return self._serialize_project_state(current_project)

        idea_folders = [folder for folder in self.ideas_folder.iterdir() if folder.is_dir()]

        if not idea_folders:
            return {"mode": "jar", "message": "No ideas found"}

        chosen_folder = random.choice(idea_folders)
        destination = self.in_progress_folder / chosen_folder.name

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

    def close_app(self):
        if webview.windows:
            webview.windows[0].destroy()


if __name__ == "__main__":
    ensure_app_folders()

    ui_file = Path(__file__).resolve().parent / "ui" / "index.html"

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