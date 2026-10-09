from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.dominio import Incidencia, Notificacion, Rol, SeguidorIncidencia, Usuario, AsignacionIncidencia


def notificar_evento(db: Session, incidencia: Incidencia, estado: str,
                    mensaje_publico: str | None = None) -> None:
    destinatarios = {incidencia.ciudadano_id}
    destinatarios.update(db.scalars(select(SeguidorIncidencia.ciudadano_id)
                                   .where(SeguidorIncidencia.incidencia_id == incidencia.id)).all())
    roles = []
    if estado in {"En revisión", "Revisión solicitada"}:
        roles.append("Operador")
    if estado in {"Derivado", "Atendido", "Impedido"}:
        roles.append("Supervisor")
    if roles:
        destinatarios.update(db.scalars(select(Usuario.id).join(Rol, Rol.id == Usuario.rol_id)
                                       .where(Usuario.activo.is_(True), Rol.nombre.in_(roles))).all())
    if estado == "Asignado":
        destinatarios.update(db.scalars(select(AsignacionIncidencia.tecnico_id)
                                       .where(AsignacionIncidencia.incidencia_id == incidencia.id,
                                              AsignacionIncidencia.activa.is_(True))).all())
    db.add_all([Notificacion(usuario_id=usuario_id, incidencia_id=incidencia.id,
                             titulo=f"Incidencia {incidencia.codigo}",
                             mensaje=mensaje_publico or f"Estado actualizado: {estado}.")
                for usuario_id in destinatarios])
