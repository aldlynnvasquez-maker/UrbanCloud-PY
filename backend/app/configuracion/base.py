"""Conexión y sesiones SQLAlchemy. Nunca crea tablas en PostgreSQL al importar."""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.configuracion.ajustes import ajustes


class Base(DeclarativeBase):
    pass


@lru_cache
def motor():
    url = ajustes().database_url
    argumentos = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=argumentos)


def sesion_bd():
    fabrica = sessionmaker(bind=motor(), autoflush=False, expire_on_commit=False)
    with fabrica() as sesion:
        yield sesion


def guardar(sesion: Session) -> None:
    sesion.commit()
