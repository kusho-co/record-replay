from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, BigInteger, ForeignKey, UniqueConstraint, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship


Base = declarative_base()

class TrafficEvent(Base):
    __tablename__ = 'traffic_events'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    path = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    headers = Column(JSON)
    path_params = Column(JSON)
    query_params = Column(JSON)
    request_body = Column(JSON)
    status = Column(Integer)
    duration_ms = Column(Float)
    response_headers = Column(JSON)

    # Relationship to anomalies
    anomalies = relationship("RequestAnomaly", back_populates="traffic_event")

class RequestAnomaly(Base):
    __tablename__ = 'request_anomalies'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(BigInteger, ForeignKey('traffic_events.id'))
    similarity_score = Column(Float)
    anomaly_type = Column(String(50))
    description = Column(Text)
    detected_at = Column(DateTime, server_default=func.current_timestamp())
    reference_events = Column(JSON)

    # Relationship to traffic event
    traffic_event = relationship("TrafficEvent", back_populates="anomalies")


class RequestPattern(Base):
    __tablename__ = 'request_patterns'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    path = Column(String(255))
    method = Column(String(10))
    pattern_vector = Column(JSON)
    updated_at = Column(
        DateTime, 
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp()
    )

    # Add unique constraint for path and method combination
    __table_args__ = (
        UniqueConstraint('path', 'method', name='unique_path_method'),
    )

class EndpointTestCase(Base):
    __tablename__ = 'endpoint_test_cases'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(BigInteger, ForeignKey('jobs.id'))
    endpoint_path = Column(String(255), nullable=False)
    http_method = Column(String(10), nullable=False)
    test_cases = Column(JSON)
    created_at = Column(DateTime, server_default=func.current_timestamp())

class EndpointTestSuite(Base):
    __tablename__ = 'endpoint_test_suites'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    url = Column(String(255), nullable=False)
    http_method = Column(String(10), nullable=False)
    last_updated = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    created_at = Column(DateTime, server_default=func.current_timestamp())

    __table_args__ = (
        UniqueConstraint('url', 'http_method', name='unique_endpoint'),
    )

class TestCase(Base):
    __tablename__ = 'test_cases'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    suite_id = Column(BigInteger, ForeignKey('endpoint_test_suites.id'), nullable=False)
    description = Column(String(255))
    category = Column(String(50))
    priority = Column(String(20))
    request_method = Column(String(10))
    request_url = Column(String(255))
    request_headers = Column(JSON)
    request_path_params = Column(JSON)
    request_query_params = Column(JSON)
    request_body = Column(JSON)
    

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(String(36), primary_key=True)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

