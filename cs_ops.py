import enum
import functools
import inspect
import os
import re
import sys
import time
from typing import Any, Callable, Dict, NoReturn, Tuple

import clr

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Management')
clr.AddReference('System.ComponentModel.Primitives')
clr.AddReference('System.Runtime.InteropServices')
clr.AddReference('System.Drawing')
clr.AddReference('System.Net.NetworkInformation')
clr.AddReference('System.Diagnostics.Process')

import System as sys_win  # type: ignore
import System.Diagnostics as diagnostics  # type: ignore
import System.Management as management  # type: ignore
import System.Windows.Forms as forms  # type: ignore
from System.ComponentModel import Container  # type: ignore
from System.Drawing import Icon, SystemIcons  # type: ignore
from System.Net.NetworkInformation import NetworkInterface  # type: ignore


PYTASKMGR = 'PyTaskManager'
if not __debug__:
    PYTASKMGR += ' (Debug Mode)'


#system
wmi_class_tag = {
    'Win32_Battery': [
        'Availability',
        'BatteryRechargeTime',
        'BatteryStatus',
        'Caption',
        'Chemistry',
        'ConfigManagerErrorCode',
        'ConfigManagerUserConfig',
        'CreationClassName',
        'Description',
        'DesignCapacity',
        'DesignVoltage',
        'DeviceID',
        'ErrorCleared',
        'ErrorDescription',
        'EstimatedChargeRemaining',
        'EstimatedRunTime',
        'ExpectedBatteryLife',
        'ExpectedLife',
        'FullChargeCapacity',
        'datetime InstallDate',
        'LastErrorCode',
        'MaxRechargeTime',
        'Name',
        'PNPDeviceID',
        'PowerManagementCapabilities',
        'PowerManagementSupported',
        'SmartBatteryVersion',
        'Status',
        'StatusInfo',
        'SystemCreationClassName',
        'SystemName',
        'TimeOnBattery',
        'TimeToFullCharge'],
    'Win32_BIOS': [
        'BiosCharacteristics',
        'BIOSVersion',
        'BuildNumber',
        'Caption',
        'CodeSet',
        'CurrentLanguage',
        'Description',
        'EmbeddedControllerMajorVersion',
        'EmbeddedControllerMinorVersion',
        'IdentificationCode',
        'InstallableLanguages',
        'InstallDate',
        'LanguageEdition',
        'ListOfLanguages',
        'Manufacturer',
        'Name',
        'OtherTargetOS',
        'PrimaryBIOS',
        'ReleaseDate',
        'SerialNumber',
        'SMBIOSBIOSVersion',
        'SMBIOSMajorVersion',
        'SMBIOSMinorVersion',
        'SMBIOSPresent',
        'SoftwareElementID',
        'SoftwareElementState',
        'Status',
        'SystemBiosMajorVersion',
        'SystemBiosMinorVersion',
        'TargetOperatingSystem',
        'Version'],
    'Win32_DiskPartition': [
        'AdditionalAvailability',
        'Availability',
        'PowerManagementCapabilities',
        'IdentifyingDescriptions',
        'MaxQuiesceTime',
        'OtherIdentifyingInfo',
        'StatusInfo',
        'PowerOnHours',
        'TotalPowerOnHours',
        'Access',
        'BlockSize',
        'Bootable',
        'BootPartition',
        'Caption',
        'ConfigManagerErrorCode',
        'ConfigManagerUserConfig',
        'CreationClassName',
        'Description',
        'DeviceID',
        'DiskIndex',
        'ErrorCleared',
        'ErrorDescription',
        'ErrorMethodology',
        'HiddenSectors',
        'Index',
        'InstallDate',
        'LastErrorCode',
        'Name',
        'NumberOfBlocks',
        'PNPDeviceID',
        'PowerManagementSupported',
        'PrimaryPartition',
        'Purpose',
        'RewritePartition',
        'Size',
        'StartingOffset',
        'Status',
        'SystemCreationClassName',
        'SystemName',
        'Type'],
    'Win32_PhysicalMemory': [
        'Attributes',
        'BankLabel',
        'Capacity',
        'Caption',
        'ConfiguredClockSpeed',
        'ConfiguredVoltage',
        'CreationClassName',
        'DataWidth',
        'Description',
        'DeviceLocator',
        'FormFactor',
        'HotSwappable',
        'InstallDate',
        'InterleaveDataDepth',
        'InterleavePosition',
        'Manufacturer',
        'MaxVoltage',
        'MemoryType',
        'MinVoltage',
        'Model',
        'Name',
        'OtherIdentifyingInfo',
        'PartNumber',
        'PositionInRow',
        'PoweredOn',
        'Removable',
        'Replaceable',
        'SerialNumber',
        'SKU',
        'SMBIOSMemoryType',
        'Speed',
        'Status',
        'Tag',
        'TotalWidth',
        'TypeDetail',
        'Version'],
    "Win32_OperatingSystem": [
        'BootDevice',
        'BuildNumber',
        'BuildType',
        'Caption',
        'CodeSet',
        'CountryCode',
        'CreationClassName',
        'CSCreationClassName',
        'CSDVersion',
        'CSName',
        'CurrentTimeZone',
        'DataExecutionPrevention_Available',
        'DataExecutionPrevention_32BitApplications',
        'DataExecutionPrevention_Drivers',
        'DataExecutionPrevention_SupportPolicy',
        'Debug',
        'Description',
        'Distributed',
        'EncryptionLevel',
        'ForegroundApplicationBoost',
        'FreePhysicalMemory',
        'FreeSpaceInPagingFiles',
        'FreeVirtualMemory',
        'InstallDate',
        'LargeSystemCache',
        'LastBootUpTime',
        'LocalDateTime',
        'Locale',
        'Manufacturer',
        'MaxNumberOfProcesses',
        'MaxProcessMemorySize',
        'MUILanguages',
        'Name',
        'NumberOfLicensedUsers',
        'NumberOfProcesses',
        'NumberOfUsers',
        'OperatingSystemSKU',
        'Organization',
        'OSArchitecture',
        'OSLanguage',
        'OSProductSuite',
        'OSType',
        'OtherTypeDescription',
        'PAEEnabled',
        'PlusProductID',
        'PlusVersionNumber',
        'PortableOperatingSystem',
        'Primary',
        'ProductType',
        'RegisteredUser',
        'SerialNumber',
        'ServicePackMajorVersion',
        'ServicePackMinorVersion',
        'SizeStoredInPagingFiles',
        'Status',
        'SuiteMask',
        'SystemDevice',
        'SystemDirectory',
        'SystemDrive',
        'TotalSwapSpaceSize',
        'TotalVirtualMemorySize',
        'TotalVisibleMemorySize',
        'Version',
        'WindowsDirectory',
        'QuantumLength',
        'QuantumType']}


container = Container()
notifyicon = forms.NotifyIcon(container)
available_memory = None
total_memory = None


re_and_ = re.compile(r'([a-zA-Z]+)\_([a-z]+)\_([a-zA-Z]+)')


def private(func: Callable[..., Any]):
    """Private function decorator"""
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        cls = self.__class__
        caller = inspect.currentframe().f_back.f_locals
        if 'self' in caller and cls == caller['self'].__class__:
            return func(self, *args, **kwargs)
        raise PermissionError("Cannot call '{}' method outside '{}' class."
                        .format(func.__name__, cls.__name__))
    return wrap


class StatusContainer:
    def __str__(self) -> str:
        s = 'Registered variables:\n'
        for k, v in self._registerd_vars.items():
            if isinstance(v, StatusContainer):
                v = '\n\t'+str(v).replace('\n', '\n\t') + '\n'
            elif isinstance(v, (list, tuple)):
                rv = '(size: {})\n\t'.format(len(v))
                for _v in v:
                    rv += str(_v).replace('\n', '\n\t') + '\n\t'
                v = rv[:-2]
            else:
                v = str(v)
            s += '\t'+ k.ljust(50) + v + '\n'
        return s[:-1]

    def __repr__(self) -> str:
        return str(self)
    
    def __len__(self):
        return len(self._registerd_vars)

    def __contains__(self, other: str) -> bool:
        assert isinstance(other, str), f'Instance targets must be str, not {other}.'
        return other in self._registerd_vars
    
    def __setattr__(self, name: str, value: dict) -> None:
        if isinstance(value, dict) and 'from_register' in value:
            super().__setattr__(name, value['value'])
        else:
            raise ValueError('You should call setattr method from `register`.')

    @property
    def isempty(self) -> bool:
        return len(self) == 0

    @private
    def _setname(self, name, index) -> str:
        if not hasattr(self, name):
            return name
        x = name + f'_{index}'
        if not hasattr(self, x):
            return x
        return self._setname(name, index+1)

    def register(self, name: str, value):
        if hasattr(value, 'ForEach'): # c# array
            value = list(value)
        elif isinstance(value, dict):
            s = StatusContainer()
            for k, v in value.items():
                s.register(k, v)
            value = s
        value = dict(value=value, from_register=True)
        setattr(self, self._setname(name, 1), value)

    @private
    def to_(self, value, attr: str):
        assert attr in ['tolist', 'todict']
        if not isinstance(value, StatusContainer):
            return value
        return getattr(value, attr)()

    def tolist(self):
        """deep list"""
        ret = []
        for t in self._registerd_vars.values():
            t = self.to_(t, 'tolist')
            if isinstance(t, (list, tuple)):
                t = [self.to_(_t, 'tolist') for _t in t]
            ret.append(t)
        return ret

    def todict(self) -> Dict[str, Any]:
        """deep dict"""
        ret = dict()
        for k, v in self._registerd_vars.items():
            v = self.to_(v, 'todict')
            if isinstance(v, (list, tuple)):
                v = [self.to_(_v, 'todict') for _v in v]
            ret[k] = v
        return ret

    @property
    @private
    def _registerd_vars(self) -> dict:
        try:
            return vars(self)
        except:
            return dict()


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


def bcs_name_fix():
    names = []
    for k in BatteryChargeStatus.__members__.keys():
        if re_and_.match(k) is not None:
            k = k.replace('_and_', '(') + ')'
        names.append(k)
    return names


def close(*disposeobjects):
    for obj in disposeobjects:
        if hasattr(obj, 'Dispose'):
            obj.Dispose()


def get_battery_status() -> StatusContainer:
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
            if re_and_.match(k) is not None:
                k = k.replace('_and_', '(') + ')'
            status.register('BatteryChargeStatus', k)
            break
    if 'PowerLineStatus' not in status:
        status.register('PowerLineStatus', 'Unknown')
    if 'BatteryChargeStatus' not in status:
        status.register('BatteryChargeStatus', 'Unknown')
    status.register('BatteryLife', int(powelinestatus.BatteryLifePercent*100))
    close(powelinestatus)
    return status


def _wmi_info(target: str) -> StatusContainer:
    mc = management.ManagementClass(target)

    moc = mc.GetInstances()
    status = StatusContainer()
    for mo in moc:
        for name in wmi_class_tag[target]:
            try:
                res = mo.get_Item(name)
                if res is None: continue
                status.register(name, res)
            except:
                pass
    close(moc, mc)
    return status


def diskpartition() -> StatusContainer:
    return _wmi_info('Win32_DiskPartition')


def bios() -> StatusContainer:
    return _wmi_info('Win32_BIOS')


def battery() -> StatusContainer:
    return _wmi_info('Win32_Battery')


def memory() -> StatusContainer:
    return _wmi_info('Win32_PhysicalMemory')


def sysinfo() -> StatusContainer:
    return _wmi_info('Win32_OperatingSystem')


def get_networks() -> StatusContainer:
    status = StatusContainer()
    adapters = NetworkInterface.GetAllNetworkInterfaces()
    for adapter in adapters:
        stats = adapter.GetIPv4Statistics()
        if adapter.Speed != -1 and stats.BytesReceived != 0:
            status.register('adapter', adapter)
            break
    return status


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


error: Callable[[str], NoReturn] = lambda message: _messagebox(
    message=message,
    buttontype=forms.MessageBoxButtons.OK,
    icon = forms.MessageBoxIcon.Error,
    exit_ = True)
info: Callable[[str], NoReturn] = lambda message: _messagebox(
    message=message,
    buttontype=forms.MessageBoxButtons.OK,
    icon = forms.MessageBoxIcon.Information,
    exit_ = False)
question: Callable[[str], bool] = lambda message: _messagebox(
    message=message,
    buttontype=forms.MessageBoxButtons.YesNo,
    icon = forms.MessageBoxIcon.Exclamation,
    exit_ = False)
ans_yes: int = forms.DialogResult.Yes


def show_notification(
    message: str,
    app_icon: str) -> None:

    app_icon = app_icon
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
    width = forms.Screen.PrimaryScreen.WorkingArea.Width
    height = forms.Screen.PrimaryScreen.WorkingArea.Height
    return width, height


def borders() -> Tuple[int, int]:
    frame_border = forms.SystemInformation.FrameBorderSize
    border = forms.SystemInformation.BorderSize
    return frame_border, border


def get_current_pids() -> list:
    return list(diagnostics.Process.GetProcesses())


def num_processors() -> int:
    return sys_win.Environment.ProcessorCount


def cpu_usage() -> list:
    target = ['_Total'] + list(range(sys_win.Environment.ProcessorCount))
    cpus = []
    for t in target:
        cpus.append(diagnostics.PerformanceCounter("Processor", "% Processor Time", f"{t}"))
    for cpu in cpus:
        _ = cpu.NextValue()
    time.sleep(1)
    return cpus


def memory_usage(refresh=False) -> float:
    global available_memory, total_memory
    if available_memory is None or refresh:
        available_memory = diagnostics.PerformanceCounter("Memory", 'Available KBytes', None)
        total_memory = sysinfo().TotalVisibleMemorySize
    return round(100*(total_memory - available_memory.NextValue())/total_memory, 2)


def close_container():
    try:
        close(container)
    except: pass

def _a():
    """unused."""
    return
    for x in list(diagnostics.PerformanceCounterCategory.GetCategories()): print(x.CategoryName)

    for x in diagnostics.PerformanceCounterCategory("Memory").GetCounters(): 
        s = x.get_CounterName()
        try:diag = diagnostics.PerformanceCounter("Memory", s, None)
        except:  continue
        r = diag.NextValue();print(s.ljust(50), round(r, 2))
        #print(x.get_CounterName())

    # Committed Bytes, Commit Limit

    #print(list(diagnostics.PerformanceCounterCategory('PhysicalDisk').GetInstanceNames()))

    #x = diagnostics.PerformanceCounter("Memory", "Available Bytes", None)
    #print(x.NextValue())
    #print(sysinfo())
