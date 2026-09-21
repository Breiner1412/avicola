"""Inicio y cierre de sesion, eleccion de finca y contrasenas."""

from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.core import limites
from app.core.auditoria import registrar
from app.core.config import config
from app.core.contexto import Contexto, contexto_actual, fincas_del_usuario, ip_de
from app.core.correo import enviar
from app.core.db import obtener_db
from app.core.errores import ErrorApi, datos_invalidos, sin_permiso, sin_sesion
from app.core.seguridad import cifrar_clave, codigo_numerico, huella, verificar_clave
from app.esquemas.auth import (
    CambiarClave,
    ElegirFinca,
    LoginEntrada,
    PedirCodigo,
    RestablecerClave,
    SesionSalida,
)
from app.esquemas.comunes import Mensaje
from app.modelos.acceso import RecuperacionClave, Sesion, Usuario
from app.servicios.sesion import (
    abrir_sesion,
    ahora_simple,
    armar_respuesta,
    borrar_cookie,
    buscar_sesion,
    cargar_usuario,
    cerrar_sesion,
    guardar_cookie,
)

router = APIRouter(prefix="/auth", tags=["Sesion"])

MINUTOS_CODIGO = 15
MAX_INTENTOS_CODIGO = 5


def _credenciales_malas() -> ErrorApi:
    return ErrorApi(status.HTTP_401_UNAUTHORIZED, "credenciales", "El correo o la contrasena no coinciden")


@router.post("/login", response_model=SesionSalida, summary="Iniciar sesion")
def login(
    datos: LoginEntrada,
    peticion: Request,
    respuesta: Response,
    db: Session = Depends(obtener_db),
):
    ip = ip_de(peticion) or "desconocida"
    limites.login_ip.registrar(ip)
    limites.login_email.registrar(datos.email)

    usuario = db.scalars(
        select(Usuario)
        .options(joinedload(Usuario.rol), joinedload(Usuario.cuenta))
        .where(Usuario.email == datos.email.lower())
    ).first()

    if usuario is None or not verificar_clave(datos.clave, usuario.clave_hash):
        registrar(
            db, None, "ingreso_fallido", "usuarios",
            entidad_id=usuario.id if usuario else None,
            descripcion=f"Intento fallido con {datos.email}",
            cuenta_id=usuario.cuenta_id if usuario else None,
            usuario_id=usuario.id if usuario else None,
            ip=ip,
        )
        db.commit()
        raise _credenciales_malas()

    if not usuario.activo:
        raise sin_permiso("Tu usuario esta inactivo. Habla con el administrador.")
    if usuario.cuenta is not None and not usuario.cuenta.activo:
        raise sin_permiso("La cuenta esta inactiva. Habla con el administrador.")

    fincas = fincas_del_usuario(db, usuario)
    if not fincas and usuario.rol.clave != "plataforma":
        raise sin_permiso("Todavia no tienes fincas asignadas. Habla con el administrador.")

    permitidas = {f.id for f, _ in fincas}
    if datos.finca_id is not None:
        if datos.finca_id not in permitidas:
            raise sin_permiso("No tienes acceso a esa finca")
        finca_id = datos.finca_id
    elif len(fincas) == 1:
        finca_id = fincas[0][0].id
    else:
        finca_id = None  # el usuario elige en la siguiente pantalla

    sesion, refresco = abrir_sesion(db, usuario, finca_id, ip, peticion.headers.get("user-agent"))
    usuario.ultimo_ingreso = ahora_simple()
    limites.login_email.limpiar(datos.email)

    registrar(
        db, None, "ingreso", "usuarios", usuario.id,
        descripcion=f"Inicio de sesion de {usuario.email}",
        cuenta_id=usuario.cuenta_id, finca_id=finca_id, usuario_id=usuario.id,
        usuario_nombre=usuario.nombre_completo, ip=ip,
    )

    salida = armar_respuesta(db, usuario, sesion)
    db.commit()
    guardar_cookie(respuesta, refresco)
    return salida


@router.post("/finca", response_model=SesionSalida, summary="Elegir la finca de trabajo")
def elegir_finca(
    datos: ElegirFinca,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(contexto_actual),
):
    usuario = cargar_usuario(db, ctx.usuario.id)
    if usuario is None:
        raise sin_sesion()

    if datos.finca_id not in {f.id for f, _ in fincas_del_usuario(db, usuario)}:
        raise sin_permiso("No tienes acceso a esa finca")

    if ctx.sesion_id is None:
        raise sin_sesion()
    sesion = db.get(Sesion, ctx.sesion_id)
    if sesion is None or sesion.revocada_en is not None:
        raise sin_sesion()

    sesion.finca_id = datos.finca_id
    registrar(db, ctx, "cambio_finca", "sesiones", sesion.id, descripcion=f"Finca activa {datos.finca_id}", finca_id=datos.finca_id)
    salida = armar_respuesta(db, usuario, sesion)
    db.commit()
    return salida


@router.post("/refrescar", response_model=SesionSalida, summary="Renovar el token de acceso")
def refrescar(
    respuesta: Response,
    db: Session = Depends(obtener_db),
    avicola_refresco: str | None = Cookie(default=None, alias=config.cookie_refresco),
):
    if not avicola_refresco:
        raise sin_sesion("No hay sesion abierta")

    sesion = buscar_sesion(db, avicola_refresco)
    if sesion is None:
        raise sin_sesion("La sesion expiro. Vuelve a entrar.")

    usuario = cargar_usuario(db, sesion.usuario_id)
    if usuario is None or not usuario.activo:
        raise sin_sesion("El usuario no esta disponible")

    salida = armar_respuesta(db, usuario, sesion)
    db.commit()
    return salida


@router.post("/salir", response_model=Mensaje, summary="Cerrar sesion")
def salir(
    respuesta: Response,
    db: Session = Depends(obtener_db),
    avicola_refresco: str | None = Cookie(default=None, alias=config.cookie_refresco),
):
    if avicola_refresco:
        sesion = buscar_sesion(db, avicola_refresco)
        if sesion is not None:
            cerrar_sesion(db, sesion)
            registrar(
                db, None, "salida", "sesiones", sesion.id,
                descripcion="Cierre de sesion", usuario_id=sesion.usuario_id, finca_id=sesion.finca_id,
            )
            db.commit()
    borrar_cookie(respuesta)
    return Mensaje(mensaje="Sesion cerrada")


@router.get("/yo", response_model=SesionSalida, summary="Datos de la sesion actual")
def yo(db: Session = Depends(obtener_db), ctx: Contexto = Depends(contexto_actual)):
    usuario = cargar_usuario(db, ctx.usuario.id)
    if usuario is None or ctx.sesion_id is None:
        raise sin_sesion()

    sesion = db.get(Sesion, ctx.sesion_id)
    if sesion is None:
        raise sin_sesion()
    return armar_respuesta(db, usuario, sesion)


@router.post("/cambiar-clave", response_model=Mensaje, summary="Cambiar mi contrasena")
def cambiar_clave(
    datos: CambiarClave,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(contexto_actual),
):
    usuario = db.get(Usuario, ctx.usuario.id)
    if usuario is None or not verificar_clave(datos.clave_actual, usuario.clave_hash):
        raise datos_invalidos("La contrasena actual no coincide")
    if datos.clave_actual == datos.clave_nueva:
        raise datos_invalidos("La contrasena nueva debe ser distinta")

    usuario.clave_hash = cifrar_clave(datos.clave_nueva)
    usuario.debe_cambiar_clave = False
    registrar(db, ctx, "cambio_clave", "usuarios", usuario.id, descripcion="Cambio de contrasena")
    db.commit()
    return Mensaje(mensaje="Contrasena actualizada")


@router.post("/recuperar", response_model=Mensaje, summary="Pedir un codigo de recuperacion")
def recuperar(datos: PedirCodigo, peticion: Request, db: Session = Depends(obtener_db)):
    ip = ip_de(peticion) or "desconocida"
    limites.recuperar_ip.registrar(ip)
    limites.recuperar_email.registrar(datos.email)

    usuario = db.scalars(select(Usuario).where(Usuario.email == datos.email.lower())).first()
    if usuario is not None and usuario.activo:
        codigo = codigo_numerico()
        db.add(
            RecuperacionClave(
                usuario_id=usuario.id,
                codigo_hash=huella(codigo),
                expira_en=ahora_simple() + timedelta(minutes=MINUTOS_CODIGO),
                creado_en=ahora_simple(),
            )
        )
        registrar(db, None, "solicitud_clave", "usuarios", usuario.id, descripcion="Pidio codigo de recuperacion", usuario_id=usuario.id, ip=ip)
        db.commit()
        enviar(
            usuario.email,
            "Codigo para recuperar tu contrasena de Avícola",
            f"Tu codigo es {codigo}. Vence en {MINUTOS_CODIGO} minutos.\n"
            "Si no lo pediste, ignora este mensaje.",
        )

    # La respuesta es la misma exista o no el correo.
    return Mensaje(mensaje="Si el correo esta registrado, te enviamos un codigo")


@router.post("/restablecer", response_model=Mensaje, summary="Cambiar la contrasena con el codigo")
def restablecer(datos: RestablecerClave, peticion: Request, db: Session = Depends(obtener_db)):
    ip = ip_de(peticion) or "desconocida"
    limites.restablecer.registrar(ip)

    usuario = db.scalars(select(Usuario).where(Usuario.email == datos.email.lower())).first()
    if usuario is None:
        raise datos_invalidos("El codigo no es valido o ya vencio")

    solicitud = db.scalars(
        select(RecuperacionClave)
        .where(
            RecuperacionClave.usuario_id == usuario.id,
            RecuperacionClave.usado_en.is_(None),
            RecuperacionClave.expira_en > ahora_simple(),
        )
        .order_by(RecuperacionClave.id.desc())
    ).first()

    if solicitud is None:
        raise datos_invalidos("El codigo no es valido o ya vencio")

    if solicitud.codigo_hash != huella(datos.codigo):
        solicitud.intentos += 1
        if solicitud.intentos >= MAX_INTENTOS_CODIGO:
            solicitud.usado_en = ahora_simple()
        db.commit()
        raise datos_invalidos("El codigo no es valido o ya vencio")

    usuario.clave_hash = cifrar_clave(datos.clave_nueva)
    usuario.debe_cambiar_clave = False
    solicitud.usado_en = ahora_simple()

    # Se cierran todas las sesiones abiertas de ese usuario.
    db.execute(
        update(Sesion)
        .where(Sesion.usuario_id == usuario.id, Sesion.revocada_en.is_(None))
        .values(revocada_en=ahora_simple())
    )

    registrar(db, None, "restablecio_clave", "usuarios", usuario.id, descripcion="Cambio de contrasena con codigo", usuario_id=usuario.id, ip=ip)
    db.commit()
    return Mensaje(mensaje="Contrasena actualizada. Ya puedes entrar.")
