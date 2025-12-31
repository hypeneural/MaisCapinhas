from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean, Float
from sqlalchemy.sql import func

from people_analytics.db.base import Base


class PeopleFlowEvent(Base):
    __tablename__ = "people_flow_events"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey("video_segments.id"), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False)
    direction = Column(String(8), nullable=False)
    is_staff = Column(Boolean, nullable=False, default=False)
    track_id = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
