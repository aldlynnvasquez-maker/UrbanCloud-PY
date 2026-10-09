import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session

from app.configuracion.base import sesion_bd
from app.modelos.dominio import (
    Area, AsignacionIncidencia, EstadoIncidencia, Incidencia, Prioridad, Rol, Usuario, ahora,
)
from app.repositorios.consultas import detalle, pagina, resumen
from app.seguridad.sesiones import exigir_rol
from app.servicios import flujo

router = APIRouter(prefix="/supervision", dependencies=[Depends(exigir_rol("Supervisor"))])
ESTADOS = {"Derivado", "Asignado", "En atención", "Atendido", "Impedido"}


class Asignar(BaseModel):
    tecnico_id: int
    comentario: str | None = Field(default=None, max_length=1000)


class Motivo(BaseModel):
    motivo: str = Field(min_length=10, max_length=2000)


class Cierre(BaseModel):
    comentario: str | None = Field(default=None, max_length=2000)


def _carga(db: Session, tecnico_id: int) -> int:
    return db.scalar(select(func.count(AsignacionIncidencia.id))
                     .where(AsignacionIncidencia.tecnico_id == tecnico_id,
                            AsignacionIncidencia.activa.is_(True))) or 0


@router.get("/equipo")
def equipo(db: Session = Depends(sesion_bd)):
    tecnicos = db.scalars(select(Usuario).join(Rol, Rol.id == Usuario.rol_id)
                          .where(Rol.nombre == "Personal técnico", Usuario.activo.is_(True))
                          .order_by(Usuario.nombre)).all()
    return [{"id": item.id, "nombre": item.nombre,
             "area": db.get(Area, item.area_id).nombre if item.area_id else None,
             "tareas_activas": _carga(db, item.id)} for item in tecnicos]


@router.get("/incidencias")
def listar(estado: str | None = None, riesgos: bool = False,
           page: int = Query(default=1, ge=1), db: Session = Depends(sesion_bd)):
    if estado is not None and estado not in ESTADOS:
        raise HTTPException(422, "Estado no válido.")
    consulta = select(Incidencia).join(EstadoIncidencia).where(
        EstadoIncidencia.nombre.in_([estado] if estado else ESTADOS))
    if riesgos:
        consulta = consulta.outerjoin(Prioridad, Prioridad.id == Incidencia.prioridad_id).where(or_(
            Prioridad.nombre == "Alta", EstadoIncidencia.nombre.in_(["Impedido", "Derivado"]),
            Incidencia.fecha_limite <= ahora() + timedelta(hours=48)))
    return pagina(db, consulta.order_by(Incidencia.created_at), page, lambda item: resumen(db, item))


@router.get("/incidencias/{incidencia_id}")
def mostrar(incidencia_id: uuid.UUID, request: Request, db: Session = Depends(sesion_bd)):
    item = db.get(Incidencia, incidencia_id)
    if item is None:
        raise HTTPException(404, "No encontramos lo que buscas.")
    tecnicos = db.scalars(select(Usuario).join(Rol, Rol.id == Usuario.rol_id)
                          .where(Usuario.activo.is_(True), Usuario.area_id == item.area_id,
                                 Rol.nombre == "Personal técnico")).all()
    return {"incidencia": detalle(db, item, str(request.base_url)),
            "tecnicos_compatibles": [{"id": tecnico.id, "nombre": tecnico.nombre,
                                      "asignaciones_activas": _carga(db, tecnico.id)}
                                     for tecnico in tecnicos]}


@router.post("/incidencias/{incidencia_id}/asignar")
def asignar(incidencia_id: uuid.UUID, datos: Asignar,
            usuario: Usuario = Depends(exigir_rol("Supervisor")), db: Session = Depends(sesion_bd)):
    return flujo.asignar(db, incidencia_id, usuario, datos.model_dump())


@router.post("/incidencias/{incidencia_id}/devolver-operador")
def devolver(incidencia_id: uuid.UUID, datos: Motivo,
             usuario: Usuario = Depends(exigir_rol("Supervisor")), db: Session = Depends(sesion_bd)):
    return flujo.devolver_operador(db, incidencia_id, usuario, datos.motivo)


@router.post("/incidencias/{incidencia_id}/cerrar")
def cerrar(incidencia_id: uuid.UUID, datos: Cierre,
           usuario: Usuario = Depends(exigir_rol("Supervisor")), db: Session = Depends(sesion_bd)):
    return flujo.cerrar(db, incidencia_id, usuario, datos.comentario)
