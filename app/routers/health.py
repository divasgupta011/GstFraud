# app/routers/health.py
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..neo4j_client import get_neo4j_driver

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health_root():
    return {"status": "ok"}

@router.get("/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"postgres": "ok"}

@router.get("/neo4j")
def health_neo4j():
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run("RETURN 1 AS ok")
        value = result.single()["ok"]
    return {"neo4j": "ok", "value": value}
