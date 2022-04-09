import ctypes


class PROCESS_DPI_AWARENESS:
    """
    https://docs.microsoft.com/en-us/windows/win32/api/shellscalingapi/ne-shellscalingapi-process_dpi_awareness
    """
    UNAWARE = 0
    SYSTEM_DPUI_AWARE = 1
    PER_MONITOR_DPI_AWARE = 2


DEFAULT_DPI = 96


def check_admin():
    from src.systemAPI.win_forms import error
    from src.utils.task import logger

    isadmin = ctypes.windll.shell32.IsUserAnAdmin()
    if isadmin == 0:
        error('管理者権限を有効にして実行してください。')
    else:
        logger.debug('Admin -> ok.')


def init_process():
    check_admin()
    ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_DPI_AWARENESS.PER_MONITOR_DPI_AWARE)
