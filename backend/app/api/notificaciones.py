import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.configuracion.base import sesion_bd
from app.modelos.dominio import Notificacion, Usuario, ahora
from app.repositorios.consultas import iso, pagina
from app.seguridad.sesiones import usuario_actual

router = APIRouter(dependencies=[Depends(usuario_actual)])


def _notificacion(item: Notificacion) -> dict:
    return {"id": str(item.id), "usuario_id": item.usuario_id,
            "incidencia_id": str(item.incidencia_id) if item.incidencia_id else None,
            "titulo": item.titulo, "mensaje": item.mensaje,
            "leida_en": iso(item.leida_en), "created_at": iso(item.created_at)}


@router.get("/notificaciones")
def listar(page: int = Query(default=1, ge=1), usuario: Usuario = Depends(usuario_actual),
           db: Session = Depends(sesion_bd)):
    no_leidas = db.scalar(select(func.count(Notificacion.id)).where(
        Notificacion.usuario_id == usuario.id, Notificacion.leida_en.is_(None))) or 0
    consulta = select(Notificacion).where(Notificacion.usuario_id == usuario.id)
    return {"no_leidas": no_leidas,
            "notificaciones": pagina(db, consulta.order_by(Notificacion.created_at.desc()),
                                    page, _notificacion)}


@router.patch("/notificaciones/leer-todas")
def marcar_todas(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(sesion_bd)):
    for item in db.scalars(select(Notificacion).where(
        Notificacion.usuario_id == usuario.id, Notificacion.leida_en.is_(None))):
        item.leida_en = ahora()
    db.commit()
    return {"mensaje": "Notificaciones leídas."}


@router.patch("/notificaciones/{notificacion_id}/leer")
def marcar_leida(notificacion_id: uuid.UUID, usuario: Usuario = Depends(usuario_actual),
                  db: Session = Depends(sesion_bd)):
    item = db.get(Notificacion, notificacion_id)
    if item is None:
        raise HTTPException(404, "No encontramos lo que buscas.")
    if item.usuario_id != usuario.id:
        raise HTTPException(403, "No tienes permiso para esta notificación.")
    item.leida_en = item.leida_en or ahora()
    db.commit()
    return {"mensaje": "Notificación leída."}
