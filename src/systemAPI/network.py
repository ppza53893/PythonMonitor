import time
from types import ModuleType
from typing import Tuple, Union, Optional

from ..utils import NetworkInterface, StatusContainer

__all__ = ["Network"]
NOT_CONNECTED = ['Not connected', 'Not connected']

class Network():
    MAX_WAIT_COUNT = 4

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
            sent, received = self._get_current_status(adapter)
            if adapter.Speed != -1 and sent != 0 and received != 0:
                status.register('adapter', adapter)
                break
        return status

    def _get_current_status(self, adapter: Optional[ModuleType] = None) -> Tuple[float, float]:
        if adapter is None:
            stats = self._network.adapter.GetIPv4Statistics()
        else:
            stats = adapter.GetIPv4Statistics()
        current_sent = stats.BytesSent
        current_received = stats.BytesReceived

        return current_sent, current_received

    def _reset_wait_count(self):
        self._network_wait_count = 0
    
    def get_sent_received(self) -> Union[Tuple[float, float], Tuple[str, str]]:
        if self._network.isempty:
            if self._network_wait_count == self.MAX_WAIT_COUNT:
                self._reset_wait_count()
                self._network = self._get_networks()
            else:
                self._network_wait_count += 1
            return NOT_CONNECTED
        else:
            current_sent, current_received = self._get_current_status()
    
            if self._sent is None or type(self._sent) is str:
                self._sent = current_sent
                self._received = current_received
                return NOT_CONNECTED
            elif current_sent < 0 or current_sent < self._sent:
                self._sent = None
                self._received = None
                self._reset_wait_count()
                return NOT_CONNECTED
            elif current_sent == self._sent and current_received == self._received:
                if self._network_wait_count == self.MAX_WAIT_COUNT:
                    self._reset_wait_count()
                    self._network = self._get_networks()
                    return NOT_CONNECTED
                else:
                    self._network_wait_count += 1
            else:
                self._reset_wait_count()

            now = time.time()
            time_diff = now - self._time
            self._time = now

            # convert to kbps
            # bps = byte diff / time diff
            # kbps = bps / 1024
            sent = (current_sent - self._sent) / (1024 * time_diff)
            received = (current_received - self._received) / (1024 * time_diff)

            self._sent = current_sent
            self._received = current_received
            return [sent, received]
