from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime

class StorageBackend(ABC):
    @abstractmethod
    def store_events(self, events: List[Dict[str, Any]]):
        pass

    @abstractmethod
    def get_analytics(self, start_time, end_time, path_pattern=None):
        pass

    # @abstractmethod
    # async def get_normal_requests(self, start_time: datetime, end_time: datetime):
    #     pass

    # @abstractmethod
    # async def store_anomalies(self, event_id: int, anomalies: List[Dict[str, Any]]):
    #     pass