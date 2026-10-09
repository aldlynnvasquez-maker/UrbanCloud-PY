import base64

import pytest

from app.servicios.ia import ErrorIntegracionIA, analizar, normalizar


def test_mapeo_ia_real_y_errores():
    respuesta = {"valido": True, "categoria": "ILUMINACION", "prioridad": "MEDIA",
                 "areaResponsable": "ALUMBRADO_PUBLICO", "confianza": 0.92}
    normalizada = normalizar(respuesta)
    assert normalizada["categoria"] == "Iluminación"
    assert normalizada["areaResponsable"] == "Alumbrado público"
    with pytest.raises(ErrorIntegracionIA):
        normalizar({**respuesta, "categoria": "DESCONOCIDA"})
    with pytest.raises(ErrorIntegracionIA):
        normalizar({"valido": False})
    assert normalizar({"valido": False, "motivo": "<b>No válido</b>"})["motivo"] == "No válido"


def test_peticion_ia_usa_base64_puro_sin_red(entorno, monkeypatch):
    recibido = {}

    class Respuesta:
        status_code = 200

        def json(self):
            return {"valido": True, "categoria": "ILUMINACION", "prioridad": "MEDIA",
                    "areaResponsable": "ALUMBRADO_PUBLICO", "confianza": 0.92}

    class Cliente:
        def __init__(self, **_):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, url, json, headers):
            recibido.update(json)
            return Respuesta()

    monkeypatch.setattr("app.servicios.ia.httpx.Client", Cliente)
    assert analizar(b"imagen", "Poste", "Apagado")["valido"] is True
    assert recibido["imagen"] == base64.b64encode(b"imagen").decode("ascii")
    assert not recibido["imagen"].startswith("data:")
