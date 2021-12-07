import ctypes as _ctypes

from .network import *
from .powerline import *
from .process import *
from .win_forms import *

def isadmin():
    return _ctypes.windll.shell32.IsUserAnAdmin() != 0
