# app/routers/invoices.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..db import get_db
from ..models.invoice import Invoice
from ..models.vendor import Vendor
from ..schemas.invoice import InvoiceCreate, InvoiceRead

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):

    # Validate vendor existence
    from_vendor = db.query(Vendor).filter(Vendor.id == payload.from_vendor_id).first()
    if not from_vendor:
        raise HTTPException(status_code=400, detail="from_vendor_id not found")

    to_vendor = db.query(Vendor).filter(Vendor.id == payload.to_vendor_id).first()
    if not to_vendor:
        raise HTTPException(status_code=400, detail="to_vendor_id not found")

    invoice = Invoice(
        invoice_number=payload.invoice_number,
        amount=payload.amount,
        date=payload.date,
        from_vendor_id=payload.from_vendor_id,
        to_vendor_id=payload.to_vendor_id
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return invoice


@router.get("", response_model=List[InvoiceRead])
def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).order_by(Invoice.id).all()
    return invoices


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )

    return invoice
