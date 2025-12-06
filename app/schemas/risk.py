# app/schemas/risk.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class VendorInfo(BaseModel):
    id: int
    name: str
    gstin: str
    state: Optional[str] = None
    address: Optional[str] = None
    pan: Optional[str] = None


class VendorRiskDetails(BaseModel):
    cycles: List[Dict[str, Any]]
    shared_address_vendors: List[Dict[str, Any]]
    invoice_stats: Dict[str, int]


class VendorRisk(BaseModel):
    vendor: VendorInfo
    risk_score: int
    risk_level: str
    flags: List[str]
    details: VendorRiskDetails
