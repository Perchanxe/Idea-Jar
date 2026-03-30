import os
import subprocess

from app_paths import get_app_root


def ensure_started_via_launcher() -> bool:
    """
    Purpose:
        Ensure the app starts through the existing launcher binary when applicable.

    Parameters:
        None

    Return:
        bool:
            True if the app should continue starting normally.
            False if control was handed off to the launcher.
    """
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