"""Alta de reportes con IA real, imagen privada y transacción atómica."""

import io
import uuid
from datetime import timedelta

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modelos.dominio import (
    AnalisisIA, Area, Categoria, Distrito, EstadoIncidencia, EvidenciaIncidencia,
    HistorialEstadoIncidencia, Incidencia, Prioridad, Usuario, ValidacionReporte,
    ahora,
)
from app.servicios.almacenamiento import almacenamiento
from app.servicios.ia import ErrorIntegracionIA, analizar
from app.servicios.notificaciones import notificar_evento

LIMITE_IMAGEN = 3 * 1024 * 1024
PLAZOS_HORAS = {"Alta": 24, "Media": 72, "Baja": 168}


def validar_imagen(contenido: bytes, mime: str, *, webp: bool = False,
                   limite: int = LIMITE_IMAGEN) -> str:
    aceptados = {"JPEG": "image/jpeg", "PNG": "image/png"}
    if webp:
        aceptados["WEBP"] = "image/webp"
    if not contenido or len(contenido) > limite or mime not in aceptados.values():
        raise HTTPException(422, "La fotografía no tiene un formato o tamaño permitido.")
    try:
        with Image.open(io.BytesIO(contenido)) as imagen:
            formato = imagen.format
            imagen.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(422, "La fotografía no es una imagen válida.") from None
    if aceptados.get(formato) != mime:
        raise HTTPException(422, "El tipo de imagen no coincide con el archivo.")
    return {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[formato]


def _codigo_siguiente(db: Session) -> str:
    anio = ahora().year
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:anio)"), {"anio": anio})
        ultimo = db.scalar(text("SELECT COALESCE(MAX(CAST(SUBSTRING(codigo FROM 10) AS INTEGER)), 0) "
                                "FROM incidencias WHERE codigo LIKE :prefijo"),
                           {"prefijo": f"URB-{anio}-%"})
    else:
        codigos = db.scalars(select(Incidencia.codigo).where(Incidencia.codigo.like(f"URB-{anio}-%"))).all()
        ultimo = max((int(c.split("-")[-1]) for c in codigos), default=0)
    return f"URB-{anio}-{ultimo + 1:04d}"


def crear_reporte(db: Session, ciudadano: Usuario, datos: dict, foto: bytes, mime: str,
                  analizar_ia=None) -> tuple[dict, int]:
    analizar_ia = analizar_ia or analizar
    extension = validar_imagen(foto, mime)
    distrito = db.get(Distrito, datos["distrito_id"])
    if distrito is None or not distrito.activo:
        raise HTTPException(422, "Selecciona un distrito válido.")
    ruta = f"reportes/{ahora():%Y/%m}/{uuid.uuid4()}.{extension}"
    disco = almacenamiento()
    disco.guardar(ruta, foto, mime)
    try:
        respuesta = analizar_ia(foto, datos["titulo"], datos["descripcion"])
        if not respuesta["valido"]:
            db.add(ValidacionReporte(ciudadano_id=ciudadano.id, incidencia_id=None,
                                     titulo=datos["titulo"], descripcion=datos["descripcion"],
                                     ruta_imagen=ruta, es_valido=False,
                                     motivo=respuesta["motivo"], respuesta_modelo=respuesta))
            db.commit()
            return {"aceptado": False, "mensaje": respuesta["motivo"]}, 422

        categoria = db.scalar(select(Categoria).where(Categoria.nombre == respuesta["categoria"],
                                                     Categoria.activo.is_(True)))
        prioridad = db.scalar(select(Prioridad).where(Prioridad.nombre == respuesta["prioridad"]))
        area = db.scalar(select(Area).where(Area.nombre == respuesta["areaResponsable"], Area.activo.is_(True)))
        estado = db.scalar(select(EstadoIncidencia).where(EstadoIncidencia.nombre == "En revisión"))
        if not all((categoria, prioridad, area, estado)):
            raise ErrorIntegracionIA
        incidencia = Incidencia(
            codigo=_codigo_siguiente(db), ciudadano_id=ciudadano.id,
            titulo=datos["titulo"], descripcion=datos["descripcion"],
            categoria_id=categoria.id, prioridad_id=prioridad.id, area_id=area.id,
            estado_id=estado.id, distrito_id=distrito.id, direccion=datos["direccion"],
            latitud=datos.get("latitud"), longitud=datos.get("longitud"),
            fecha_limite=ahora() + timedelta(hours=PLAZOS_HORAS[prioridad.nombre]),
        )
        db.add(incidencia)
        db.flush()
        db.add_all([
            ValidacionReporte(ciudadano_id=ciudadano.id, incidencia_id=incidencia.id,
                              titulo=datos["titulo"], descripcion=datos["descripcion"],
                              ruta_imagen=ruta, es_valido=True, confianza=respuesta["confianza"],
                              respuesta_modelo=respuesta),
            AnalisisIA(incidencia_id=incidencia.id, categoria_sugerida_id=categoria.id,
                       prioridad_sugerida_id=prioridad.id, area_sugerida_id=area.id,
                       confianza=respuesta["confianza"], respuesta_modelo=respuesta),
            EvidenciaIncidencia(incidencia_id=incidencia.id, usuario_id=ciudadano.id,
                                tipo="REPORTE", ruta_archivo=ruta),
            HistorialEstadoIncidencia(incidencia_id=incidencia.id, estado_nuevo_id=estado.id,
                                      cambiado_por=ciudadano.id,
                                      comentario="Reporte recibido y validado inicialmente."),
        ])
        notificar_evento(db, incidencia, "En revisión")
        db.commit()
        return {"aceptado": True, "id": str(incidencia.id),
                "codigo": incidencia.codigo, "estado": "En revisión"}, 201
    except Exception:
        db.rollback()
        disco.eliminar(ruta)
        raise
