# app/graph/sync.py

from typing import Tuple
from sqlalchemy.orm import Session

from ..neo4j_client import get_neo4j_driver
from ..models.vendor import Vendor
from ..models.invoice import Invoice


def sync_all_to_neo4j(db: Session) -> Tuple[int, int]:
    """
    Full rebuild of the Neo4j graph from Postgres data.
    Returns: (vendor_count, invoice_count)
    """
    # Fetch data from Postgres
    vendors = db.query(Vendor).all()
    invoices = db.query(Invoice).all()

    vendor_count = len(vendors)
    invoice_count = len(invoices)

    driver = get_neo4j_driver()

    with driver.session() as session:
        # ⚠️ For now: clear everything (dev mode)
        session.run("MATCH (n) DETACH DELETE n")

        # Prepare vendor dicts for UNWIND
        vendor_dicts = [
            {
                "id": v.id,
                "gstin": v.gstin,
                "name": v.name,
                "address": v.address,
                "state": v.state,
                "pan": v.pan,
            }
            for v in vendors
        ]

        if vendor_dicts:
            session.run(
                """
                UNWIND $vendors AS v
                MERGE (ven:Vendor {id: v.id})
                SET ven.gstin = v.gstin,
                    ven.name = v.name,
                    ven.address = v.address,
                    ven.state = v.state,
                    ven.pan = v.pan
                """,
                vendors=vendor_dicts,
            )

        # Prepare invoice dicts for UNWIND
        invoice_dicts = [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "amount": inv.amount,
                "date": inv.date.isoformat(),  # "YYYY-MM-DD"
                "from_vendor_id": inv.from_vendor_id,
                "to_vendor_id": inv.to_vendor_id,
            }
            for inv in invoices
        ]

        if invoice_dicts:
            session.run(
                """
                UNWIND $invoices AS i
                MATCH (from:Vendor {id: i.from_vendor_id})
                MATCH (to:Vendor {id: i.to_vendor_id})
                MERGE (from)-[r:SUPPLIES_TO {invoice_id: i.id}]->(to)
                SET r.invoice_number = i.invoice_number,
                    r.amount = i.amount,
                    r.date = date(i.date)
                """,
                invoices=invoice_dicts,
            )

    return vendor_count, invoice_count

# app/graph/sync.py (add at top)
from ..db import SessionLocal

def sync_all_to_neo4j_using_new_session() -> Tuple[int, int]:
    """
    Create a fresh DB session and call sync_all_to_neo4j; safe for background tasks.
    """
    db = SessionLocal()
    try:
        return sync_all_to_neo4j(db)
    finally:
        db.close()

