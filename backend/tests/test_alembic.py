from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.configuracion.ajustes import ajustes
from app.configuracion.base import Base
from app.modelos import dominio  # noqa: F401: registra las tablas originales


def test_linea_base_crea_solo_la_tabla_nueva(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'esquema_existente.sqlite').as_posix()}"
    motor = create_engine(url)
    originales = [tabla for nombre, tabla in Base.metadata.tables.items()
                 if nombre != "sesiones_renovacion"]
    Base.metadata.create_all(motor, tables=originales)
    monkeypatch.setenv("DATABASE_URL", url)
    ajustes.cache_clear()

    config = Config("alembic.ini")
    command.stamp(config, "0001_linea_base")
    command.upgrade(config, "head")

    nombres = set(inspect(motor).get_table_names())
    assert {"usuarios", "incidencias", "notificaciones_incidencia",
            "sesiones_renovacion", "alembic_version"}.issubset(nombres)
    assert len(nombres) == len(originales) + 2
    motor.dispose()
    ajustes.cache_clear()
