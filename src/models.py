from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TrafficEvent(Base):
    __tablename__ = 'traffic_events'

    id = Column(Integer, primary_key=True)
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