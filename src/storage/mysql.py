from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import create_engine, select, distinct, and_, text
from sqlalchemy.orm import sessionmaker
from .base import StorageBackend
from ..models import TrafficEvent, RequestAnomaly

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

    async def get_events_by_endpoint(self, path: str, method: str, start_time: datetime, end_time: datetime):
        session = self.Session()
        try:
            query = (
                session.query(TrafficEvent)
                .filter(
                    and_(
                        TrafficEvent.path == path,
                        TrafficEvent.method == method,
                        TrafficEvent.timestamp.between(start_time, end_time)
                    )
                )
            )
            return query.all()
        finally:
            session.close()

    async def store_anomaly(self, event_id: int, similarity_score: float, 
                          anomaly_type: str, description: str, reference_events: List[Dict]):
        session = self.Session()
        try:
            anomaly = RequestAnomaly(
                event_id=event_id,
                similarity_score=similarity_score,
                anomaly_type=anomaly_type,
                description=description,
                reference_events=reference_events
            )
            session.add(anomaly)
            session.commit()
        finally:
            session.close()

    # async def get_unique_endpoints(self, hours: int):
    #     session = self.Session()
    #     try:
    #         cutoff_time = datetime.now() - timedelta(hours=hours)
    #         query = (
    #             session.query(distinct(TrafficEvent.path), TrafficEvent.method)
    #             .filter(TrafficEvent.timestamp >= cutoff_time)
    #         )
    #         return query.all()
    #     finally:
    #         session.close()

    async def get_unique_endpoints(self, hours: int):
        session = self.Session()
        try:
            query = (
                session.query(distinct(TrafficEvent.path), TrafficEvent.method)
                .filter(TrafficEvent.path.like('/api/users%'))  # Filter paths that start with /api/users
            )
            return query.all()
        finally:
            session.close()



    async def get_anomalies(self, hours: int = 24, min_score: float = 0.0):
        session = self.Session()
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            query = (
                session.query(RequestAnomaly, TrafficEvent)
                .join(TrafficEvent, RequestAnomaly.event_id == TrafficEvent.id)
                .filter(
                    and_(
                        RequestAnomaly.detected_at >= cutoff_time,
                        RequestAnomaly.similarity_score >= min_score
                    )
                )
                .order_by(RequestAnomaly.detected_at.desc())
            )
            results = query.all()
            
            # Convert the results to a JSON-serializable format
            formatted_results = []
            for anomaly, event in results:
                formatted_results.append({
                    'anomaly': {
                        'id': anomaly.id,
                        'event_id': anomaly.event_id,
                        'similarity_score': float(anomaly.similarity_score),
                        'anomaly_type': anomaly.anomaly_type,
                        'description': anomaly.description,
                        'detected_at': anomaly.detected_at.isoformat(),
                        'reference_events': anomaly.reference_events
                    },
                    'event': {
                        'id': event.id,
                        'timestamp': event.timestamp.isoformat(),
                        'path': event.path,
                        'method': event.method,
                        'headers': event.headers,
                        'path_params': event.path_params,
                        'query_params': event.query_params,
                        'request_body': event.request_body,
                        'status': event.status,
                        'duration_ms': float(event.duration_ms) if event.duration_ms else None,
                        'response_headers': event.response_headers
                    }
                })
            
            return formatted_results
        finally:
            session.close()

    async def get_deduplication_data(self, start_time: datetime, end_time: datetime):
        """
        Fetch data required for deduplication within a specific time range.
        :param start_time: Start of the time range.
        :param end_time: End of the time range.
        :return: A dictionary of records with their IDs as keys.
        """
        session = self.Session()
        try:
            query = (
                session.query(
                    TrafficEvent.id,
                    TrafficEvent.path,
                    TrafficEvent.method,
                    TrafficEvent.request_body
                )
                .filter(
                    TrafficEvent.timestamp.between(start_time, end_time)
                )
            )
            results = query.all()

            # Prepare data for deduplication
            data = {
                record.id: {
                    "path": record.path,
                    "method": record.method,
                    "request_body": record.request_body or ""
                }
                for record in results
            }
            return data
        finally:
            session.close()