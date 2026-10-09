"""Cliente real de clasificación y normalización del contrato externo."""

import base64
import re

import httpx

from app.configuracion.ajustes import ajustes


class ErrorIntegracionIA(Exception):
    pass


_categorias = {"ILUMINACION": "Iluminación", "LIMPIEZA": "Limpieza",
               "VIAS_Y_PISTAS": "Vías y pistas", "PARQUES": "Parques",
               "SERVICIOS": "Servicios", "OTRO": "Otro"}
_prioridades = {"BAJA": "Baja", "MEDIA": "Media", "ALTA": "Alta"}
_areas = {"ALUMBRADO_PUBLICO": "Alumbrado público", "MANTENIMIENTO": "Mantenimiento",
          "SERVICIOS_AMBIENTALES": "Servicios ambientales", "AREAS_VERDES": "Áreas verdes",
          "VIAS_Y_OBRAS": "Vías y obras"}


def normalizar(respuesta: object) -> dict:
    if not isinstance(respuesta, dict) or "error" in respuesta:
        raise ErrorIntegracionIA
    if respuesta.get("valido") is False:
        motivo = respuesta.get("motivo")
        if not isinstance(motivo, str) or not motivo.strip():
            raise ErrorIntegracionIA
        motivo = re.sub(r"[\x00-\x1f\x7f]", " ", re.sub(r"<[^>]*>", "", motivo)).strip()[:500]
        if not motivo:
            raise ErrorIntegracionIA
        return {"valido": False, "motivo": motivo}
    if respuesta.get("valido") is not True:
        raise ErrorIntegracionIA
    try:
        confianza = respuesta["confianza"]
        if isinstance(confianza, bool) or not isinstance(confianza, (int, float)) or not 0 <= confianza <= 1:
            raise ValueError
        return {"valido": True, "categoria": _categorias[respuesta["categoria"]],
                "prioridad": _prioridades[respuesta["prioridad"]],
                "areaResponsable": _areas[respuesta["areaResponsable"]],
                "confianza": float(confianza)}
    except (KeyError, TypeError, ValueError):
        raise ErrorIntegracionIA from None


def analizar(imagen: bytes, titulo: str, descripcion: str) -> dict:
    config = ajustes()
    if not config.analisis_ia_url.startswith("https://"):
        raise ErrorIntegracionIA
    cuerpo = {"imagen": base64.b64encode(imagen).decode("ascii"),
              "titulo": titulo, "descripcion": descripcion}
    for intento in range(config.analisis_ia_reintentos + 1):
        try:
            with httpx.Client(timeout=config.analisis_ia_timeout, follow_redirects=False) as cliente:
                respuesta = cliente.post(config.analisis_ia_url, json=cuerpo,
                                        headers={"Accept": "application/json"})
        except httpx.RequestError:
            if intento >= config.analisis_ia_reintentos:
                raise ErrorIntegracionIA from None
            continue
        if respuesta.status_code == 429 or respuesta.status_code >= 500:
            if intento < config.analisis_ia_reintentos:
                continue
        if not 200 <= respuesta.status_code < 300:
            raise ErrorIntegracionIA
        try:
            return normalizar(respuesta.json())
        except (ValueError, ErrorIntegracionIA):
            raise ErrorIntegracionIA from None
    raise ErrorIntegracionIA
