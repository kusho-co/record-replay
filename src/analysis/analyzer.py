from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from .vectorizer import RequestVectorizer
from ..storage.mysql import MySQLStorage
from dataclasses import dataclass
from .deduplicator_v1 import APIDeduplicator

# Configure logger
logger = logging.getLogger(__name__)

@dataclass
class AnomalyResult:
    event_id: int
    similarity_score: float
    anomaly_type: str
    description: str
    reference_events: List[Dict[str, Any]]

class RequestAnalyzer:
    def __init__(self, storage: MySQLStorage):
        self.storage = storage
        self.vectorizer = RequestVectorizer()
        self.deduplicator = APIDeduplicator()
        self.similarity_threshold = 0.7
        logger.info("RequestAnalyzer initialized with similarity threshold: %f", self.similarity_threshold)

    async def analyze_endpoint(self, path: str, method: str, hours: int = 24):
        """Analyze requests for a specific endpoint."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        logger.info("Analyzing endpoint %s %s from %s to %s", method, path, start_time, end_time)
        
        events = await self.storage.get_events_by_endpoint(path, method, start_time, end_time)
        
        if not events or len(events) < 2:
            logger.warning("Insufficient events for analysis: %d events found", len(events) if events else 0)
            return

        logger.info("Deduplicating %d events", len(events))
        unique_events = self.deduplicator.deduplicate(events)
        logger.info("%d unique events remaining after deduplication", len(unique_events))

        logger.debug("Processing %d events for analysis", len(events))

        requests_data = []
        for event in events:
            request_data = {
                'path': event.path,
                'method': event.method,
                'body': event.request_body if event.request_body else {},
                'query_params': event.query_params if event.query_params else {},
                'headers': event.headers if event.headers else {}
            }
            requests_data.append(request_data)

        try:
            logger.debug("Vectorizing %d requests", len(requests_data))
            vectors = self.vectorizer.fit_transform(requests_data)
            logger.debug("Vector shape: %s", vectors.shape)
            
            anomalies = self._find_anomalies(vectors, events)
            logger.info("Found %d anomalies", len(anomalies))
            
            for anomaly in anomalies:
                logger.debug("Storing anomaly: event_id=%d, score=%f, type=%s", 
                           anomaly.event_id, anomaly.similarity_score, anomaly.anomaly_type)
                await self.storage.store_anomaly(
                    event_id=anomaly.event_id,
                    similarity_score=anomaly.similarity_score,
                    anomaly_type=anomaly.anomaly_type,
                    description=anomaly.description,
                    reference_events=anomaly.reference_events
                )
        except Exception as e:
            logger.error("Error analyzing endpoint %s %s: %s", path, method, str(e), exc_info=True)

    def _parse_status_code(self, status_value) -> int:
        """Parse status code from different formats (e.g., '200 OK' or '200')."""
        try:
            if isinstance(status_value, int):
                return status_value
                
            status_str = str(status_value)
            # Extract first number found in the string
            status_code = int(status_str.split()[0])
            return status_code
        except (ValueError, IndexError) as e:
            logger.warning("Failed to parse status code from '%s': %s", status_value, str(e))
            return 0

    def _find_anomalies(self, vectors, events) -> List[AnomalyResult]:
        """Find anomalies in the vectorized requests."""
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        logger.debug("Calculating similarity matrix for %d vectors", len(vectors))
        similarities = cosine_similarity(vectors)
        anomalies = []

        logger.info("Starting anomaly detection for %d events", len(events))
        
        for i, event in enumerate(events):
            # Convert event.id to int if it's not already
            event_id = int(event.id) if hasattr(event, 'id') else i
            logger.debug("Analyzing event %d: %s %s", event_id, event.method, event.path)
            
            # Initialize anomaly flags
            is_anomaly = False
            anomaly_reasons = []
            
            # Check for suspicious patterns in query parameters
            if event.query_params:
                logger.debug("Checking query parameters for event %d: %s", event_id, event.query_params)
                suspicious_patterns = ['OR 1=1', 'DROP TABLE', ';']
                for pattern in suspicious_patterns:
                    if any(pattern.lower() in str(v).lower() for v in event.query_params.values()):
                        is_anomaly = True
                        reason = f"Suspicious SQL pattern found: {pattern}"
                        anomaly_reasons.append(reason)
                        logger.warning("Event %d: %s", event_id, reason)

            # Check for suspicious headers
            if event.headers:
                logger.debug("Checking headers for event %d: %s", event_id, event.headers)
                suspicious_headers = ['sqlmap', 'scanner', 'attack']
                for header in suspicious_headers:
                    if any(header.lower() in str(v).lower() for v in event.headers.values()):
                        is_anomaly = True
                        reason = f"Suspicious header found: {header}"
                        anomaly_reasons.append(reason)
                        logger.warning("Event %d: %s", event_id, reason)

            # Check for unusual HTTP methods
            unusual_methods = ['TRACE', 'CONNECT', 'OPTIONS']
            if event.method in unusual_methods:
                is_anomaly = True
                reason = f"Unusual HTTP method: {event.method}"
                anomaly_reasons.append(reason)
                logger.warning("Event %d: %s", event_id, reason)

            # Check for abnormal response times
            if hasattr(event, 'duration_ms'):
                try:
                    duration = float(event.duration_ms)
                    logger.debug("Checking response time for event %d: %.2fms", event_id, duration)
                    if duration > 1000:  # Over 1 second
                        is_anomaly = True
                        reason = f"Abnormal response time: {duration}ms"
                        anomaly_reasons.append(reason)
                        logger.warning("Event %d: %s", event_id, reason)
                except (ValueError, TypeError):
                    logger.warning("Invalid duration value for event %d: %s", event_id, event.duration_ms)

            # Check for error status codes
            if hasattr(event, 'status'):
                status_code = self._parse_status_code(event.status)
                logger.debug("Checking status code for event %d: %s (parsed as %d)", 
                            event_id, event.status, status_code)
                
                if status_code >= 400:
                    is_anomaly = True
                    reason = f"Error status code: {event.status}"
                    anomaly_reasons.append(reason)
                    logger.warning("Event %d: %s", event_id, reason)

            # Check request similarity
            request_similarities = similarities[i].copy()
            request_similarities[i] = 0
            max_similarity = float(np.max(request_similarities))
            logger.debug("Event %d max similarity score: %f", event_id, max_similarity)
            
            if max_similarity < self.similarity_threshold:
                is_anomaly = True
                reason = f"Unusual request pattern (similarity: {max_similarity:.2f})"
                anomaly_reasons.append(reason)
                logger.warning("Event %d: %s", event_id, reason)

            if is_anomaly:
                logger.info("Anomaly detected for event %d with %d reasons", 
                        event_id, len(anomaly_reasons))
                
                similar_indices = np.argsort(request_similarities)[-3:]
                logger.debug("Most similar events for %d: %s", 
                            event_id, similar_indices.tolist())
                
                reference_events = []
                for idx in similar_indices:
                    ref_event = events[idx]
                    ref_event_id = int(ref_event.id) if hasattr(ref_event, 'id') else idx
                    reference_events.append({
                        'id': ref_event_id,
                        'timestamp': ref_event.timestamp.isoformat(),
                        'path': ref_event.path,
                        'method': ref_event.method,
                        'request_body': ref_event.request_body,
                        'status': str(ref_event.status),  # Keep original status string
                        'similarity': float(request_similarities[idx])
                    })

                anomaly = AnomalyResult(
                    event_id=event_id,
                    similarity_score=max_similarity,
                    anomaly_type='request_pattern_anomaly',
                    description='; '.join(anomaly_reasons),
                    reference_events=reference_events
                )
                
                logger.info("Created anomaly result for event %d: %s", 
                        event_id, anomaly.description)
                anomalies.append(anomaly)
            else:
                logger.debug("No anomalies detected for event %d", event_id)

        logger.info("Anomaly detection complete. Found %d anomalies in %d events", 
                    len(anomalies), len(events))
        return anomalies

    async def analyze_recent_traffic(self, hours: int = 24):
        """Analyze all traffic from recent hours."""
        logger.info("Starting analysis of recent traffic for past %d hours", hours)
        endpoints = await self.storage.get_unique_endpoints(hours)
        logger.info("Found %d unique endpoints to analyze", len(endpoints))
        
        for path, method in endpoints:
            await self.analyze_endpoint(path, method, hours)