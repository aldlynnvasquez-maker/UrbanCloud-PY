from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.configuracion.base import sesion_bd
from app.modelos.dominio import Area, Categoria, Distrito, EstadoIncidencia, Prioridad, Rol, Usuario
from app.seguridad.sesiones import usuario_actual

router = APIRouter()


@router.get("/catalogos")
def listar(_usuario: Usuario = Depends(usuario_actual), db: Session = Depends(sesion_bd)):
    def items(modelo, *columnas, filtro=None, orden=None):
        consulta = select(modelo)
        if filtro is not None:
            consulta = consulta.where(filtro)
        if orden is not None:
            consulta = consulta.order_by(orden)
        return [{columna: getattr(fila, columna) for columna in columnas}
                for fila in db.scalars(consulta).all()]

    return {
        "distritos": items(Distrito, "id", "nombre", filtro=Distrito.activo.is_(True), orden=Distrito.nombre),
        "categorias": items(Categoria, "id", "nombre", filtro=Categoria.activo.is_(True), orden=Categoria.nombre),
        "prioridades": items(Prioridad, "id", "nombre", "nivel", orden=Prioridad.nivel),
        "areas": items(Area, "id", "nombre", filtro=Area.activo.is_(True), orden=Area.nombre),
        "estados": items(EstadoIncidencia, "id", "nombre", orden=EstadoIncidencia.id),
        "roles": items(Rol, "id", "nombre", orden=Rol.id),
    }
