from typing import Generator
from sqlalchemy.orm import Session

def get_db() -> Generator:
    db = Session()
    try:
        yield db
    finally:
        db.close()

