from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db

Db = Depends(get_db)
