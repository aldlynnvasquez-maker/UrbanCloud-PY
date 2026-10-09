from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.configuracion.base import sesion_bd
from app.modelos.dominio import (
    AnalisisIA, Area, AsignacionIncidencia, Auditoria, Categoria,
    ConfiguracionSistema, EstadoIncidencia, Incidencia, Notificacion,
    Prioridad, Rol, SeguidorIncidencia, Usuario, ahora,
)
from app.repositorios.consultas import resumen
from app.seguridad.sesiones import rol_usuario, usuario_actual

router = APIRouter()


def _cuenta(db: Session, consulta) -> int:
    return db.scalar(select(func.count()).select_from(consulta.subquery())) or 0


@router.get("/panel/resumen")
def mostrar(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(sesion_bd)):
    rol = rol_usuario(db, usuario)
    estado = lambda nombres: select(Incidencia).join(EstadoIncidencia).where(
        EstadoIncidencia.nombre.in_(nombres))
    abiertas = select(Incidencia).join(EstadoIncidencia).where(EstadoIncidencia.nombre != "Cerrado")
    cerradas = _cuenta(db, estado(["Cerrado"]))
    if rol == "Ciudadano":
        propias = select(Incidencia).where(Incidencia.ciudadano_id == usuario.id)
        datos = {"total": _cuenta(db, propias),
                 "seguidas": _cuenta(db, select(SeguidorIncidencia).where(SeguidorIncidencia.ciudadano_id == usuario.id)),
                 "resueltas": _cuenta(db, propias.join(EstadoIncidencia).where(EstadoIncidencia.nombre == "Cerrado")),
                 "recientes": [resumen(db, item) for item in db.scalars(
                     propias.order_by(Incidencia.created_at.desc()).limit(5))]}
    elif rol == "Operador":
        configuracion = db.scalar(select(ConfiguracionSistema.valor).where(
            ConfiguracionSistema.clave == "UMBRAL_CONFIANZA_IA"))
        umbral = int(configuracion or 0)
        categorias = db.scalars(select(Categoria).order_by(Categoria.id)).all()
        datos = {"abiertas": _cuenta(db, abiertas),
                 "pendientes": _cuenta(db, estado(["En revisión", "Revisión solicitada"])),
                 "prioridad_alta": _cuenta(db, abiertas.join(Prioridad).where(Prioridad.nombre == "Alta")),
                 "cerradas": cerradas, "umbral_ia": umbral,
                 "confianza_baja": _cuenta(db, select(AnalisisIA).join(Incidencia).join(EstadoIncidencia)
                                            .where(AnalisisIA.confianza < umbral / 100,
                                                   EstadoIncidencia.nombre == "En revisión")),
                 "por_categoria": [{"nombre": item.nombre,
                                    "total": _cuenta(db, select(Incidencia).where(Incidencia.categoria_id == item.id))}
                                   for item in categorias]}
    elif rol == "Supervisor":
        areas = db.scalars(select(Area).order_by(Area.id)).all()
        tecnico = db.scalar(select(Rol.id).where(Rol.nombre == "Personal técnico"))
        asignada = select(AsignacionIncidencia.id).where(
            AsignacionIncidencia.incidencia_id == Incidencia.id,
            AsignacionIncidencia.activa.is_(True)).exists()
        datos = {"abiertas": _cuenta(db, abiertas),
                 "proximas_vencer": _cuenta(db, abiertas.where(
                     Incidencia.fecha_limite.between(ahora(), ahora() + timedelta(days=2)))),
                 "sin_responsable": _cuenta(db, abiertas.where(~asignada)),
                 "cerradas": cerradas,
                 "carga_por_area": [{"id": area.id, "nombre": area.nombre,
                                     "tecnicos_activos": _cuenta(db, select(Usuario).where(
                                         Usuario.area_id == area.id, Usuario.rol_id == tecnico,
                                         Usuario.activo.is_(True)))} for area in areas]}
    elif rol == "Personal técnico":
        asignaciones = select(AsignacionIncidencia).where(AsignacionIncidencia.tecnico_id == usuario.id)
        datos = {"activas": _cuenta(db, asignaciones.where(AsignacionIncidencia.activa.is_(True))),
                 "anteriores": _cuenta(db, asignaciones.where(AsignacionIncidencia.activa.is_(False))),
                 "impedidas": _cuenta(db, select(Incidencia).join(AsignacionIncidencia)
                                      .join(EstadoIncidencia).where(
                                          AsignacionIncidencia.tecnico_id == usuario.id,
                                          EstadoIncidencia.nombre == "Impedido").distinct())}
    elif rol == "Administrador":
        categorias = db.scalars(select(Categoria.nombre).where(Categoria.activo.is_(True))
                                 .order_by(Categoria.nombre)).all()
        umbral = db.scalar(select(ConfiguracionSistema.valor).where(
            ConfiguracionSistema.clave == "UMBRAL_CONFIANZA_IA"))
        datos = {"perfiles": _cuenta(db, select(Usuario)), "categorias": len(categorias),
                 "categorias_activas": categorias, "umbral_ia": umbral,
                 "auditorias": _cuenta(db, select(Auditoria))}
    else:
        raise HTTPException(403, "No tienes permiso para realizar esta acción.")
    datos["no_leidas"] = _cuenta(db, select(Notificacion).where(
        Notificacion.usuario_id == usuario.id, Notificacion.leida_en.is_(None)))
    return datos
