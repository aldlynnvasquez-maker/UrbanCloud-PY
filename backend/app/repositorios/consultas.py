"""Consultas y serialización compatibles con el cliente React actual."""

import math
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.modelos.dominio import (
    ActualizacionIncidencia, AnalisisIA, Area, AsignacionIncidencia, Categoria,
    Distrito, EstadoIncidencia, EvidenciaIncidencia, HistorialEstadoIncidencia,
    Incidencia, Prioridad,
)


def iso(valor: datetime | None) -> str | None:
    return valor.isoformat() if valor else None


def nombre(db: Session, modelo, identificador) -> str | None:
    objeto = db.get(modelo, identificador) if identificador is not None else None
    return objeto.nombre if objeto else None


def resumen(db: Session, incidencia: Incidencia) -> dict:
    return {"id": str(incidencia.id), "codigo": incidencia.codigo,
            "titulo": incidencia.titulo,
            "estado": nombre(db, EstadoIncidencia, incidencia.estado_id),
            "categoria": nombre(db, Categoria, incidencia.categoria_id),
            "prioridad": nombre(db, Prioridad, incidencia.prioridad_id),
            "area": nombre(db, Area, incidencia.area_id),
            "distrito": nombre(db, Distrito, incidencia.distrito_id),
            "direccion": incidencia.direccion, "fecha": iso(incidencia.created_at),
            "fecha_limite": iso(incidencia.fecha_limite)}


def detalle(db: Session, incidencia: Incidencia, base_url: str, ciudadano: bool = False) -> dict:
    datos = resumen(db, incidencia)
    datos.update(descripcion=incidencia.descripcion,
                 latitud=float(incidencia.latitud) if incidencia.latitud is not None else None,
                 longitud=float(incidencia.longitud) if incidencia.longitud is not None else None,
                 fecha_cierre=iso(incidencia.fecha_cierre))
    evidencias = db.scalars(select(EvidenciaIncidencia)
                            .where(EvidenciaIncidencia.incidencia_id == incidencia.id)
                            .order_by(EvidenciaIncidencia.created_at)).all()
    datos["evidencias"] = [
        {"id": str(item.id), "tipo": item.tipo,
         **({} if ciudadano else {"descripcion": item.descripcion, "fecha": iso(item.created_at),
                                "descarga": f"{base_url}incidencias/{incidencia.id}/evidencias/{item.id}"}),
         "vista": f"{base_url}incidencias/{incidencia.id}/evidencias/{item.id}/ver"}
        for item in evidencias]
    historia = db.scalars(select(HistorialEstadoIncidencia)
                          .where(HistorialEstadoIncidencia.incidencia_id == incidencia.id)
                          .order_by(HistorialEstadoIncidencia.created_at, HistorialEstadoIncidencia.id)).all()
    datos["historial"] = [
        {**({} if ciudadano else {"anterior": nombre(db, EstadoIncidencia, item.estado_anterior_id),
                                "comentario": item.comentario}),
         "nuevo": nombre(db, EstadoIncidencia, item.estado_nuevo_id), "fecha": iso(item.created_at)}
        for item in historia]
    avances = db.scalars(select(ActualizacionIncidencia)
                         .where(ActualizacionIncidencia.incidencia_id == incidencia.id)
                         .order_by(ActualizacionIncidencia.created_at)).all()
    if ciudadano:
        ultimo = avances[-1] if avances else None
        datos["ultimo_avance"] = (nombre(db, EstadoIncidencia, ultimo.estado_id) or "En camino") if ultimo else None
        return datos
    datos["fecha_limite"] = iso(incidencia.fecha_limite)
    datos["actualizaciones"] = [{"comentario": item.comentario, "fecha": iso(item.created_at)} for item in avances]
    asignaciones = db.scalars(select(AsignacionIncidencia)
                              .where(AsignacionIncidencia.incidencia_id == incidencia.id)
                              .order_by(AsignacionIncidencia.fecha_asignacion)).all()
    datos["asignaciones"] = [{"tecnico_id": item.tecnico_id,
                             "fecha_asignacion": iso(item.fecha_asignacion),
                             "fecha_fin": iso(item.fecha_fin), "activa": item.activa}
                            for item in asignaciones]
    analisis = db.scalars(select(AnalisisIA).where(AnalisisIA.incidencia_id == incidencia.id)
                          .order_by(AnalisisIA.created_at)).all()
    datos["analisis_ia"] = [{"categoria_sugerida": nombre(db, Categoria, item.categoria_sugerida_id),
                            "prioridad_sugerida": nombre(db, Prioridad, item.prioridad_sugerida_id),
                            "area_sugerida": nombre(db, Area, item.area_sugerida_id),
                            "confianza": float(item.confianza) if item.confianza is not None else None,
                            "fecha": iso(item.created_at)} for item in analisis]
    return datos


def pagina(db: Session, consulta: Select, numero: int = 1, transformar=None, por_pagina: int = 20) -> dict:
    numero = max(1, numero)
    total = db.scalar(select(func.count()).select_from(consulta.order_by(None).subquery())) or 0
    elementos = db.scalars(consulta.limit(por_pagina).offset((numero - 1) * por_pagina)).all()
    datos = [transformar(item) if transformar else item for item in elementos]
    return {"data": datos, "current_page": numero,
            "last_page": max(1, math.ceil(total / por_pagina)), "per_page": por_pagina,
            "total": total, "from": (numero - 1) * por_pagina + 1 if total else None,
            "to": min(numero * por_pagina, total) if total else None}
