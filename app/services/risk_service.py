# app/services/risk_service.py

from typing import Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.vendor import Vendor
from ..models.invoice import Invoice
from ..neo4j_client import get_neo4j_driver


def _get_vendor_or_404(db: Session, vendor_id: int) -> Vendor:
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise ValueError("VENDOR_NOT_FOUND")
    return vendor


def _get_cycles_for_vendor(vendor_id: int, max_length: int = 5) -> List[Dict[str, Any]]:
    """
    Return all unique cycles that involve this vendor.
    We can keep this simpler than the /graph/cycles endpoint for now.
    """
    driver = get_neo4j_driver()
    cycles: List[Dict[str, Any]] = []

    query = f"""
    MATCH p = (v:Vendor {{id: $vendor_id}})-[:SUPPLIES_TO*2..{max_length}]->(v)
    RETURN [n IN nodes(p) | {{id: n.id, name: n.name, gstin: n.gstin}}] AS vendors
    """

    with driver.session() as session:
        result = session.run(query, vendor_id=vendor_id)

        for record in result:
            vendors_in_path = record["vendors"]
            if not vendors_in_path or len(vendors_in_path) < 3:
                continue
            cycles.append(
                {
                    "length": len(vendors_in_path),
                    "vendors": vendors_in_path,
                }
            )

    return cycles


def _get_shared_address_cluster(db: Session, vendor: Vendor):
    """
    Return list of other vendors sharing the same address, if any.
    """
    if not vendor.address:
        return []

    others = (
        db.query(Vendor)
        .filter(
            Vendor.address == vendor.address,
            Vendor.id != vendor.id,
        )
        .all()
    )

    return [
        {
            "id": v.id,
            "name": v.name,
            "gstin": v.gstin,
            "state": v.state,
            "pan": v.pan,
        }
        for v in others
    ]


def _get_invoice_stats(db: Session, vendor_id: int) -> Dict[str, int]:
    """
    Get basic counts: incoming and outgoing invoices.
    """
    outgoing_count = (
        db.query(func.count(Invoice.id))
        .filter(Invoice.from_vendor_id == vendor_id)
        .scalar()
    )

    incoming_count = (
        db.query(func.count(Invoice.id))
        .filter(Invoice.to_vendor_id == vendor_id)
        .scalar()
    )

    return {
        "outgoing": outgoing_count or 0,
        "incoming": incoming_count or 0,
    }


def compute_vendor_risk(db: Session, vendor_id: int) -> Dict[str, Any]:
    """
    Compute a simple risk score + flags for a vendor based on:
    - circular trading cycles
    - shared address
    - no invoices (shell)
    """

    vendor = _get_vendor_or_404(db, vendor_id)

    # 1) graph-based cycles
    cycles = _get_cycles_for_vendor(vendor_id)
    in_cycle = len(cycles) > 0

    # 2) shared addresses
    shared_address_vendors = _get_shared_address_cluster(db, vendor)
    has_shared_address = len(shared_address_vendors) > 0
    
    # 2b) shared PAN
    shared_pan_vendors = _get_shared_pan_vendors(db, vendor)
    has_shared_pan = len(shared_pan_vendors) > 0

    # 3) basic invoice stats
    invoice_stats = _get_invoice_stats(db, vendor_id)
    no_invoices = (invoice_stats["incoming"] == 0 and invoice_stats["outgoing"] == 0)

    # --- scoring ---
    score = 0
    flags: List[str] = []

    if in_cycle:
        score += 50
        flags.append("IN_CYCLE")

    if has_shared_address:
        score += 30
        flags.append("SHARED_ADDRESS")
        
    if has_shared_pan:
        score += 30
        flags.append("SHARED_PAN")

    if no_invoices:
        score += 20
        flags.append("NO_INVOICES")

    if score >= 60:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "vendor": {
            "id": vendor.id,
            "name": vendor.name,
            "gstin": vendor.gstin,
            "state": vendor.state,
            "address": vendor.address,
            "pan": vendor.pan,
        },
        "risk_score": score,
        "risk_level": level,
        "flags": flags,
        "details": {
            "cycles": cycles,
            "shared_address_vendors": shared_address_vendors,
            "invoice_stats": invoice_stats,
        },
    }


def compute_all_vendors_risk(db: Session) -> List[Dict[str, Any]]:
    """
    Compute risk for all vendors.
    NOTE: This calls compute_vendor_risk per vendor (OK for small/medium data).
    """
    vendors = db.query(Vendor).order_by(Vendor.id).all()

    results: List[Dict[str, Any]] = []
    for v in vendors:
        try:
            risk = compute_vendor_risk(db, v.id)
            results.append(risk)
        except ValueError:
            # if vendor not found (shouldn't happen), skip
            continue

    # Sort by risk_score descending
    results.sort(key=lambda r: r["risk_score"], reverse=True)
    return results


def _get_shared_pan_vendors(db: Session, vendor: Vendor):
    """
    Return list of other vendors sharing the same PAN, if any.
    """
    if not vendor.pan:
        return []

    others = (
        db.query(Vendor)
        .filter(
            Vendor.pan == vendor.pan,
            Vendor.id != vendor.id,
        )
        .all()
    )

    return [
        {
            "id": v.id,
            "name": v.name,
            "gstin": v.gstin,
            "state": v.state,
            "address": v.address,
        }
        for v in others
    ]
