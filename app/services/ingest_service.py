# app/services/ingest_service.py
from typing import Tuple, List, Dict, Any
from sqlalchemy.orm import Session
import pandas as pd
from datetime import datetime
from ..models.vendor import Vendor
from ..models.invoice import Invoice
from ..graph.sync import sync_all_to_neo4j_using_new_session

def upsert_vendors_from_df(db: Session, df: pd.DataFrame, create_missing: bool = False) -> Dict[str, Any]:
    """
    df must have columns: gstin, name, address, state, pan
    create_missing: if True, create missing fields even if some empty
    Returns summary dict with counts and row-level errors.
    """
    created = 0
    updated = 0
    errors: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        gstin = str(row.get("gstin", "")).strip()
        name = str(row.get("name", "")).strip()
        address = row.get("address") if not pd.isna(row.get("address")) else None
        state = row.get("state") if not pd.isna(row.get("state")) else None
        pan = row.get("pan") if not pd.isna(row.get("pan")) else None

        if not gstin or not name:
            errors.append({"row": int(idx)+1, "error": "missing gstin or name"})
            continue

        existing = db.query(Vendor).filter(Vendor.gstin == gstin).first()
        if existing:
            # update basic fields if changed
            changed = False
            if name and existing.name != name:
                existing.name = name
                changed = True
            if address and existing.address != address:
                existing.address = address
                changed = True
            if state and existing.state != state:
                existing.state = state
                changed = True
            if pan and existing.pan != pan:
                existing.pan = pan
                changed = True
            if changed:
                db.add(existing)
                updated += 1
        else:
            vendor = Vendor(gstin=gstin, name=name, address=address, state=state, pan=pan)
            db.add(vendor)
            created += 1

    db.commit()
    return {"created": created, "updated": updated, "errors": errors}


def upsert_invoices_from_df(db: Session, df: pd.DataFrame) -> Dict[str, Any]:
    """
    df must have columns: invoice_number, amount, date, from_gstin, to_gstin
    We map GSTIN -> vendor.id; if a GSTIN missing in vendor table, error out (or optionally create vendor)
    """
    created = 0
    errors: List[Dict[str, Any]] = []

    # build GSTIN -> vendor id cache
    vendors = db.query(Vendor).all()
    gstin_map = {v.gstin: v.id for v in vendors}

    for idx, row in df.iterrows():
        try:
            inv_no = str(row.get("invoice_number", "")).strip()
            amount = float(row.get("amount", 0))
            date_raw = row.get("date")
            # parse date robustly
            if pd.isna(date_raw):
                raise ValueError("missing date")
            if isinstance(date_raw, str):
                date_parsed = datetime.fromisoformat(date_raw).date()
            elif isinstance(date_raw, (pd.Timestamp, datetime)):
                date_parsed = pd.to_datetime(date_raw).date()
            else:
                date_parsed = pd.to_datetime(date_raw).date()

            from_gstin = str(row.get("from_gstin", "")).strip()
            to_gstin = str(row.get("to_gstin", "")).strip()

            if not inv_no or not from_gstin or not to_gstin:
                raise ValueError("missing invoice_number/from_gstin/to_gstin")

            if from_gstin not in gstin_map or to_gstin not in gstin_map:
                raise ValueError("unknown GSTIN (ensure vendors uploaded first)")

            from_id = gstin_map[from_gstin]
            to_id = gstin_map[to_gstin]

            # duplicate check: optional — avoid duplicate invoice by invoice_number+from+to+date
            existing = (
                db.query(Invoice)
                .filter(
                    Invoice.invoice_number == inv_no,
                    Invoice.from_vendor_id == from_id,
                    Invoice.to_vendor_id == to_id,
                )
                .first()
            )
            if existing:
                # update amount/date if needed
                changed = False
                if existing.amount != amount:
                    existing.amount = amount
                    changed = True
                if existing.date != date_parsed:
                    existing.date = date_parsed
                    changed = True
                if changed:
                    db.add(existing)
                # do not increment created
            else:
                invoice = Invoice(
                    invoice_number=inv_no,
                    amount=amount,
                    date=date_parsed,
                    from_vendor_id=from_id,
                    to_vendor_id=to_id,
                )
                db.add(invoice)
                created += 1

        except Exception as e:
            errors.append({"row": int(idx)+1, "error": str(e)})
            continue

    db.commit()
    return {"created": created, "errors": errors}


# add this import at top if not present
from ..graph.sync import sync_all_to_neo4j_using_new_session

def sync_graph_async() -> Tuple[int, int]:
    """
    Background-friendly sync that creates its own DB session.
    Designed to be called with no arguments (safe for FastAPI BackgroundTasks).
    """
    return sync_all_to_neo4j_using_new_session()
