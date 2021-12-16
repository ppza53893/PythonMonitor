from .network import Network

from .powerline import alert_on_balloontip
from .powerline import get_battery_status

from .process import diskpartition
from .process import bios
from .process import battery
from .process import memory
from .process import operating_system
from .process import num_processors
from .process import cpu_usage
from .process import get_current_pids
from .process import c_disk_usage

from .win_forms import error
from .win_forms import info
from .win_forms import question
from .win_forms import ans_yes
from .win_forms import show_message_to_notification
from .win_forms import workingarea
from .win_forms import borders
from .win_forms import set_icon

from .gpu import nvidia_smi_update
from .gpu import is_nvidia_smi_available
from .gpu import gpu_power_limit
from .gpu import gpu_fan_speed

def check_admin():
    import ctypes
    if ctypes.windll.shell32.IsUserAnAdmin() == 0:
        error('管理者権限を有効にして実行してください。')
