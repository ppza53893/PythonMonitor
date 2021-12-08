import dataclasses
import enum
import time
from typing import Tuple

from .systemAPI import ans_yes, error, get_battery_status, question
from .utils import StatusContainer, close_container, import_module

__all__ = ['OpenHardwareMonitor']


class HardWareType(enum.IntEnum):
    MainBoard = 0
    SuperIO = enum.auto()
    CPU = enum.auto()
    RAM = enum.auto()
    GpuNvidia = enum.auto()
    GPuAti = enum.auto()
    TBalancer = enum.auto()
    HeatMaster = enum.auto()
    HDD = enum.auto()


class SensorType(enum.IntEnum):
    Voltage = 0
    Clock = enum.auto()
    Temperature = enum.auto()
    Load = enum.auto()
    Fan = enum.auto()
    Flow = enum.auto()
    Control = enum.auto()
    Level = enum.auto()
    Factor = enum.auto()
    Power = enum.auto()
    Data = enum.auto()
    SmallData = enum.auto()
    Throughput = enum.auto()


sensortype_prefix = [
    'V', 'MHz', '°C', '%', 'RPM', 'L/h', '%', '%', 1, 'W', 'GB', 'MB', 'MB']


def hardware_getvaluetoname(value: int) -> str:
    for k, v in HardWareType.__members__.items():
        if v == value: return k


def sensor_getvaluetoname(value: int) -> Tuple[str, str]:
    for k, v in SensorType.__members__.items():
        if v == value:
            return k, sensortype_prefix[v]


@dataclasses.dataclass
class OpenHardwareMonitor:
    """
    OpenHardwareMonitorからの情報を取得する
    https://github.com/openhardwaremonitor/openhardwaremonitor/tree/master/Hardware
    """
    dllpath: str = 'OpenHardwareMonitorLib'
    
    def __post_init__(self) -> None:
        Hardware = import_module(
            self.dllpath, "OpenHardwareMonitor", 'Hardware')

        self._handle = Hardware.Computer()
        self._handle.CPUEnabled = True
        self._handle.RAMEnabled = True
        self._handle.GPUEnabled = True
        self._handle.Open()
        self._closed = False

    def curstatus(self)-> StatusContainer:
        self._container = StatusContainer()
        for sensors in self._handle.Hardware:
            # cpu, ram, ...
            self._parse_sensors(sensors)
        return self._container

    def _parse_sensors(self, sensors) -> None:
        sensors.Update()
        sensor_name = sensors.Sensors[0].Hardware.HardwareType
        key = hardware_getvaluetoname(sensor_name)

        keycontainer = StatusContainer()
        keycontainer.register('name', sensors.Name)
        register_dicts = dict()

        i_sensors = sorted(
            list(sensors.Sensors),
            key=lambda x: int(x.Identifier.ToString().split('/')[-1]))
        for sensor in i_sensors:
            # get sensortype
            # e.g. Temperature, Load, ...
            sensortype, format = sensor_getvaluetoname(sensor.SensorType)

            if sensortype not in register_dicts:
                register_dicts[sensortype] = []

            sensorcontainer = StatusContainer()
            values = dict(
                index = sensor.Index,
                name = sensor.Name,
                type = sensortype,
                identifier = sensor.Identifier.ToString(),
                value = sensor.Value,
                min = sensor.Min,
                max = sensor.Max,
                format = format)
            sensorcontainer.register('container', values)
            register_dicts[sensortype].append(sensorcontainer)

        keycontainer.register('size', len(register_dicts))
        for st, values in register_dicts.items():
            keycontainer.register(st, values)
        
        self._container.register(key, keycontainer)

    def close(self) -> None:
        if self._closed:
            return
        time.sleep(1)
        self._handle.Close()
        close_container()
        self._closed = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args, **kwargs):
        if not self._closed:
            self.close()

    @property
    def has_nvidia_gpu(self) -> bool:
        return 'GpuNvidia' in self.curstatus()
    
    def select_battery_or_gpu(self) -> bool:
        batteries = get_battery_status().BatteryChargeStatus
        has_battery = batteries not in ['NoSystemBattery', 'Unknown']
        has_nvgpu = self.has_nvidia_gpu
        if has_battery and has_nvgpu:
            result = question('Nvidia GPUを検出しました。バッテリ―状態の代わりに表示しますか?')
            return result != ans_yes
        else:
            return has_battery

    def i_cpu_size(self, key: str) -> int:
        status = self.curstatus().CPU
        if key in status:
            return len(getattr(status, key))
        else:
            # 見つからないとき
            self.close()
            error(f'OpenHardWareMonitor: {key}が見つかりませんでした。')
