from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import create_engine, select, distinct, and_, text
from sqlalchemy.orm import sessionmaker
from .base import StorageBackend
from ..models import TrafficEvent, RequestAnomaly, EndpointTestSuite, TestCase
import logging

logger = logging.getLogger(__name__)


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

    async def get_unique_endpoints(self, hours: int):
        session = self.Session()
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            query = (
                session.query(distinct(TrafficEvent.path), TrafficEvent.method)
                .filter(TrafficEvent.timestamp >= cutoff_time)
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
    
    async def get_anomalies_by_endpoint(self, hours: int = 24):
        session = self.Session()
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            query = (
                session.query(RequestAnomaly)
                .filter(RequestAnomaly.detected_at >= cutoff_time)
            )
            return query.all()
        finally:
            session.close()

    
    async def store_test_case(self, url: str, http_method: str, test_case: Dict):
        session = self.Session()
        try:
            # Try to find existing test suite for this endpoint
            test_suite = session.query(EndpointTestSuite).filter(
                and_(
                    EndpointTestSuite.url == url,
                    EndpointTestSuite.http_method == http_method
                )
            ).first()

            if not test_suite:
                # If doesn't exist, create new test suite
                test_suite = EndpointTestSuite(
                    url=url,
                    http_method=http_method
                )
                session.add(test_suite)
                session.flush()  # This will populate the id

            # Create new test case
            new_test_case = TestCase(
                suite_id=test_suite.id,
                description=test_case.get('description'),
                category=test_case.get('category'),
                priority=test_case.get('priority'),
                request_method=test_case['request']['method'],
                request_url=test_case['request']['url'],
                request_headers=test_case['request'].get('headers'),
                request_path_params=test_case['request'].get('path_params'),
                request_query_params=test_case['request'].get('query_params'),
                request_body=test_case['request'].get('body')
            )
            session.add(new_test_case)
            session.commit()
            return new_test_case.id
        except Exception as e:
            logger.error(f"Error storing test case: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()

    def generate_openapi_data(self, base_url: str) -> Dict:
        """Generate OpenAPI-compatible data."""
        session = self.Session()
        try:
            openapi_data = {
                "openapi": "3.0.0",
                "info": {
                    "title": "API Documentation",
                    "version": "1.0.0",
                },
                "servers": [{"url": base_url}],
                "paths": {}
            }

            # Query all test suites
            test_suites = session.query(EndpointTestSuite).all()

            for suite in test_suites:
                if suite.url not in openapi_data["paths"]:
                    openapi_data["paths"][suite.url] = {}

                # Query test cases for each suite
                test_cases = session.query(TestCase).filter_by(suite_id=suite.id).all()
                for case in test_cases:
                    method = case.request_method.lower()
                    if method not in openapi_data["paths"][suite.url]:
                        openapi_data["paths"][suite.url][method] = {
                            "summary": case.description or "",
                            "parameters": [
                                {
                                    "name": "path",
                                    "in": "path",
                                    "required": False,
                                    "schema": {"type": "string"}
                                }
                            ],
                            "requestBody": {
                                "content": {
                                    "application/json": case.request_body
                                }
                            },
                            "responses": {
                                "200": {
                                    "description": "Successful response",
                                }
                            }
                        }

            return openapi_data

        except Exception as e:
            logger.error(f"Error generating OpenAPI data: {str(e)}")
            raise
        finally:
            session.close()

    def generate_openapi_data_for_endpoint(self, url: str, http_method: str, base_url: str) -> Dict:
        """Generate OpenAPI-compatible data for a single endpoint."""
        session = self.Session()
        try:
            test_suite = session.query(EndpointTestSuite).filter_by(url=url, http_method=http_method).first()
            if not test_suite:
                raise ValueError(f"No test suite found for URL {url} and method {http_method}")

            openapi_data = {
                "openapi": "3.0.0",
                "info": {
                    "title": "API Documentation",
                    "version": "1.0.0",
                },
                "servers": [{"url": base_url}],
                "paths": {
                    url: {
                        http_method.lower(): {
                            "summary": "",
                            "parameters": [],
                            "responses": {}
                        }
                    }
                }
            }

            test_cases = session.query(TestCase).filter_by(suite_id=test_suite.id).all()
            for case in test_cases:
                method_data = openapi_data["paths"][url][http_method.lower()]
                method_data["summary"] = case.description or ""
                method_data["parameters"] = [
                    {
                        "name": "path",
                        "in": "path",
                        "required": False,
                        "schema": {"type": "string"}
                    }
                ]
                method_data["requestBody"] = {
                    "content": {
                        "application/json": case.request_body
                    }
                }
                method_data["responses"]["200"] = {"description": "Successful response"}

            return openapi_data

        except Exception as e:
            logger.error(f"Error generating OpenAPI data for endpoint: {str(e)}")
            raise
        finally:
            session.close()

    def get_available_endpoints(self) -> List[Dict[str, str]]:
        """Get all available endpoints."""
        session = self.Session()
        try:
            endpoints = session.query(EndpointTestSuite).all()
            return [{"url": e.url, "http_method": e.http_method} for e in endpoints]
        finally:
            session.close()

