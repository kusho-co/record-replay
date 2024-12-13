from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base import StorageBackend
from ..models import TrafficEvent

class MySQLStorage(StorageBackend):
    def __init__(self, connection_uri: str):
        self.engine = create_engine(connection_uri)
        self.Session = sessionmaker(bind=self.engine)

    def store_events(self, events: List[Dict[str, Any]]):
        session = self.Session()
        try:
            for event_data in events:
                event = TrafficEvent(
                    timestamp=datetime.fromtimestamp(event_data['timestamp']),
                    path=event_data['path'],
                    method=event_data['method'],
                    headers=event_data.get('headers'),
                    path_params=event_data.get('path_params'),
                    query_params=event_data.get('query_params'),
                    request_body=event_data.get('request_body'),
                    status=event_data.get('status'),
                    duration_ms=event_data.get('duration_ms'),
                    response_headers=event_data.get('response_headers')
                )
                session.add(event)
            session.commit()
        finally:
            session.close()

    def get_analytics(self, start_time, end_time, path_pattern=None):
        session = self.Session()
        try:
            query = session.query(TrafficEvent)
            if path_pattern:
                query = query.filter(TrafficEvent.path.like(f'%{path_pattern}%'))
            query = query.filter(
                TrafficEvent.timestamp.between(start_time, end_time)
            )
            return query.all()
        finally:
            session.close()