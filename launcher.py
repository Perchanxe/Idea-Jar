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
import platform
from pathlib import Path

VERSION_URL = "https://www.asoody.com/programs/idea-jar/version.json"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent


def get_install_dir() -> Path:
    """
    Purpose:
        Return the stable install directory for the current operating system.

    Parameters:
        None

    Return:
        Path: OS-specific install directory path.
    """
    system_name = platform.system()

    if system_name == "Windows":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "IdeaJar"
        return Path.home() / "AppData" / "Local" / "IdeaJar"

    if system_name == "Linux":
        return Path.home() / "IdeaJar"

    return BASE_DIR


INSTALL_DIR = get_install_dir()
APP_FILENAME = "IdeaJar.exe" if platform.system() == "Windows" else "IdeaJar"
APP_PATH = INSTALL_DIR / APP_FILENAME
VERSION_FILE = INSTALL_DIR / "version.txt"

TEMP_DIR = INSTALL_DIR / "_update_tmp"
ZIP_PATH = INSTALL_DIR / "update.zip"


class StatusPopup:
    """
    Purpose:
        Show a small status window while the launcher checks for updates
        and starts the main app.

    Parameters:
        None

    Return:
        StatusPopup: Popup controller instance.
    """

    def __init__(self):
        """
        Purpose:
            Create and configure the launcher status popup.

        Parameters:
            None

        Return:
            None
        """
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
        """
        Purpose:
            Update the popup label text and print the same status to stdout.

        Parameters:
            text (str): Status text to display.

        Return:
            None
        """
        print(text, flush=True)
        self.label_var.set(text)
        self.root.update_idletasks()

    def close(self):
        """
        Purpose:
            Close the popup window safely.

        Parameters:
            None

        Return:
            None
        """
        try:
            self.root.destroy()
        except Exception:
            pass


def ensure_install_dir():
    """
    Purpose:
        Ensure the OS-specific install directory exists before launch/update work.

    Parameters:
        None

    Return:
        None
    """
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)


def get_local_version():
    """
    Purpose:
        Read the locally installed app version from version.txt.

    Parameters:
        None

    Return:
        str: Local version string, or '0.0.0' if missing.
    """
    if VERSION_FILE.exists():
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
        print(f"Local version: {version}", flush=True)
        return version

    print("Local version file missing, using 0.0.0", flush=True)
    return "0.0.0"


def set_local_version(version):
    """
    Purpose:
        Write the provided version string to version.txt.

    Parameters:
        version (str): Version string to save.

    Return:
        None
    """
    VERSION_FILE.write_text(version, encoding="utf-8")


def get_remote_version():
    """
    Purpose:
        Fetch the remote version metadata JSON for the app update.

    Parameters:
        None

    Return:
        dict | None:
            Parsed JSON metadata if successful, otherwise None.
    """
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
    """
    Purpose:
        Download a file from a URL to a destination path.

    Parameters:
        url (str): Source download URL.
        dest (Path | str): Destination file path.

    Return:
        None
    """
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
    """
    Purpose:
        Add executable permissions to a file on Unix-like systems.

    Parameters:
        path (Path): File path to mark executable.

    Return:
        None
    """
    if platform.system() == "Windows":
        return

    try:
        current_mode = path.stat().st_mode
        path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Made executable: {path}", flush=True)
    except Exception as e:
        print(f"Failed to chmod {path}: {e}", flush=True)


def find_extracted_app(temp_dir: Path) -> Path | None:
    """
    Purpose:
        Find the extracted app binary inside the update temp directory.

    Parameters:
        temp_dir (Path): Temporary extraction directory.

    Return:
        Path | None: Path to the extracted app binary, or None if missing.
    """
    direct_path = temp_dir / APP_FILENAME
    if direct_path.exists():
        return direct_path

    nested_path = temp_dir / "IdeaJar" / APP_FILENAME
    if nested_path.exists():
        return nested_path

    for candidate in temp_dir.rglob(APP_FILENAME):
        if candidate.is_file():
            return candidate

    return None


def find_extracted_version_file(temp_dir: Path) -> Path | None:
    """
    Purpose:
        Find the extracted version.txt file inside the update temp directory.

    Parameters:
        temp_dir (Path): Temporary extraction directory.

    Return:
        Path | None: Path to version.txt, or None if missing.
    """
    direct_path = temp_dir / "version.txt"
    if direct_path.exists():
        return direct_path

    nested_path = temp_dir / "IdeaJar" / "version.txt"
    if nested_path.exists():
        return nested_path

    for candidate in temp_dir.rglob("version.txt"):
        if candidate.is_file():
            return candidate

    return None


def apply_update(zip_url, popup: StatusPopup):
    """
    Purpose:
        Download and apply an app update from the provided zip URL.

    Parameters:
        zip_url (str): URL of the update zip file.
        popup (StatusPopup): Popup instance used for status updates.

    Return:
        None
    """
    popup.set_status("Updating...")
    ensure_install_dir()

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

    new_app = find_extracted_app(TEMP_DIR)
    new_version = find_extracted_version_file(TEMP_DIR)

    print(f"Looking for new app. Found: {new_app}", flush=True)
    print(f"Looking for new version file. Found: {new_version}", flush=True)

    if new_app is None or not new_app.exists():
        raise Exception(f"Invalid update package: {APP_FILENAME} not found in zip")

    if APP_PATH.exists():
        print(f"Removing old app: {APP_PATH}", flush=True)
        APP_PATH.unlink()

    print(f"Moving new app into place: {new_app} -> {APP_PATH}", flush=True)
    shutil.move(str(new_app), str(APP_PATH))
    make_executable(APP_PATH)

    if new_version is not None and new_version.exists():
        print(f"Updating version file: {new_version} -> {VERSION_FILE}", flush=True)
        if VERSION_FILE.exists():
            VERSION_FILE.unlink()
        shutil.move(str(new_version), str(VERSION_FILE))
    else:
        print("No version.txt found in update zip", flush=True)

    print(f"Cleaning up temp dir: {TEMP_DIR}", flush=True)
    shutil.rmtree(TEMP_DIR)

    print(f"Cleaning up zip: {ZIP_PATH}", flush=True)
    ZIP_PATH.unlink()


def launch_app(popup: StatusPopup):
    """
    Purpose:
        Launch the main IdeaJar app binary and mark it as started by the launcher.

    Parameters:
        popup (StatusPopup): Popup instance used for status updates.

    Return:
        None
    """
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
        cwd=str(INSTALL_DIR),
        env=env
    )

    popup.root.after(500, popup.close)


def main_work(popup: StatusPopup):
    """
    Purpose:
        Run the launcher workflow:
        check for updates, apply update if needed, then launch the app.

    Parameters:
        popup (StatusPopup): Popup instance used for status updates.

    Return:
        None
    """
    try:
        ensure_install_dir()
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
    """
    Purpose:
        Start the launcher UI and background worker thread.

    Parameters:
        None

    Return:
        None
    """
    print("Launcher started", flush=True)
    print(f"BASE_DIR: {BASE_DIR}", flush=True)
    print(f"INSTALL_DIR: {INSTALL_DIR}", flush=True)
    print(f"APP_PATH: {APP_PATH}", flush=True)
    print(f"VERSION_FILE: {VERSION_FILE}", flush=True)
    print(f"TEMP_DIR: {TEMP_DIR}", flush=True)
    print(f"ZIP_PATH: {ZIP_PATH}", flush=True)

    popup = StatusPopup()

    thread = threading.Thread(target=main_work, args=(popup,), daemon=True)
    thread.start()

    popup.root.mainloop()


if __name__ == "__main__":
    main()