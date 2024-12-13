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