# app/models/vendor.py

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from .base import Base

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    gstin = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=True)
    state = Column(String(100), nullable=True)
    pan = Column(String(20), nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    # relationships
    outgoing_invoices = relationship(
        "Invoice",
        foreign_keys="Invoice.from_vendor_id",
        back_populates="from_vendor"
    )
    
    incoming_invoices = relationship(
        "Invoice",
        foreign_keys="Invoice.to_vendor_id",
        back_populates="to_vendor"
    )

    directors = relationship("VendorDirector", back_populates="vendor")
