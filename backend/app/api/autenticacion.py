import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.configuracion.base import sesion_bd
from app.modelos.dominio import Rol, Usuario
from app.seguridad.sesiones import (
    cerrar_sesion, hash_clave, iniciar_sesion, renovar_sesion, resumen_usuario,
    usuario_actual, verificar_clave,
)

router = APIRouter()
DOMINIO = re.compile(r"^[A-Za-z0-9_+\-]+(?:\.[A-Za-z0-9_+\-]+)*@urbancloudai\.com$", re.I)
DESTINOS = {"Ciudadano": "/ciudadano", "Operador": "/operador", "Supervisor": "/supervisor",
            "Personal técnico": "/tecnico", "Administrador": "/administrador"}


class Registro(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    email: str = Field(max_length=255)
    password: str = Field(min_length=8)
    password_confirmation: str


class Credenciales(BaseModel):
    email: str
    password: str


@router.get("/login")
def login_requerido():
    raise HTTPException(401, "Debe iniciar sesión.")


def _sesion_activa(request: Request, db: Session) -> bool:
    try:
        usuario_actual(request, db)
        return True
    except HTTPException:
        return False


@router.post("/registro", status_code=201)
def registrar(datos: Registro, request: Request, db: Session = Depends(sesion_bd)):
    if _sesion_activa(request, db):
        raise HTTPException(409, "Cierre la sesión antes de registrar otra cuenta.")
    correo = datos.email.strip().lower()
    if not DOMINIO.fullmatch(correo):
        raise HTTPException(422, "Usa un correo válido de @urbancloudai.com.")
    if datos.password != datos.password_confirmation:
        raise HTTPException(422, "Las contraseñas no coinciden.")
    rol = db.scalar(select(Rol).where(Rol.nombre == "Ciudadano"))
    if rol is None:
        raise HTTPException(503, "No está disponible el registro en este momento.")
    usuario = Usuario(nombre=datos.nombre.strip(), email=correo,
                      password=hash_clave(datos.password), rol_id=rol.id, activo=True)
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(422, "Este correo ya está registrado.") from None
    return {"mensaje": "Cuenta ciudadana creada.", "usuario": resumen_usuario(db, usuario)}


@router.post("/login")
def login(datos: Credenciales, request: Request, respuesta: Response, db: Session = Depends(sesion_bd)):
    if _sesion_activa(request, db):
        raise HTTPException(409, "Ya existe una sesión activa.")
    usuario = db.scalar(select(Usuario).where(Usuario.email == datos.email.strip().lower()))
    if usuario is None or not usuario.activo or not verificar_clave(datos.password, usuario.password):
        raise HTTPException(422, "Las credenciales no son válidas o la cuenta está inactiva.")
    iniciar_sesion(respuesta, db, usuario)
    db.commit()
    rol = resumen_usuario(db, usuario)
    return {"mensaje": "Sesión iniciada.", "usuario": rol, "destino": DESTINOS.get(rol["rol"])}


@router.post("/auth/refresh")
def refresh(request: Request, respuesta: Response, db: Session = Depends(sesion_bd)):
    renovar_sesion(respuesta, db, request.cookies.get("uc_refresh"))
    return {"mensaje": "Sesión renovada."}


@router.post("/logout")
def logout(request: Request, respuesta: Response, db: Session = Depends(sesion_bd)):
    cerrar_sesion(respuesta, db, request.cookies.get("uc_refresh"))
    return {"mensaje": "Sesión cerrada."}


@router.get("/dashboard")
def dashboard(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(sesion_bd)):
    datos = resumen_usuario(db, usuario)
    return {"usuario": datos, "destino": DESTINOS.get(datos["rol"])}


@router.get("/dashboard/{panel}")
def panel_rol(panel: str, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(sesion_bd)):
    ruta = {"ciudadano": "Ciudadano", "operador": "Operador", "supervisor": "Supervisor",
            "tecnico": "Personal técnico", "administrador": "Administrador"}
    rol = resumen_usuario(db, usuario)["rol"]
    if ruta.get(panel) != rol:
        raise HTTPException(403, "No tienes permiso para realizar esta acción.")
    return {"mensaje": "Acceso autorizado.", "rol": rol}
