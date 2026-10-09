import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.configuracion.base import sesion_bd
from app.modelos.dominio import AsignacionIncidencia, Incidencia, Usuario
from app.repositorios.consultas import detalle, pagina, resumen
from app.seguridad.sesiones import exigir_rol
from app.servicios.flujo import actualizar_tarea

router = APIRouter(prefix="/tecnico", dependencies=[Depends(exigir_rol("Personal técnico"))])


@router.get("/tareas")
def tareas(page: int = Query(default=1, ge=1), usuario: Usuario = Depends(exigir_rol("Personal técnico")),
           db: Session = Depends(sesion_bd)):
    consulta = select(Incidencia).join(AsignacionIncidencia).where(
        AsignacionIncidencia.tecnico_id == usuario.id,
        AsignacionIncidencia.activa.is_(True)).order_by(Incidencia.created_at.desc())
    return pagina(db, consulta, page, lambda item: resumen(db, item))


@router.get("/historial")
def historial(page: int = Query(default=1, ge=1), usuario: Usuario = Depends(exigir_rol("Personal técnico")),
              db: Session = Depends(sesion_bd)):
    asignacion_activa = aliased(AsignacionIncidencia)
    activa = select(asignacion_activa.id).where(
        asignacion_activa.incidencia_id == Incidencia.id,
        asignacion_activa.tecnico_id == usuario.id,
        asignacion_activa.activa.is_(True)).correlate(Incidencia).exists()
    consulta = select(Incidencia).join(AsignacionIncidencia).where(
        AsignacionIncidencia.tecnico_id == usuario.id,
        AsignacionIncidencia.activa.is_(False), ~activa).distinct().order_by(Incidencia.created_at.desc())
    return pagina(db, consulta, page, lambda item: resumen(db, item))


@router.get("/tareas/{incidencia_id}")
def mostrar(incidencia_id: uuid.UUID, request: Request,
            usuario: Usuario = Depends(exigir_rol("Personal técnico")), db: Session = Depends(sesion_bd)):
    asignacion = db.scalar(select(AsignacionIncidencia).where(
        AsignacionIncidencia.incidencia_id == incidencia_id,
        AsignacionIncidencia.tecnico_id == usuario.id, AsignacionIncidencia.activa.is_(True)))
    if asignacion is None:
        raise HTTPException(403, "No tienes permiso para ver esta tarea.")
    item = db.get(Incidencia, incidencia_id)
    if item is None:
        raise HTTPException(404, "No encontramos lo que buscas.")
    return detalle(db, item, str(request.base_url))


@router.post("/tareas/{incidencia_id}/actualizar")
async def actualizar(incidencia_id: uuid.UUID,
                     accion: str = Form(), comentario: str = Form(min_length=10, max_length=2000),
                     fotografia: UploadFile | None = File(default=None),
                     tipo_evidencia: str | None = Form(default=None),
                     usuario: Usuario = Depends(exigir_rol("Personal técnico")),
                     db: Session = Depends(sesion_bd)):
    if tipo_evidencia and tipo_evidencia not in {"ATENCION", "CIERRE", "OTRA"}:
        raise HTTPException(422, "Tipo de evidencia no válido.")
    if tipo_evidencia == "CIERRE" and accion != "atendido":
        raise HTTPException(422, "CIERRE solo corresponde a una tarea atendida.")
    if accion == "atendido" and tipo_evidencia not in {None, "CIERRE"}:
        raise HTTPException(422, "La evidencia final debe ser de tipo CIERRE.")
    foto = await fotografia.read(5 * 1024 * 1024 + 1) if fotografia else None
    return actualizar_tarea(db, incidencia_id, usuario,
                            {"accion": accion, "comentario": comentario, "tipo_evidencia": tipo_evidencia},
                            foto, fotografia.content_type if fotografia else None)
