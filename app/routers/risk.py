# app/routers/risk.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict,Any
from ..db import get_db
from ..schemas.risk import VendorRisk
from ..services.risk_service import compute_vendor_risk,compute_all_vendors_risk
from ..genai.risk_explainer import generate_risk_explanation

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/vendor/{vendor_id}", response_model=VendorRisk)
def get_vendor_risk(vendor_id: int, db: Session = Depends(get_db)):
    try:
        risk = compute_vendor_risk(db, vendor_id)
    except ValueError as e:
        if str(e) == "VENDOR_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found",
            )
        else:
            raise

    return risk

@router.get("/vendors", response_model=List[VendorRisk])
def list_vendors_risk(db: Session = Depends(get_db)):
    """
    Return risk info for all vendors, sorted by risk_score desc.
    """
    risks = compute_all_vendors_risk(db)
    return risks


@router.get("/vendor/{vendor_id}/explanation")
def get_vendor_risk_with_explanation(
    vendor_id: int, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns risk JSON + an AI-generated explanation.
    If LLM is not configured, explanation will be null.
    """
    try:
        risk = compute_vendor_risk(db, vendor_id)
    except ValueError as e:
        if str(e) == "VENDOR_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found",
            )
        else:
            raise

    explanation = generate_risk_explanation(risk)

    return {
        "risk": risk,
        "ai_explanation": explanation,
        "llm_enabled": explanation is not None,
    }
