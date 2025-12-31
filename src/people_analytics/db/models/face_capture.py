from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.dialects.postgresql import JSONB

from people_analytics.db.base import Base


class FaceCapture(Base):
    __tablename__ = "face_captures"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey("video_segments.id"), nullable=True, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    track_id = Column(String(64), nullable=True, index=True)
    source = Column(String(32), nullable=True)
    face_score = Column(Float, nullable=True)
    face_bbox = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    path = Column(String(512), nullable=False)
