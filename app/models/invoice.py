# app/models/invoice.py

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from .base import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)

    from_vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    to_vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)

    created_at = Column(DateTime, server_default=func.now())

    from_vendor = relationship("Vendor", foreign_keys=[from_vendor_id], back_populates="outgoing_invoices")
    to_vendor = relationship("Vendor", foreign_keys=[to_vendor_id], back_populates="incoming_invoices")
