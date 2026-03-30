import json
import sys
from pathlib import Path


def get_app_root() -> Path:
    """
    Purpose:
        Return the root folder where the app is running from.

    Parameters:
        None

    Return:
        Path: The resolved application root path.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_ui_file() -> Path:
    """
    Purpose:
        Return the path to the UI entry file for pywebview.

    Parameters:
        None

    Return:
        Path: Path to the UI index.html file.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "ui" / "index.html"
    return Path(__file__).resolve().parent / "ui" / "index.html"


def ensure_app_folders():
    """
    Purpose:
        Ensure the base Idea Jar folder structure exists for the jar-first version
        of the app.

    Parameters:
        None

    Return:
        dict: A dictionary containing resolved paths used by the backend.
    """
    app_root = get_app_root()
    base_folder = app_root / "IdeaFolder"
    jars_root = base_folder / "Jars"
    jars_file = base_folder / "jars.json"

    base_folder.mkdir(parents=True, exist_ok=True)
    jars_root.mkdir(parents=True, exist_ok=True)

    if not jars_file.exists():
        jars_file.write_text("[]", encoding="utf-8")

    try:
        data = json.loads(jars_file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            jars_file.write_text("[]", encoding="utf-8")
    except Exception:
        jars_file.write_text("[]", encoding="utf-8")

    return {
        "app_root": app_root,
        "base_folder": base_folder,
        "jars_root": jars_root,
        "jars_file": jars_file,
    }