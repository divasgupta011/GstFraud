# app/schemas/vendor.py
from pydantic import BaseModel, Field
from typing import Optional


class VendorBase(BaseModel):
    gstin: str = Field(..., max_length=20)
    name: str = Field(..., max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    state: Optional[str] = Field(None, max_length=100)
    pan: Optional[str] = Field(None, max_length=20)


class VendorCreate(VendorBase):
    pass


class VendorRead(VendorBase):
    id: int

    class Config:
        from_attributes = True  # important for SQLAlchemy ORM objects
