"""Usuarios de la cuenta y su asignacion a fincas."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import conflicto, datos_invalidos, no_encontrado, sin_permiso
from app.core.seguridad import cifrar_clave
from app.esquemas.comunes import Mensaje
from app.esquemas.usuarios import (
    ClaveNueva,
    FincaAsignada,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioSalida,
)
from app.modelos.acceso import Rol, Sesion, Usuario, UsuarioFinca
from app.modelos.organizacion import Finca
from app.servicios.alcance import cuenta_objetivo
from app.servicios.sesion import ahora_simple

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def _salida(usuario: Usuario) -> UsuarioSalida:
    return UsuarioSalida(
        id=usuario.id,
        cuenta_id=usuario.cuenta_id,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        email=usuario.email,
        documento=usuario.documento,
        telefono=usuario.telefono,
        rol=usuario.rol.clave,
        rol_nombre=usuario.rol.nombre,
        activo=usuario.activo,
        debe_cambiar_clave=usuario.debe_cambiar_clave,
        ultimo_ingreso=usuario.ultimo_ingreso,
        fincas=[FincaAsignada(finca_id=f.finca_id, solo_lectura=f.solo_lectura) for f in usuario.fincas],
    )


def _rol_por_clave(db: Session, ctx: Contexto, clave: str) -> Rol:
    rol = db.scalars(select(Rol).where(Rol.clave == clave)).first()
    if rol is None:
        raise datos_invalidos(f"El rol {clave} no existe")
    if rol.de_plataforma and not ctx.es_plataforma:
        raise sin_permiso("No puedes asignar ese rol")
    if not ctx.es_plataforma and rol.nivel < ctx.usuario.rol.nivel:
        raise sin_permiso("No puedes crear usuarios con mas permisos que los tuyos")
    return rol


def _usuario_de_la_cuenta(db: Session, ctx: Contexto, usuario_id: int) -> Usuario:
    usuario = db.scalars(
        select(Usuario).options(joinedload(Usuario.rol)).where(Usuario.id == usuario_id)
    ).first()
    if usuario is None:
        raise no_encontrado("El usuario no existe")
    if not ctx.es_plataforma and usuario.cuenta_id != ctx.cuenta_id:
        raise no_encontrado("El usuario no existe")
    if not ctx.es_plataforma and usuario.rol.nivel < ctx.usuario.rol.nivel:
        raise sin_permiso("No puedes administrar a ese usuario")
    return usuario


def _guardar_fincas(db: Session, usuario: Usuario, cuenta_id: int | None, asignaciones: list[FincaAsignada]) -> None:
    ids = [a.finca_id for a in asignaciones]
    if ids:
        validas = set(
            db.scalars(select(Finca.id).where(Finca.id.in_(ids), Finca.cuenta_id == cuenta_id)).all()
        )
        faltantes = set(ids) - validas
        if faltantes:
            raise datos_invalidos(f"Estas fincas no son de la cuenta: {sorted(faltantes)}")

    usuario.fincas.clear()
    db.flush()
    for asignacion in asignaciones:
        usuario.fincas.append(
            UsuarioFinca(finca_id=asignacion.finca_id, solo_lectura=asignacion.solo_lectura)
        )


@router.get("", response_model=list[UsuarioSalida], summary="Usuarios de la cuenta")
def listar(
    cuenta_id: int | None = Query(None, description="Solo para el rol de plataforma"),
    incluir_inactivos: bool = Query(True),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("usuarios", "ver")),
):
    consulta = select(Usuario).options(joinedload(Usuario.rol))
    if ctx.es_plataforma:
        if cuenta_id is not None:
            consulta = consulta.where(Usuario.cuenta_id == cuenta_id)
    else:
        consulta = consulta.where(Usuario.cuenta_id == ctx.cuenta_id)
    if not incluir_inactivos:
        consulta = consulta.where(Usuario.activo.is_(True))

    usuarios = db.scalars(consulta.order_by(Usuario.nombres, Usuario.apellidos)).unique().all()
    return [_salida(u) for u in usuarios]


@router.post("", response_model=UsuarioSalida, status_code=201, summary="Crear usuario")
def crear(
    datos: UsuarioCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("usuarios", "crear")),
):
    rol = _rol_por_clave(db, ctx, datos.rol)
    cuenta_id = None if rol.de_plataforma else cuenta_objetivo(ctx, datos.cuenta_id)
    email = datos.email.lower()

    if db.scalars(select(Usuario.id).where(Usuario.email == email)).first():
        raise conflicto("Ya hay un usuario con ese correo")

    usuario = Usuario(
        cuenta_id=cuenta_id,
        rol_id=rol.id,
        nombres=datos.nombres,
        apellidos=datos.apellidos,
        email=email,
        documento=datos.documento,
        telefono=datos.telefono,
        clave_hash=cifrar_clave(datos.clave),
        debe_cambiar_clave=datos.debe_cambiar_clave,
    )
    db.add(usuario)
    db.flush()
    _guardar_fincas(db, usuario, cuenta_id, datos.fincas)

    registrar(
        db, ctx, "crear", "usuarios", usuario.id,
        f"Creo el usuario {usuario.email} con rol {rol.clave}",
        datos.model_dump(exclude={"clave"}),
    )
    db.commit()
    db.refresh(usuario)
    return _salida(usuario)


@router.get("/{usuario_id}", response_model=UsuarioSalida, summary="Ver un usuario")
def ver(usuario_id: int, db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("usuarios", "ver"))):
    return _salida(_usuario_de_la_cuenta(db, ctx, usuario_id))


@router.patch("/{usuario_id}", response_model=UsuarioSalida, summary="Editar usuario")
def editar(
    usuario_id: int,
    datos: UsuarioActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("usuarios", "editar")),
):
    usuario = _usuario_de_la_cuenta(db, ctx, usuario_id)
    cambios = datos.model_dump(exclude_unset=True)

    if "email" in cambios and cambios["email"]:
        nuevo = cambios["email"].lower()
        if db.scalars(select(Usuario.id).where(Usuario.email == nuevo, Usuario.id != usuario.id)).first():
            raise conflicto("Ya hay un usuario con ese correo")
        usuario.email = nuevo

    if "rol" in cambios and cambios["rol"]:
        usuario.rol_id = _rol_por_clave(db, ctx, cambios["rol"]).id

    if "activo" in cambios and cambios["activo"] is not None:
        if usuario.id == ctx.usuario.id and not cambios["activo"]:
            raise datos_invalidos("No puedes desactivar tu propio usuario")
        usuario.activo = cambios["activo"]

    for campo in ("nombres", "apellidos", "documento", "telefono"):
        if campo in cambios:
            setattr(usuario, campo, cambios[campo])

    if datos.fincas is not None:
        _guardar_fincas(db, usuario, usuario.cuenta_id, datos.fincas)

    registrar(db, ctx, "editar", "usuarios", usuario.id, f"Edito el usuario {usuario.email}", cambios)
    db.commit()
    db.refresh(usuario)
    return _salida(usuario)


@router.post("/{usuario_id}/clave", response_model=Mensaje, summary="Asignar una contrasena nueva")
def cambiar_clave(
    usuario_id: int,
    datos: ClaveNueva,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("usuarios", "editar")),
):
    usuario = _usuario_de_la_cuenta(db, ctx, usuario_id)
    usuario.clave_hash = cifrar_clave(datos.clave)
    usuario.debe_cambiar_clave = datos.debe_cambiar_clave

    # Al cambiarle la contrasena se cierran sus sesiones abiertas.
    db.execute(
        update(Sesion)
        .where(Sesion.usuario_id == usuario.id, Sesion.revocada_en.is_(None))
        .values(revocada_en=ahora_simple())
    )
    registrar(db, ctx, "cambio_clave", "usuarios", usuario.id, f"Asigno contrasena nueva a {usuario.email}")
    db.commit()
    return Mensaje(mensaje="Contrasena actualizada")


@router.delete("/{usuario_id}", response_model=Mensaje, summary="Desactivar usuario")
def desactivar(
    usuario_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("usuarios", "borrar")),
):
    usuario = _usuario_de_la_cuenta(db, ctx, usuario_id)
    if usuario.id == ctx.usuario.id:
        raise datos_invalidos("No puedes desactivar tu propio usuario")
    usuario.activo = False
    registrar(db, ctx, "desactivar", "usuarios", usuario.id, f"Desactivo el usuario {usuario.email}")
    db.commit()
    return Mensaje(mensaje="Usuario desactivado")
