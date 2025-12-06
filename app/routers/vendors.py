# app/routers/vendors.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.vendor import Vendor
from ..schemas.vendor import VendorCreate, VendorRead

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.post("", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db)):
    # Check if GSTIN already exists
    existing = db.query(Vendor).filter(Vendor.gstin == payload.gstin).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor with this GSTIN already exists",
        )

    vendor = Vendor(
        gstin=payload.gstin,
        name=payload.name,
        address=payload.address,
        state=payload.state,
        pan=payload.pan,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("", response_model=List[VendorRead])
def list_vendors(db: Session = Depends(get_db)):
    vendors = db.query(Vendor).order_by(Vendor.id).all()
    return vendors


@router.get("/{vendor_id}", response_model=VendorRead)
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )
    return vendor
