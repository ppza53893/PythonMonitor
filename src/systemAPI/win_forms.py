import inspect
import os
import sys
from typing import NoReturn, Tuple, Optional

from src.gname import PYTASKMGR
from src.utils import Icon, SystemIcons, close_container, container, forms


__all__ = ['error',
           'info',
           'question',
           'show_message_to_notification',
           'workingarea',
           'borders',
           'set_icon']


notifyicon = forms.NotifyIcon(container)
ICON = SystemIcons.Application


def set_icon(icon_path: str) -> None:
    """
    Set the icon of the application
    
    Args:
        icon_path (str): The path to the icon. It should be a .ico file.
    """
    global ICON

    _, ext = os.path.splitext(icon_path)
    if ext.lower() != '.ico':
        raise ValueError('The icon should be a .ico file')
    if os.path.exists(icon_path):
        ICON = Icon(icon_path)


def set_msg_type(buttontype: int, icon: int, exit_: bool,
                 window_name: str = PYTASKMGR,
                 compare_value: Optional[int] = None):
    """messagebox wrapper."""
    def wrap_base(func):
        def wrapper(message: str):
            result = forms.MessageBox.Show(message, window_name, buttontype, icon)
            if exit_:
                close_container()
                sys.exit(1)
            if compare_value is not None:
                return result == compare_value
            return result
        
        # copy docstrings
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        wrapper.__name__ = func.__name__
        wrapper.__signature__ = inspect.signature(func)
        
        return wrapper
    return wrap_base


@set_msg_type(buttontype=forms.MessageBoxButtons.OK,
              icon=forms.MessageBoxIcon.Error,
              exit_=True)
def error(message: str) -> NoReturn:
    """
    Show an error message box, and exit the application.
    
    Args:
        message (str): The message to show
    """
    pass


@set_msg_type(buttontype=forms.MessageBoxButtons.OK,
              icon=forms.MessageBoxIcon.Information,
              exit_=False)
def info(message: str) -> None:
    """
    Show an information message box
    
    Args:
        message (str): The message to show
    """
    pass


@set_msg_type(buttontype=forms.MessageBoxButtons.YesNo,
              icon=forms.MessageBoxIcon.Exclamation,
              exit_=False,
              compare_value=forms.DialogResult.Yes)
def question(message: str) -> bool:
    """
    Show a question message box
    
    Args:
        message (str): The message to show
    Returns:
        bool: True if the user clicked "Yes"
    """
    pass


def show_message_to_notification(message: str) -> None:
    """
    Show a message to the notification area
    
    Args:
        message (str): The message to show
        app_icon (str): The icon to show the message
    """
    notifyicon.Icon = ICON
    notifyicon.BalloonTipTitle = PYTASKMGR
    notifyicon.BalloonTipText = message
    notifyicon.Visible = True
    notifyicon.ShowBalloonTip(1)


def workingarea() -> Tuple[int, int]:
    """
    Get the working area of the screen.
    
    Returns:
        Tuple[int, int]: Screen width and height
    """
    width = forms.Screen.PrimaryScreen.WorkingArea.Width
    height = forms.Screen.PrimaryScreen.WorkingArea.Height
    return width, height


def borders() -> Tuple[int, int]:
    """
    Get the borders of the screen.
    
    Returns:
        Tuple[int, int]: FrameBorderSize and BorderSize.
    """
    frame_border = forms.SystemInformation.FrameBorderSize
    border = forms.SystemInformation.BorderSize
    return frame_border, border
