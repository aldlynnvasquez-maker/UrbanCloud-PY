from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.configuracion.ajustes import ajustes
from app.configuracion.base import Base
from app.modelos import dominio  # noqa: F401: registra los modelos

config = context.config
config.set_main_option("sqlalchemy.url", ajustes().database_url.replace("%", "%%"))
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def ejecutar_offline():
    context.configure(url=ajustes().database_url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def ejecutar_online():
    motor = engine_from_config(config.get_section(config.config_ini_section),
                               prefix="sqlalchemy.", poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    ejecutar_offline()
else:
    ejecutar_online()
