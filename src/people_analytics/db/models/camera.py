from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from people_analytics.db.base import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    camera_code = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=True)

    store = relationship("Store")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "store_id": self.store_id,
            "camera_code": self.camera_code,
            "name": self.name,
        }
