# app/routers/ingest.py

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, status, Depends
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
from typing import Dict, Any
from datetime import datetime
from ..genai.extractors import extract_invoice_fields_from_pdf_bytes
from ..models.vendor import Vendor
from ..models.invoice import Invoice


from ..db import get_db
from ..services.ingest_service import upsert_vendors_from_df, upsert_invoices_from_df, sync_graph_async

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/vendors-csv")
async def ingest_vendors_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Upload vendors CSV file. Returns summary and triggers graph sync in background.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    try:
        df = pd.read_csv(BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    summary = upsert_vendors_from_df(db, df)

    # trigger graph sync in background if background_tasks provided
    if background_tasks is not None:
        background_tasks.add_task(sync_graph_async)
    else:
        # fallback: run sync synchronously (not ideal for large data)
        sync_graph_async()

    return {"status": "ok", "summary": summary}


@router.post("/invoices-csv")
async def ingest_invoices_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Upload invoices CSV file (must upload vendors first).
    Triggers graph sync in background.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    try:
        df = pd.read_csv(BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    summary = upsert_invoices_from_df(db, df)

    if background_tasks is not None:
        background_tasks.add_task(sync_graph_async)
    else:
        sync_graph_async()

    return {"status": "ok", "summary": summary}


@router.post("/invoice-pdf")
async def ingest_invoice_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Upload a single invoice PDF (or image). The endpoint will:
    - extract structured fields via LLM
    - auto-create vendor if GSTIN not present in DB (optional)
    - create invoice entry
    - schedule graph sync in background
    """
    content = await file.read()
    # ensure it's not too big
    if len(content) > 10 * 1024 * 1024:  # 10 MB limit for POC
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Extract fields using extractor
    extracted = extract_invoice_fields_from_pdf_bytes(content, ocr_if_empty=True)
    print(extracted)

    # Validate minimal fields: invoice_number and amount preferred; gstin optional but preferable
    # gstin = extracted.get("gstin")
    # pan = extracted.get("pan")
    # vendor_name = extracted.get("vendor_name")
    # invoice_number = extracted.get("invoice_number")
    # invoice_date = extracted.get("invoice_date")
    # amount = extracted.get("amount")

    # if not invoice_number:
    #     # try to fallback to generated id or reject
    #     invoice_number = f"AUTO-{int(datetime.utcnow().timestamp())}"

    # # Find or create vendor
    # vendor = None
    # if gstin:
    #     vendor = db.query(Vendor).filter(Vendor.gstin == gstin).first()

    # if vendor is None:
    #     # fallback: try to find vendor by name substring
    #     if vendor_name:
    #         vendor = db.query(Vendor).filter(Vendor.name.ilike(f"%{vendor_name}%")).first()

    # if vendor is None:
    #     # create a minimal vendor record (auto-created vendor) with a flag in name to review
    #     created_vendor = Vendor(
    #         gstin=gstin if gstin else f"AUTO-{invoice_number}",
    #         name=vendor_name or f"Auto Vendor {invoice_number}",
    #         address=None,
    #         state=None,
    #         pan=pan
    #     )
    #     db.add(created_vendor)
    #     db.commit()
    #     db.refresh(created_vendor)
    #     vendor = created_vendor
    #     created_vendor_note = True
    # else:
    #     created_vendor_note = False

    # # parse invoice_date into date
    # inv_date = None
    # try:
    #     if invoice_date:
    #         # try to parse yyyy-mm-dd, fallback to other formats
    #         inv_date = datetime.fromisoformat(invoice_date).date()
    # except Exception:
    #     inv_date = None

    # # create invoice
    # invoice = Invoice(
    #     invoice_number=invoice_number,
    #     amount=amount if amount is not None else 0.0,
    #     date=inv_date if inv_date is not None else datetime.utcnow().date(),
    #     from_vendor_id=vendor.id,
    #     to_vendor_id=None  # TODO: decide if we can infer buyer; for now assume to_vendor unknown (use tenant_id later)
    # )

    # # For POC: we need to decide to whom invoice was issued (to_vendor_id). If this system is
    # # for a single buyer (you), you can set to your organization vendor id. For now we'll insert
    # # invoices where to_vendor_id = NULL which breaks FK constraint. So instead:
    # # Option: we set to_vendor_id = vendor.id (i.e., treat it as from->to within same vendor) — not ideal.
    # # Better: require your system to have a "tenant" vendor id (e.g. your company). We'll assume to_vendor_id = 1 for now.
    # # If you don't have such vendor, create one named "Self (System Buyer)" once.
    # #
    # # We'll attempt to use vendor with id=1 as buyer; if missing, we create a placeholder buyer.
    # buyer = db.query(Vendor).filter(Vendor.id == 1).first()
    # if buyer is None:
    #     buyer = Vendor(gstin="SYSTEM-BUYER-1", name="System Buyer (placeholder)")
    #     db.add(buyer)
    #     db.commit()
    #     db.refresh(buyer)

    # invoice.to_vendor_id = buyer.id

    # db.add(invoice)
    # db.commit()
    # db.refresh(invoice)

    # # schedule graph sync
    # if background_tasks is not None:
    #     background_tasks.add_task(sync_graph_async)
    # else:
    #     sync_graph_async()

    # return {
    #     "status": "ok",
    #     "extracted": extracted,
    #     "created_vendor": created_vendor_note,
    #     "vendor_id": vendor.id,
    #     "invoice_id": invoice.id,
    # }
    return
