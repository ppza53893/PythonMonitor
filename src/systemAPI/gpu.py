import os
import re
import subprocess
import sys
import time
from typing import Union

from src.utils.csharp_modules import Diagnostics, System
from src.utils.pythonnet import import_module

__all__ = ['nvidia_smi_update',
           'is_nvidia_smi_available',
           'gpu_power_limit',
           'gpu_fan_speed',
           'NetGPU']

NVSMI_QUERIES = [
    'nvidia-smi', '-i', '0',
    '--query-gpu=enforced.power.limit,fan.speed',
    '--format=csv,noheader,nounits']
GPU_MAX_POWER = None
GPU_FAN_SPEED = None
EXECUTABLE_NAME = os.path.splitext(os.path.basename(sys.executable))[0]


def nvidia_smi_update() -> None:
    global GPU_MAX_POWER, GPU_FAN_SPEED
    if GPU_MAX_POWER != 'DISABLERD' and GPU_FAN_SPEED != 'DISABLERD':
        if EXECUTABLE_NAME != 'pythonw':
            # Calling nvidia-smi from pythonw is disabled 
            # because it launches the command prompt every time
            try:
                enf_power, fan_speed = map(float,
                            (subprocess.run(NVSMI_QUERIES, stdout=subprocess.PIPE, shell=True).stdout
                             .decode('utf-8')
                             .replace('\r', '')
                             .replace('\n', '')
                             .replace(' ', '')
                             .split(',')))
                GPU_MAX_POWER = enf_power
                GPU_FAN_SPEED = fan_speed
            except:
                GPU_MAX_POWER = 'DISABLERD'
                GPU_FAN_SPEED = 'DISABLERD'
        else:
            GPU_MAX_POWER = 'DISABLERD'
            GPU_FAN_SPEED = 'DISABLERD'


def _check_update(function = None,
                  power: bool = False,
                  fan: bool = False) -> None:
    def wrap_fn(f):
        def wrap():
            cond = False
            if power:
                cond = cond or GPU_MAX_POWER is None
            if fan:
                cond = cond or GPU_FAN_SPEED is None
            if cond:
                nvidia_smi_update()
            return f()
        return wrap
    if function:
        return wrap_fn(function)
    return wrap_fn


@_check_update(power=True, fan=True)
def is_nvidia_smi_available() -> bool:
    return GPU_MAX_POWER != 'DISABLERD' and GPU_FAN_SPEED != 'DISABLERD'


@_check_update(power=True)
def gpu_power_limit() -> Union[float, str]:
    return GPU_MAX_POWER


@_check_update(fan=True)
def gpu_fan_speed() -> Union[float, str]:
    return GPU_FAN_SPEED


class DLL_NetGPU:
    def __init__(self):
        self.gpu = import_module('./src/systemAPI/dll/GPUUsage.dll',
                                 'GPUUsage', 'GPU')()

    def __call__(self):
        return self.gpu.Usage()


class PY_NetGPU:
    def __init__(self):
        # List
        List = import_module('System.Collections',
                             module_name='System.Collections.Generic',
                             submodule_or_classes='List')
        PerformanceCounter = Diagnostics.PerformanceCounter
        category = Diagnostics.PerformanceCounterCategory('GPU Engine')
        
        # pythonnet does not support import extension
        # https://stackoverflow.com/questions/35148789/how-to-use-linq-in-python-net

        self._action = import_module('System', submodule_or_classes='Action')[PerformanceCounter]
        self._status = List[PerformanceCounter]()
        self._init = False
        self._wrap_func = self._action(self._collect)
        self._result = 0.
        
        for cat_name in category.GetInstanceNames():
            if re.findall(r'engtype_3D', cat_name):
                self._status.Add(category.GetCounters(cat_name)[-1])
        self._setup()

    def _collect(self, x):
        try:
            x = x.NextValue()
        except System.InvalidOperationException:
            pass
        else:
            self._result += x

    def _setup(self):
        f = self._action(lambda x: x.NextValue())
        self._status.ForEach(f)
        time.sleep(1)
        self._init = True
    
    def __call__(self) -> float:
        self._result = 0.
        self._status.ForEach(self._wrap_func)
        return self._result


def NetGPU():
    if os.path.exists('./src/systemAPI/dll/GPUUsage.dll'):
        return DLL_NetGPU()
    else:
        return PY_NetGPU()


if __name__ == '__main__':
    print(gpu_power_limit())
    print(gpu_fan_speed())
