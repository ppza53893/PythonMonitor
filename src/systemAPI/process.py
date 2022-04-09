
import shutil
import time
from typing import List, TypeVar

from src.utils import StatusContainer, diagnostics, dispose, management, system


__all__ = [
    'diskpartition',
    'bios',
    'battery',
    'memory',
    'operating_system',
    'num_processors',
    'cpu_usage',
    'get_current_pids',
    'c_disk_usage']


PerformanceCounter = TypeVar('PerformanceCounter')
Process = TypeVar('Process')

WMI_CLASS_TAG = {
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
available_memory = None
total_memory = None


def _wmi_info(target: str) -> StatusContainer:
    """Get WMI data for a given target.

    Args:
        target (str): The target to get info for.
        Must be in the WMI_INFO_TARGETS dict.

    Returns:
        StatusContainer: Status.
    """
    mc = management.ManagementClass(target)

    moc = mc.GetInstances()
    status = StatusContainer()
    for mo in moc:
        for name in WMI_CLASS_TAG[target]:
            try:
                res = mo.get_Item(name)
                if res is None: continue
                status.register(name, res)
            except:
                pass
    dispose(moc, mc)
    return status


def diskpartition() -> StatusContainer:
    """Get disk partition data.
    
    See also:
    https://docs.microsoft.com/en-us/windows/win32/cimwin32prov/win32-diskpartition

    Returns:
        StatusContainer: Status.
    """
    return _wmi_info('Win32_DiskPartition')


def bios() -> StatusContainer:
    """Get BIOS data.
    
    See also:
    https://docs.microsoft.com/en-us/windows/win32/cimwin32prov/win32-bios

    Returns:
        StatusContainer: Status.
    """
    return _wmi_info('Win32_BIOS')


def battery() -> StatusContainer:
    """Get battery data.
    
    See also:
    https://docs.microsoft.com/en-us/windows/win32/cimwin32prov/win32-bios

    Returns:
        StatusContainer: Status.
    """
    return _wmi_info('Win32_Battery')


def memory() -> StatusContainer:
    """Get memory data.
    
    See also:
    https://docs.microsoft.com/en-us/windows/win32/cimwin32prov/win32-physicalmemory

    Returns:
        StatusContainer: Status.
    """
    return _wmi_info('Win32_PhysicalMemory')


def operating_system() -> StatusContainer:
    """Get operating system data.

    See also:
    https://docs.microsoft.com/en-us/windows/win32/cimwin32prov/win32-operatingsystem

    Returns:
        StatusContainer: Status.
    """
    return _wmi_info('Win32_OperatingSystem')


def num_processors() -> int:
    """Get the number of processors.

    Returns:
        int: Number of processors.
    """
    return system.Environment.ProcessorCount


def cpu_usage() -> List[PerformanceCounter]:
    """
    Get the usage of each CPU processor.
    
    This function should only be called once, because it calls the processor counter.

    Returns:
        List[PerformanceCounter]: List of PerformanceCounter objects.
    """
    target = ['_Total'] + list(range(num_processors()))
    cpus = []
    for t in target:
        cpus.append(diagnostics.PerformanceCounter("Processor", "% Processor Time", f"{t}"))
    for cpu in cpus:
        cpu.NextValue()
    time.sleep(1)
    return cpus


def get_current_pids() -> int:
    """Get the current running processes.

    Returns:
        int: Number of processes.
    """
    return len(list(diagnostics.Process.GetProcesses()))


def c_disk_usage() -> float:
    """Get disk usage.

    Returns:
        float: Disk usage (%).
    """
    total, used, _ = shutil.disk_usage('c:\\')
    return round(100*used / total, 1)
