# app/setup_db.py

from .db import engine
from .models.base import Base
import app.models.vendor  # Needed to register models
import app.models.invoice
import app.models.director
import app.models.vendor_director

def init_db():
    Base.metadata.create_all(bind=engine)
