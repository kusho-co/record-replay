from abc import ABC, abstractmethod
from typing import List, Dict, Any

class StorageBackend(ABC):
    @abstractmethod
    def store_events(self, events: List[Dict[str, Any]]):
        pass

    @abstractmethod
    def get_analytics(self, start_time, end_time, path_pattern=None):
        pass