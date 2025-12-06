# app/schemas/invoice.py
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class InvoiceBase(BaseModel):
    invoice_number: str = Field(..., max_length=100)
    amount: float
    date: date
    from_vendor_id: int
    to_vendor_id: int


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceRead(InvoiceBase):
    id: int

    class Config:
        from_attributes = True
