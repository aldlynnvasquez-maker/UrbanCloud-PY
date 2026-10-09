import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.configuracion.base import sesion_bd
from app.modelos.dominio import EstadoIncidencia, Incidencia, Usuario
from app.repositorios.consultas import detalle, pagina, resumen
from app.seguridad.sesiones import exigir_rol
from app.servicios import flujo

router = APIRouter(prefix="/operacion", dependencies=[Depends(exigir_rol("Operador"))])


class Revision(BaseModel):
    categoria_id: int
    prioridad_id: int
    area_id: int
    motivo: str | None = Field(default=None, max_length=1000)


class Resolucion(BaseModel):
    decision: str
    motivo: str = Field(min_length=10, max_length=2000)


@router.get("/incidencias")
def bandeja(request: Request, page: int = Query(default=1, ge=1), db: Session = Depends(sesion_bd)):
    consulta = select(Incidencia).join(EstadoIncidencia).where(
        EstadoIncidencia.nombre.in_(["En revisión", "Revisión solicitada"])).order_by(Incidencia.created_at)
    return pagina(db, consulta, page, lambda item: detalle(db, item, str(request.base_url)))


@router.get("/incidencias/todas")
def todas(buscar: str | None = Query(default=None, max_length=90),
          estado: str | None = Query(default=None, max_length=50),
          area_id: int | None = None, prioridad_id: int | None = None,
          page: int = Query(default=1, ge=1), db: Session = Depends(sesion_bd)):
    consulta = select(Incidencia)
    if buscar:
        patron = f"%{buscar}%"
        consulta = consulta.where(or_(Incidencia.codigo.ilike(patron), Incidencia.titulo.ilike(patron),
                                      Incidencia.direccion.ilike(patron)))
    if estado:
        consulta = consulta.join(EstadoIncidencia).where(EstadoIncidencia.nombre == estado)
    if area_id:
        consulta = consulta.where(Incidencia.area_id == area_id)
    if prioridad_id:
        consulta = consulta.where(Incidencia.prioridad_id == prioridad_id)
    return pagina(db, consulta.order_by(Incidencia.created_at.desc()), page, lambda item: resumen(db, item))


@router.get("/incidencias/{incidencia_id}")
def mostrar(incidencia_id: uuid.UUID, request: Request, db: Session = Depends(sesion_bd)):
    item = db.get(Incidencia, incidencia_id)
    if item is None:
        raise HTTPException(404, "No encontramos lo que buscas.")
    return detalle(db, item, str(request.base_url))


@router.post("/incidencias/{incidencia_id}/revisar")
def revisar(incidencia_id: uuid.UUID, datos: Revision,
            usuario: Usuario = Depends(exigir_rol("Operador")), db: Session = Depends(sesion_bd)):
    return flujo.revisar(db, incidencia_id, usuario, datos.model_dump())


@router.post("/incidencias/{incidencia_id}/resolver-revision")
def resolver(incidencia_id: uuid.UUID, datos: Resolucion,
             usuario: Usuario = Depends(exigir_rol("Operador")), db: Session = Depends(sesion_bd)):
    return flujo.resolver_revision(db, incidencia_id, usuario, datos.decision, datos.motivo)
