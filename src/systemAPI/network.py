import time
from typing import Tuple, Union

from ..utils import NetworkInterface, StatusContainer

__all__ = ["Network"]

class Network():
    def __init__(self):
        self._time = time.time()
        self._network = self._get_networks()
        self._network_wait_count = 0

        self._sent = None
        self._received = None

    def _get_networks(self) -> StatusContainer:
        status = StatusContainer()
        adapters = NetworkInterface.GetAllNetworkInterfaces()
        for adapter in adapters:
            stats = adapter.GetIPv4Statistics()
            if adapter.Speed != -1 and stats.BytesReceived != 0:
                status.register('adapter', adapter)
                break
        return status
    
    def get_sent_received(self) -> Union[Tuple[float, float], Tuple[str, str]]:
        if self._network.isempty:
            if self._network_wait_count == 4:
                self._network_wait_count = 0
                self._network = self._get_networks()
                return ['Connecting...']*2
            self._network_wait_count += 1
            return ['nan']*2
        stats = self._network.adapter.GetIPv4Statistics()
        current_sent = stats.BytesSent
        current_received = stats.BytesReceived

        now = time.time()
        time_diff = now - self._time
        self._time = now

        if self._sent is None or isinstance(self._sent, str):
            self._sent = current_sent
            self._received = current_received
            return ['Connecting...']*2
        elif current_sent < 0 or current_sent < self._sent:
            self._sent = None
            self._received = None
            self._network_wait_count = 0
            return ['nan']*2
        elif current_sent == self._sent and current_received == self._received:
            self._network_wait_count = 0
            self._network = self._get_networks()
            return ['nan']*2

        self._network_wait_count = 0
        sent = (current_sent - self._sent) / 1024 * time_diff
        received = (current_received - self._received) / 1024 * time_diff

        self._sent = current_sent
        self._received = current_received
        return [sent, received]
