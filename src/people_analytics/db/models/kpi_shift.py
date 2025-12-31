from sqlalchemy import Column, Date, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from people_analytics.db.base import Base


class KpiShift(Base):
    __tablename__ = "kpi_shift"
    __table_args__ = (UniqueConstraint("store_id", "camera_id", "date", "shift_id", name="uq_kpi_shift"),)

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True, index=True)
    date = Column(Date, nullable=False, index=True)
    shift_id = Column(String(32), nullable=False)
    in_count = Column(Integer, nullable=False, default=0)
    out_count = Column(Integer, nullable=False, default=0)
    staff_in = Column(Integer, nullable=False, default=0)
    staff_out = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "date": self.date,
            "shift_id": self.shift_id,
            "in": self.in_count,
            "out": self.out_count,
            "staff_in": self.staff_in,
            "staff_out": self.staff_out,
        }
