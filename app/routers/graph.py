# app/routers/graph.py

from typing import List,Any,Dict,Tuple
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..graph.sync import sync_all_to_neo4j
from ..neo4j_client import get_neo4j_driver


router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/sync")
def sync_graph(db: Session = Depends(get_db)):
    vendor_count, invoice_count = sync_all_to_neo4j(db)
    return {
        "status": "ok",
        "vendors_synced": vendor_count,
        "invoices_synced": invoice_count,
    }
    
    
# @router.get("/cycles")
# def get_cycles(max_length: int = 5) -> Dict[str, Any]:
#     """
#     Find circular trading patterns: Vendor -> ... -> Vendor
#     max_length: maximum number of hops in the cycle (min 2)
#     """
#     driver = get_neo4j_driver()

#     # Clamp max_length to a safe range
#     if max_length < 2:
#         max_length = 2
#     if max_length > 10:
#         max_length = 10

#     # Build query string with the integer literal
#     query = f"""
#     MATCH p = (v:Vendor)-[:SUPPLIES_TO*2..{max_length}]->(v)
#     RETURN [n IN nodes(p) | {{id: n.id, name: n.name, gstin: n.gstin}}] AS vendors
#     """

#     cycles: List[Dict[str, Any]] = []

#     with driver.session() as session:
#         result = session.run(query)

#         for record in result:
#             vendors_in_cycle = record["vendors"]
#             cycles.append(
#                 {
#                     "length": len(vendors_in_cycle),
#                     "vendors": vendors_in_cycle,
#                 }
#             )

#     return {
#         "count": len(cycles),
#         "cycles": cycles,
#         "max_length_used": max_length,
#     }


def _canonical_cycle_key(ids: List[int]) -> Tuple[int, ...]:
    """
    Given a list of node IDs representing a cycle without the repeated end node,
    return a canonical tuple so that rotations and reversed order of the same
    cycle map to the same key.
    """
    if not ids:
        return tuple()

    # ensure we work on a copy
    ids = list(ids)

    # generate all rotations
    n = len(ids)
    rotations = []

    for i in range(n):
        rot = ids[i:] + ids[:i]
        rotations.append(rot)

    # also consider reversed direction
    rev = list(reversed(ids))
    for i in range(n):
        rot_rev = rev[i:] + rev[:i]
        rotations.append(rot_rev)

    # pick lexicographically smallest tuple among all rotations (both directions)
    canon = min(tuple(r) for r in rotations)
    return canon


@router.get("/cycles")
def get_cycles(max_length: int = 5) -> Dict[str, Any]:
    """
    Find unique circular trading patterns: Vendor -> ... -> Vendor.
    Returns deduplicated cycles (same loop in different rotations counted once).
    max_length: maximum number of hops in the cycle (min 2, max 10).
    """
    driver = get_neo4j_driver()

    if max_length < 2:
        max_length = 2
    if max_length > 10:
        max_length = 10

    query = f"""
    MATCH p = (v:Vendor)-[:SUPPLIES_TO*2..{max_length}]->(v)
    RETURN [n IN nodes(p) | {{id: n.id, name: n.name, gstin: n.gstin}}] AS vendors
    """

    unique_cycles: Dict[Tuple[int, ...], Dict[str, Any]] = {}

    with driver.session() as session:
        result = session.run(query)

        for record in result:
            vendors_in_path = record["vendors"]

            if not vendors_in_path or len(vendors_in_path) < 3:
                continue

            # Convert to IDs
            ids = [v["id"] for v in vendors_in_path]

            # For cycles Neo4j returns, first and last are the same node.
            # Remove the last duplicate if present.
            if ids[0] == ids[-1]:
                ids = ids[:-1]

            # Ignore trivial or degenerate ones
            if len(ids) < 2:
                continue

            # Canonical key for this cycle
            key = _canonical_cycle_key(ids)

            # Store the first representative for this key
            if key not in unique_cycles:
                unique_cycles[key] = {
                    "length": len(ids),
                    "vendors": vendors_in_path,
                }

    cycles_list = list(unique_cycles.values())

    return {
        "count": len(cycles_list),
        "cycles": cycles_list,
        "max_length_used": max_length,
    }
