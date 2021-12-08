from .network import *
from .powerline import *
from .process import *
from .win_forms import *
from .gpu import *


def check_admin():
    import ctypes
    if ctypes.windll.shell32.IsUserAnAdmin() == 0:
        error('管理者権限を有効にして実行してください。')
