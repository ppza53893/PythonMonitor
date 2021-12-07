import re
import enum

from ..utils import StatusContainer
from ..utils import forms, dispose


__all__ = ['bcs_name_fix', 'get_battery_status']


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


_re_and= re.compile(r'([a-zA-Z]+)\_([a-z]+)\_([a-zA-Z]+)')


def bcs_name_fix():
    names = []
    for k in BatteryChargeStatus.__members__.keys():
        if _re_and.match(k) is not None:
            k = k.replace('_and_', '(') + ')'
        names.append(k)
    return names


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
    for k, v in BatteryChargeStatus.__members__.items():
        if bcs == v:
            if _re_and.match(k) is not None:
                k = k.replace('_and_', '(') + ')'
            status.register('BatteryChargeStatus', k)
            break
    if 'PowerLineStatus' not in status:
        status.register('PowerLineStatus', 'Unknown')
    if 'BatteryChargeStatus' not in status:
        status.register('BatteryChargeStatus', 'Unknown')
    status.register('BatteryLife', int(powelinestatus.BatteryLifePercent*100))
    dispose(powelinestatus)
    return status
