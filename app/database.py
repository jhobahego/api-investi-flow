from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

database_url = settings.require_database_url()

# Neon (and pgbouncer) can close idle connections. Pre-ping validates a
# pooled connection before use and recycles it periodically, so long-running
# API/worker processes reconnect instead of failing with
# "SSL connection has been closed unexpectedly".
engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency para obtener una sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
