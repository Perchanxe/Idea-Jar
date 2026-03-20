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

VERSION_URL = "https://www.asoody.com/programs/idea-jar/version.json"

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
        print(text, flush=True)
        self.label_var.set(text)
        self.root.update_idletasks()

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass


def get_local_version():
    if VERSION_FILE.exists():
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
        print(f"Local version: {version}", flush=True)
        return version
    print("Local version file missing, using 0.0.0", flush=True)
    return "0.0.0"


def set_local_version(version):
    VERSION_FILE.write_text(version, encoding="utf-8")


def get_remote_version():
    try:
        print(f"Fetching remote version from: {VERSION_URL}", flush=True)

        req = urllib.request.Request(
            VERSION_URL,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*"
            }
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            print(f"Remote raw response: {raw}", flush=True)
            parsed = json.loads(raw)
            print(f"Parsed remote JSON: {parsed}", flush=True)
            return parsed
    except Exception as e:
        print(f"Remote version check failed: {e}", flush=True)
        return None

def download_file(url, dest):
    print(f"Downloading file from: {url}", flush=True)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*"
        }
    )

    with urllib.request.urlopen(req, timeout=30) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out)

    print(f"Downloaded file to: {dest}", flush=True)


def make_executable(path: Path):
    try:
        current_mode = path.stat().st_mode
        path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Made executable: {path}", flush=True)
    except Exception as e:
        print(f"Failed to chmod {path}: {e}", flush=True)


def apply_update(zip_url, popup: StatusPopup):
    popup.set_status("Updating...")

    if TEMP_DIR.exists():
        print(f"Removing old temp dir: {TEMP_DIR}", flush=True)
        shutil.rmtree(TEMP_DIR)

    if ZIP_PATH.exists():
        print(f"Removing old zip: {ZIP_PATH}", flush=True)
        ZIP_PATH.unlink()

    download_file(zip_url, ZIP_PATH)

    print(f"Extracting zip to: {TEMP_DIR}", flush=True)
    with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
        zip_ref.extractall(TEMP_DIR)

    new_app = TEMP_DIR / "IdeaJar"
    new_version = TEMP_DIR / "version.txt"

    print(f"Looking for new app at: {new_app}", flush=True)
    print(f"Looking for new version file at: {new_version}", flush=True)

    if not new_app.exists():
        raise Exception("Invalid update package: IdeaJar not found in zip")

    if APP_PATH.exists():
        print(f"Removing old app: {APP_PATH}", flush=True)
        APP_PATH.unlink()

    print(f"Moving new app into place: {new_app} -> {APP_PATH}", flush=True)
    shutil.move(str(new_app), str(APP_PATH))
    make_executable(APP_PATH)

    if new_version.exists():
        print(f"Updating version file: {new_version} -> {VERSION_FILE}", flush=True)
        shutil.move(str(new_version), str(VERSION_FILE))
    else:
        print("No version.txt found in update zip", flush=True)

    print(f"Cleaning up temp dir: {TEMP_DIR}", flush=True)
    shutil.rmtree(TEMP_DIR)

    print(f"Cleaning up zip: {ZIP_PATH}", flush=True)
    ZIP_PATH.unlink()


def launch_app(popup: StatusPopup):
    print(f"Trying to launch app from: {APP_PATH}", flush=True)

    if not APP_PATH.exists():
        popup.set_status("App not found")
        print("App not found on disk", flush=True)
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

            print(f"Remote version: {remote_version}", flush=True)
            print(f"Remote zip URL: {zip_url}", flush=True)

            if remote_version and zip_url and remote_version != local_version:
                print("Update needed", flush=True)
                apply_update(zip_url, popup)
            else:
                print("No update needed", flush=True)
        else:
            print("Remote data was None, skipping update", flush=True)

        launch_app(popup)

    except Exception as e:
        print(f"Launcher error: {e}", flush=True)
        popup.set_status(f"Error: {e}")
        popup.root.after(2500, popup.close)


def main():
    print("Launcher started", flush=True)
    print(f"BASE_DIR: {BASE_DIR}", flush=True)
    print(f"APP_PATH: {APP_PATH}", flush=True)
    print(f"VERSION_FILE: {VERSION_FILE}", flush=True)

    popup = StatusPopup()

    thread = threading.Thread(target=main_work, args=(popup,), daemon=True)
    thread.start()

    popup.root.mainloop()


if __name__ == "__main__":
    main()