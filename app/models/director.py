# app/models/director.py

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from .base import Base

class Director(Base):
    __tablename__ = "directors"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    pan = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    vendors = relationship("VendorDirector", back_populates="director")
