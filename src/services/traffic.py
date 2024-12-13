from typing import List, Dict, Any
from ..storage.base import StorageBackend

class TrafficService:
    def __init__(self, storage: StorageBackend):
        self.storage = storage

    def store_events(self, events: List[Dict[str, Any]]):
        return self.storage.store_events(events)

    def get_analytics(self, start_time, end_time, path_pattern=None):
        return self.storage.get_analytics(start_time, end_time, path_pattern)