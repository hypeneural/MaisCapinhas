from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func

from people_analytics.db.base import Base


class PresenceSample(Base):
    __tablename__ = "presence_samples"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey("video_segments.id"), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False)
    count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
