import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db_session():
    """Mock database session for unit tests."""
    session = MagicMock(spec=Session)
    session.flush = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.execute = MagicMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    return session