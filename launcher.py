import sys
import os
import json
import shutil
import stat
import urllib.request
import zipfile
import subprocess
import threading
import tkinter as tk
from pathlib import Path

VERSION_URL = "https://asoody.com/programs/idea-jar/version.json"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

APP_PATH = BASE_DIR / "IdeaJar"
VERSION_FILE = BASE_DIR / "version.txt"

TEMP_DIR = BASE_DIR / "_update_tmp"
ZIP_PATH = BASE_DIR / "update.zip"


class StatusPopup:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Idea Jar")
        self.root.geometry("300x100")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        try:
            self.root.eval("tk::PlaceWindow . center")
        except Exception:
            pass

        self.label_var = tk.StringVar(value="Starting...")
        label = tk.Label(
            self.root,
            textvariable=self.label_var,
            font=("Arial", 11),
            padx=20,
            pady=20
        )
        label.pack(expand=True, fill="both")

        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

    def set_status(self, text: str):
        self.label_var.set(text)
        self.root.update_idletasks()

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass


def get_local_version():
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return "0.0.0"


def set_local_version(version):
    VERSION_FILE.write_text(version, encoding="utf-8")


def get_remote_version():
    try:
        with urllib.request.urlopen(VERSION_URL, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def download_file(url, dest):
    with urllib.request.urlopen(url) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out)


def make_executable(path: Path):
    try:
        current_mode = path.stat().st_mode
        path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def apply_update(zip_url, popup: StatusPopup):
    popup.set_status("Updating...")

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    download_file(zip_url, ZIP_PATH)

    with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
        zip_ref.extractall(TEMP_DIR)

    new_app = TEMP_DIR / "IdeaJar"
    new_version = TEMP_DIR / "version.txt"

    if not new_app.exists():
        raise Exception("Invalid update package")

    if APP_PATH.exists():
        APP_PATH.unlink()

    shutil.move(str(new_app), str(APP_PATH))
    make_executable(APP_PATH)

    if new_version.exists():
        shutil.move(str(new_version), str(VERSION_FILE))

    shutil.rmtree(TEMP_DIR)
    ZIP_PATH.unlink()


def launch_app(popup: StatusPopup):
    if not APP_PATH.exists():
        popup.set_status("App not found")
        popup.root.after(1500, popup.close)
        return

    popup.set_status("Launching Idea Jar...")

    env = os.environ.copy()
    env["IDEAJAR_STARTED_BY_LAUNCHER"] = "1"

    subprocess.Popen(
        [str(APP_PATH)],
        cwd=str(BASE_DIR),
        env=env
    )

    popup.root.after(500, popup.close)


def main_work(popup: StatusPopup):
    try:
        popup.set_status("Checking for update...")

        local_version = get_local_version()
        remote = get_remote_version()

        if remote:
            remote_version = remote.get("version")
            zip_url = remote.get("url")

            if remote_version and zip_url and remote_version != local_version:
                apply_update(zip_url, popup)

        launch_app(popup)

    except Exception as e:
        popup.set_status(f"Error: {e}")
        popup.root.after(2500, popup.close)


def main():
    popup = StatusPopup()

    thread = threading.Thread(target=main_work, args=(popup,), daemon=True)
    thread.start()

    popup.root.mainloop()


if __name__ == "__main__":
    main()