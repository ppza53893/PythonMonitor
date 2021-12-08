import subprocess
from typing import Union

__all__ = ['nvidia_smi_update', 'is_nvidia_smi_available', 'gpu_power_limit', 'gpu_fan_speed']

NVSMI_QUERIES = [
    'nvidia-smi', '-i', '0',
    '--query-gpu=enforced.power.limit,fan.speed',
    '--format=csv,noheader,nounits']
GPU_MAX_POWER = None
GPU_FAN_SPEED = None


def nvidia_smi_update() -> None:
    global GPU_MAX_POWER, GPU_FAN_SPEED
    if GPU_MAX_POWER != 'NOT_AVAILABLE' and GPU_FAN_SPEED != 'NOT_AVAILABLE':
        try:
            enf_power, fan_speed = map(float,
                        subprocess.run(NVSMI_QUERIES, stdout=subprocess.PIPE)\
                        .stdout.decode('utf-8').replace('\r', '').replace('\n', '').replace(' ', '').split(','))
            GPU_MAX_POWER = enf_power
            GPU_FAN_SPEED = fan_speed
        except:
            GPU_MAX_POWER = 'NOT_AVAILABLE'
            GPU_FAN_SPEED = 'NOT_AVAILABLE'


def is_nvidia_smi_available() -> bool:
    if GPU_MAX_POWER is None or GPU_FAN_SPEED is None:
        nvidia_smi_update()
    return GPU_MAX_POWER != 'NOT_AVAILABLE' and GPU_FAN_SPEED != 'NOT_AVAILABLE'


def gpu_power_limit() -> Union[float, str]:
    if GPU_MAX_POWER is None:
        nvidia_smi_update()
    return GPU_MAX_POWER


def gpu_fan_speed() -> Union[float, str]:
    if GPU_FAN_SPEED is None:
        nvidia_smi_update()
    return GPU_FAN_SPEED


if __name__ == '__main__':
    print(gpu_power_limit())
    print(gpu_fan_speed())