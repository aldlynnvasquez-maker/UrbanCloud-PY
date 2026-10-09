import mimetypes
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.configuracion.base import sesion_bd
from app.modelos.dominio import AsignacionIncidencia, EvidenciaIncidencia, Incidencia, SeguidorIncidencia, Usuario
from app.seguridad.sesiones import rol_usuario, usuario_actual
from app.servicios.almacenamiento import almacenamiento

router = APIRouter(dependencies=[Depends(usuario_actual)])


def _leer(incidencia_id: uuid.UUID, evidencia_id: uuid.UUID, usuario: Usuario,
         db: Session, descarga: bool) -> Response:
    incidencia = db.get(Incidencia, incidencia_id)
    evidencia = db.get(EvidenciaIncidencia, evidencia_id)
    if incidencia is None or evidencia is None or evidencia.incidencia_id != incidencia.id:
        raise HTTPException(404, "No encontramos lo que buscas.")
    rol = rol_usuario(db, usuario)
    permitido = False
    if rol == "Ciudadano":
        permitido = incidencia.ciudadano_id == usuario.id or db.scalar(select(SeguidorIncidencia.id).where(
            SeguidorIncidencia.incidencia_id == incidencia.id,
            SeguidorIncidencia.ciudadano_id == usuario.id)) is not None
    elif rol in {"Operador", "Supervisor"}:
        permitido = True
    elif rol == "Personal técnico":
        permitido = db.scalar(select(AsignacionIncidencia.id).where(
            AsignacionIncidencia.incidencia_id == incidencia.id,
            AsignacionIncidencia.tecnico_id == usuario.id,
            AsignacionIncidencia.activa.is_(True))) is not None
    if not permitido:
        raise HTTPException(403, "No tienes permiso para ver esta evidencia.")
    try:
        contenido = almacenamiento().leer(evidencia.ruta_archivo)
    except FileNotFoundError:
        raise HTTPException(404, "No encontramos el archivo.") from None
    mime = mimetypes.guess_type(evidencia.ruta_archivo)[0] or "application/octet-stream"
    nombre = evidencia.ruta_archivo.rsplit("/", 1)[-1]
    return Response(content=contenido, media_type=mime,
                    headers={"Content-Disposition": f'{"attachment" if descarga else "inline"}; filename="{nombre}"',
                             "Cache-Control": "private, no-store"})


@router.get("/incidencias/{incidencia_id}/evidencias/{evidencia_id}")
def descargar(incidencia_id: uuid.UUID, evidencia_id: uuid.UUID,
              usuario: Usuario = Depends(usuario_actual), db: Session = Depends(sesion_bd)):
    return _leer(incidencia_id, evidencia_id, usuario, db, True)


@router.get("/incidencias/{incidencia_id}/evidencias/{evidencia_id}/ver")
def ver(incidencia_id: uuid.UUID, evidencia_id: uuid.UUID,
        usuario: Usuario = Depends(usuario_actual), db: Session = Depends(sesion_bd)):
    return _leer(incidencia_id, evidencia_id, usuario, db, False)
