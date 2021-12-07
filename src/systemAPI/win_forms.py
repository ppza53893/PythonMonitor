import os
import sys
from typing import NoReturn, Tuple

from ..gname import PYTASKMGR
from ..utils import Icon, SystemIcons, close_container, container, forms


__all__ = [
    'error',
    'info',
    'question',
    'ans_yes',
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


def _messagebox(
    message: str,
    buttontype: int,
    icon: int,
    exit_: bool):
    ret =  forms.MessageBox.Show(message, PYTASKMGR, buttontype, icon)
    if exit_:
        print(message)
        close_container()
        sys.exit(1)
    return ret


def error(message: str) -> NoReturn:
    """
    Show an error message box
    
    Args:
        message (str): The message to show
    """
    _messagebox(
        message = message,
        buttontype = forms.MessageBoxButtons.OK,
        icon = forms.MessageBoxIcon.Error,
        exit_ = True)


def info(message: str) -> None:
    """
    Show an information message box
    
    Args:
        message (str): The message to show
    """
    _messagebox(
        message = message,
        buttontype = forms.MessageBoxButtons.OK,
        icon = forms.MessageBoxIcon.Information,
        exit_ = False)


def question(message: str) -> bool:
    """
    Show a question message box
    
    Args:
        message (str): The message to show
    """
    return _messagebox(
        message=message,
        buttontype=forms.MessageBoxButtons.YesNo,
        icon=forms.MessageBoxIcon.Exclamation,
        exit_=False)
ans_yes: int = forms.DialogResult.Yes


def show_message_to_notification(
    message: str,
    app_icon: str) -> None:
    """
    Show a message to the notification area
    
    Args:
        message (str): The message to show
        app_icon (str): The icon to show the message
    """
    if os.path.exists(app_icon):
        icon = Icon(app_icon)
    else:
        icon = SystemIcons.Application

    notifyicon.Icon = icon
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

