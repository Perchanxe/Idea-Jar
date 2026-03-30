import sys

import webview

from api import Api
from app_paths import ensure_app_folders, get_ui_file
from startup_guard import ensure_started_via_launcher


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
        width=260,
        height=270
    )

    webview.start()