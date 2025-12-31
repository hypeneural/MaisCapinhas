from sqlalchemy import Column, Date, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from people_analytics.db.base import Base


class KpiHourly(Base):
    __tablename__ = "kpi_hourly"
    __table_args__ = (UniqueConstraint("store_id", "camera_id", "date", "hour", name="uq_kpi_hourly"),)

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True, index=True)
    date = Column(Date, nullable=False, index=True)
    hour = Column(Integer, nullable=False)
    in_count = Column(Integer, nullable=False, default=0)
    out_count = Column(Integer, nullable=False, default=0)
    staff_in = Column(Integer, nullable=False, default=0)
    staff_out = Column(Integer, nullable=False, default=0)
    avg_presence = Column(Integer, nullable=True)
    max_presence = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "date": self.date,
            "hour": self.hour,
            "in": self.in_count,
            "out": self.out_count,
            "staff_in": self.staff_in,
            "staff_out": self.staff_out,
            "avg_presence": self.avg_presence,
            "max_presence": self.max_presence,
        }
