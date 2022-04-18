import ctypes
from ctypes import wintypes, pointer
from functools import partial


AWARENESS_OK = False
# TODO: Class

class PROCESS_DPI_AWARENESS:
    """
    https://docs.microsoft.com/en-us/windows/win32/api/shellscalingapi/ne-shellscalingapi-process_dpi_awareness
    """
    UNAWARE = 0
    SYSTEM_DPUI_AWARE = 1
    PER_MONITOR_DPI_AWARE = 2


dwFlags_dict = {"MONITOR_DEFAULTTONEAREST": 2,
                "MONITOR_DEFAULTTONULL": 0,
                "MONITOR_DEFAULTTOPRIMARY": 1}


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG)]


class tagMONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD)]


def tagMONITORINFO_init():
    monitorinfo = tagMONITORINFO()
    monitorinfo.cbSize = ctypes.sizeof(monitorinfo)
    monitorinfo.rcMonitor = RECT()
    monitorinfo.rcWork = RECT()
    return monitorinfo


def _setDpiAwareness():
    global AWARENESS_OK
    if AWARENESS_OK:
        return
    ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_DPI_AWARENESS.PER_MONITOR_DPI_AWARE)
    AWARENESS_OK = True


def _MonitorFromWindow(hwnd: int, dwFlags):
    return ctypes.windll.user32.MonitorFromWindow(hwnd, dwFlags)


def _GetDpiForMonitor(hmonitor: int, dpiType: int, dpix: pointer, dpiy: pointer):
    ctypes.windll.shcore.GetDpiForMonitor(hmonitor, dpiType, dpix, dpiy)


def _check_admin():
    from src.systemAPI.win_forms import error
    from src.utils.task import logger

    isadmin = ctypes.windll.shell32.IsUserAnAdmin()
    if isadmin == 0:
        error('管理者権限を有効にして実行してください。')
    else:
        logger.debug('Admin -> ok.')


def getTaskBarHeight(handler: int) -> int:
    hwnd = wintypes.HWND(handler)
    hmonitor = _MonitorFromWindow(hwnd, dwFlags_dict['MONITOR_DEFAULTTONEAREST'])
    monitorinfo = tagMONITORINFO_init()
    ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(monitorinfo))
    
    return monitorinfo.rcMonitor.bottom - monitorinfo.rcWork.bottom


def getWindowDPI(handler: int, mode='MONITOR_DEFAULTTONEAREST'):
    _setDpiAwareness()
    hwnd = wintypes.HWND(handler)
    hmonitor = _MonitorFromWindow(hwnd, dwFlags_dict[mode])
    
    pX, pY = wintypes.UINT(), wintypes.UINT()
    
    _GetDpiForMonitor(hmonitor, 0, pointer(pX), pointer(pY))
    monitorinfo = tagMONITORINFO()
    ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(monitorinfo))
    return pX.value, pY.value


getNearestWindowDPI = partial(getWindowDPI, mode='MONITOR_DEFAULTTONEAREST')


def dpi_changed(handler: int, current_dpi: int):
    current_dpi = tuple([current_dpi] * 2)
    return getNearestWindowDPI(handler) != current_dpi


def getDpiFactor(handler: int, current_dpi: int):
    x, y = getNearestWindowDPI(handler)
    cx, cy = current_dpi, current_dpi
    return x/cx, y/cy, min(x, y)


def init_process():
    _check_admin()
    _setDpiAwareness()

