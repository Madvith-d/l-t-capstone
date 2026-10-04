import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["RETRIEVAL_SCORE_THRESHOLD"] = "0.1"
os.environ["RETRIEVAL_MIN_TERM_COVERAGE"] = "0.15"
os.environ["LLM_PROVIDER"] = "local"
os.environ["EMBEDDING_PROVIDER"] = "local"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    with TestingSession() as session:
        yield session


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(
        app,
        raise_server_exceptions=True,
        headers={"X-User-ID": "test-user-0001"},
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()
