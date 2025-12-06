# app/routers/anomalies.py

from typing import List, Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db import get_db
from ..models.vendor import Vendor

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("/shared-addresses")
def get_shared_addresses(min_vendors: int = 2, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Find addresses that are used by multiple vendors (default: 2+).
    This is an indicator of potential shell networks or linked entities.
    """

    # 1) group by address and count vendors
    grouped = (
        db.query(
            Vendor.address.label("address"),
            func.count(Vendor.id).label("vendor_count")
        )
        .filter(Vendor.address.isnot(None))
        .group_by(Vendor.address)
        .having(func.count(Vendor.id) >= min_vendors)
        .all()
    )

    # 2) for each such address, get vendor details
    result: List[Dict[str, Any]] = []
    for row in grouped:
        address = row.address
        vendor_count = row.vendor_count

        vendors_at_address = (
            db.query(Vendor)
            .filter(Vendor.address == address)
            .order_by(Vendor.id)
            .all()
        )

        result.append(
            {
                "address": address,
                "vendor_count": vendor_count,
                "vendors": [
                    {
                        "id": v.id,
                        "name": v.name,
                        "gstin": v.gstin,
                        "state": v.state,
                        "pan": v.pan,
                    }
                    for v in vendors_at_address
                ],
            }
        )

    return {
        "count": len(result),
        "min_vendors": min_vendors,
        "clusters": result,
    }

@router.get("/shared-pan")
def get_shared_pan(min_vendors: int = 2, db: Session = Depends(get_db)):
    """
    Find PANs that are used by multiple vendors (default: 2+).
    """
    grouped = (
        db.query(
            Vendor.pan.label("pan"),
            func.count(Vendor.id).label("vendor_count")
        )
        .filter(Vendor.pan.isnot(None))
        .group_by(Vendor.pan)
        .having(func.count(Vendor.id) >= min_vendors)
        .all()
    )

    result = []
    for row in grouped:
        pan = row.pan
        vendor_count = row.vendor_count

        vendors = (
            db.query(Vendor)
            .filter(Vendor.pan == pan)
            .order_by(Vendor.id)
            .all()
        )

        result.append({
            "pan": pan,
            "vendor_count": vendor_count,
            "vendors": [
                {
                    "id": v.id,
                    "name": v.name,
                    "gstin": v.gstin,
                    "address": v.address,
                    "state": v.state
                } for v in vendors
            ]
        })

    return {
        "count": len(result),
        "min_vendors": min_vendors,
        "clusters": result
    }
