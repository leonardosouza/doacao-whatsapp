import os
import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# ── SET TEST ENVIRONMENT BEFORE ANY APP IMPORTS ──────────────────────
os.environ.update(
    {
        "APP_ENV": "test",
        "APP_NAME": "DoaZap-Test",
        "DEBUG": "true",
        "API_KEY": "test-api-key-12345",
        "DATABASE_URL": "sqlite:///:memory:",
        "OPENAI_API_KEY": "sk-test-fake-key-not-real",
        "OPENAI_MODEL": "gpt-4o-mini",
        "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
        "OPENAI_TEMPERATURE": "0.0",
        "ZAPI_INSTANCE_ID": "test-instance-id",
        "ZAPI_TOKEN": "test-token",
        "ZAPI_CLIENT_TOKEN": "test-client-token",
    }
)

# ── NOW SAFE TO IMPORT APP MODULES ──────────────────────────────────
from app.database import Base, get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.models.message import Message  # noqa: E402
from app.models.ong import Ong  # noqa: E402


# ── DATABASE FIXTURES ────────────────────────────────────────────────
@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    from starlette.testclient import TestClient

    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(db_session):
    from httpx import ASGITransport, AsyncClient

    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


# ── DATA FACTORY FIXTURES ────────────────────────────────────────────
@pytest.fixture
def sample_ong_data():
    return {
        "name": "ONG Teste",
        "category": "Saúde",
        "city": "São Paulo",
        "state": "SP",
        "phone": "(11) 99999-0000",
        "website": "https://ongteste.org.br",
        "pix_key": "contato@ongteste.org.br",
    }


@pytest.fixture
def sample_ong_in_db(db_session, sample_ong_data):
    ong = Ong(**sample_ong_data)
    db_session.add(ong)
    db_session.commit()
    db_session.refresh(ong)
    return ong


@pytest.fixture
def multiple_ongs_in_db(db_session):
    ongs_data = [
        {"name": "ONG Fome A", "category": "Fome", "city": "Rio de Janeiro", "state": "RJ", "pix_key": "pix@fome.org"},
        {"name": "ONG Saúde B", "category": "Saúde", "city": "São Paulo", "state": "SP", "bank_info": "Banco 001 Ag 1234"},
        {"name": "ONG Animais C", "category": "Animais", "city": "Curitiba", "state": "PR"},
        {"name": "ONG Assistência D", "category": "Assistência Social", "city": "São Paulo", "state": "SP"},
        {"name": "ONG Crianças E", "category": "Crianças", "city": "Belo Horizonte", "state": "MG", "donation_url": "https://doe.org"},
        {"name": "ONG Inativa F", "category": "Saúde", "city": "Salvador", "state": "BA", "is_active": False},
    ]
    ongs = []
    for data in ongs_data:
        ong = Ong(**data)
        db_session.add(ong)
        ongs.append(ong)
    db_session.commit()
    for ong in ongs:
        db_session.refresh(ong)
    return ongs


@pytest.fixture
def sample_conversation(db_session):
    conv = Conversation(phone_number="5511999990000")
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)
    return conv


# ── AUTH HEADER FIXTURES ─────────────────────────────────────────────
@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-api-key-12345"}


@pytest.fixture
def wrong_auth_headers():
    return {"X-API-Key": "wrong-key"}
