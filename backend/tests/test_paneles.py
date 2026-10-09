from tests.conftest import login


def test_panel_y_catalogos_por_cada_rol(entorno):
    cliente, _, _ = entorno
    for correo, rol in [
        ("admin@urbancloudai.com", "Administrador"),
        ("operador@urbancloudai.com", "Operador"),
        ("supervisor@urbancloudai.com", "Supervisor"),
        ("tecnico@urbancloudai.com", "Personal técnico"),
    ]:
        cabeceras = login(cliente, correo)
        assert cliente.get("/dashboard").json()["usuario"]["rol"] == rol
        assert cliente.get("/panel/resumen").status_code == 200
        assert cliente.get("/catalogos").status_code == 200
        assert cliente.post("/logout", headers=cabeceras).status_code == 200
