from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from people_analytics.db.base import Base
from people_analytics.storage.paths import VideoPathInfo


class VideoSegment(Base):
    __tablename__ = "video_segments"
    __table_args__ = (UniqueConstraint("path", name="uq_video_segments_path"),)

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    path = Column(String(512), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    fingerprint = Column(String(128), nullable=False, index=True)
    file_size = Column(Integer, nullable=True)
    status = Column(String(32), default="new", nullable=False)

    store = relationship("Store")
    camera = relationship("Camera")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "path": self.path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
        }

    def to_path_info(self, store_code: str, camera_code: str, tz_name: str | None = None) -> VideoPathInfo:
        from people_analytics.core.timeutils import to_local

        start_dt = self.start_time
        end_dt = self.end_time
        if tz_name:
            start_dt = to_local(start_dt, tz_name)
            end_dt = to_local(end_dt, tz_name)
        return VideoPathInfo(
            store_code=store_code,
            camera_code=camera_code,
            date=start_dt.date(),
            start_time=start_dt.timetz().replace(tzinfo=None),
            end_time=end_dt.timetz().replace(tzinfo=None),
            relative_path=self.path,
        )
