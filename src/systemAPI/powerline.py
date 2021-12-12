import re
import enum


from .win_forms import show_message_to_notification
from ..utils import StatusContainer
from ..utils import forms, dispose


__all__ = ['alert_on_balloontip', 'get_battery_status']


BATTERY_ALERT_MIN = 35
BATTERY_ALERT_MAX = 95
BATTERY_STATUS = 0


@enum.unique
class BatteryChargeStatus(enum.IntEnum):
    Charging = 8
    Critical = 4
    High = 1
    Low = 2
    Charging_and_High = Charging | High
    Charging_and_Low = Charging | Low
    Charging_and_Critical = Charging | Critical
    NoSystemBattery = 128
    Uncharged = 0
    Unknown = 255


@enum.unique
class PowerLineStatus(enum.IntEnum):
    Offline = 0
    Online = 1
    Unknown = 255


def alert_on_balloontip(
    remain: float,
    powerline_status: str) -> None:
    global BATTERY_STATUS
    
    charging = powerline_status == PowerLineStatus.Online
    
    if (remain <= BATTERY_ALERT_MIN and
        not charging and
        BATTERY_STATUS != BatteryChargeStatus.Critical):
        # 残量がないとき
        show_message_to_notification(
            message = f'残りバッテリ―容量が{remain}%です。ACアダプタを接続してください。')
        BATTERY_STATUS = BatteryChargeStatus.Critical
    elif (remain >= BATTERY_ALERT_MAX and
          charging and
          BATTERY_STATUS != BatteryChargeStatus.High):
        # 十分充電されたとき
        show_message_to_notification(
            message = 'PCは十分に充電されています。')
        BATTERY_STATUS = BatteryChargeStatus.High
    elif BATTERY_ALERT_MIN < remain < BATTERY_ALERT_MAX:
        # 特にないとき
        BATTERY_STATUS = BatteryChargeStatus.Uncharged


_re_and= re.compile(r'([a-zA-Z]+)\_([a-z]+)\_([a-zA-Z]+)')

def get_battery_status() -> StatusContainer:
    """Get current battery charge status.

    Returns:
        StatusContainer: powerline status, battery charge status and battery charge percentage.
    """
    powelinestatus = forms.SystemInformation.PowerStatus
    
    status = StatusContainer()
    powerline = powelinestatus.PowerLineStatus
    bcs = powelinestatus.BatteryChargeStatus
    for k, v in PowerLineStatus.__members__.items():
        if powerline == v: 
            status.register('PowerLineStatus', k)
            break
    if 'PowerLineStatus' not in status:
        status.register('PowerLineStatus', 'Unknown')
    status.register('BatteryLife', int(powelinestatus.BatteryLifePercent*100))
    for k, v in BatteryChargeStatus.__members__.items():
        if bcs == v:
            if _re_and.match(k) is not None:
                k = k.replace('_and_', '(') + ')'
            status.register('BatteryChargeStatus', k)
            break
    if 'BatteryChargeStatus' not in status:
        status.register('BatteryChargeStatus', 'Unknown')
    dispose(powelinestatus)
    return status
