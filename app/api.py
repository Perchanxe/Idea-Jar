import webview

from jar_storage import JarStorage


class Api(JarStorage):
    """
    Purpose:
        Expose backend storage methods to the pywebview frontend.

    Parameters:
        None

    Return:
        Api: Webview API instance.
    """

    def __init__(self):
        """
        Purpose:
            Initialize the API and storage layer.

        Parameters:
            None

        Return:
            None
        """
        super().__init__()

    def resize_window(self, width: int, height: int):
        """
        Purpose:
            Resize the pywebview window.

        Parameters:
            width (int): New width.
            height (int): New height.

        Return:
            None
        """
        if webview.windows:
            webview.windows[0].resize(width, height)

    def close_app(self):
        """
        Purpose:
            Close the pywebview application window.

        Parameters:
            None

        Return:
            None
        """
        if webview.windows:
            webview.windows[0].destroy()