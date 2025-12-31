from sqlalchemy import Column, ForeignKey, Integer, String, Text

from people_analytics.db.base import Base


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    label = Column(String(128), nullable=True)
    embedding_json = Column(Text, nullable=True)
