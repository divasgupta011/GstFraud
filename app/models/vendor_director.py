# app/models/vendor_director.py

from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from .base import Base

class VendorDirector(Base):
    __tablename__ = "vendor_directors"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), index=True)
    director_id = Column(Integer, ForeignKey("directors.id"), index=True)

    created_at = Column(DateTime, server_default=func.now())

    vendor = relationship("Vendor", back_populates="directors")
    director = relationship("Director", back_populates="vendors")
