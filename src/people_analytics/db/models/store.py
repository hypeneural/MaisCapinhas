from sqlalchemy import Column, Integer, String

from people_analytics.db.base import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=True)
    city = Column(String(128), nullable=True)

    def to_dict(self) -> dict:
        return {"id": self.id, "code": self.code, "name": self.name, "city": self.city}
