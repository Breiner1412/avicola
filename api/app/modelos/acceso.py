"""Usuarios, roles, permisos, asignacion a fincas y sesiones."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modelos.base import Base, Marcas
from app.modelos.organizacion import Cuenta, Finca


class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    # Nivel: 0 plataforma, 1 propietario, 2 administrador, 3 supervisor, 4 operativo
    nivel: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    # Los roles de plataforma no se pueden asignar desde una cuenta
    de_plataforma: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permisos: Mapped[list["Permiso"]] = relationship(back_populates="rol", cascade="all, delete-orphan")


class Modulo(Base):
    __tablename__ = "modulos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    grupo: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    permisos: Mapped[list["Permiso"]] = relationship(back_populates="modulo", cascade="all, delete-orphan")


class Permiso(Base):
    __tablename__ = "permisos"

    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id", ondelete="CASCADE"), primary_key=True)
    ver: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    crear: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    editar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    borrar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    rol: Mapped["Rol"] = relationship(back_populates="permisos")
    modulo: Mapped["Modulo"] = relationship(back_populates="permisos")


class Usuario(Base, Marcas):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Los usuarios de plataforma no pertenecen a ninguna cuenta
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), index=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False, index=True)
    nombres: Mapped[str] = mapped_column(String(80), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    documento: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(30))
    clave_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    debe_cambiar_clave: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ultimo_ingreso: Mapped[datetime | None] = mapped_column(DateTime)

    cuenta: Mapped[Cuenta | None] = relationship(back_populates="usuarios")
    rol: Mapped["Rol"] = relationship()
    fincas: Mapped[list["UsuarioFinca"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}".strip()


class UsuarioFinca(Base):
    """Fincas en las que trabaja o supervisa un usuario."""

    __tablename__ = "usuario_fincas"
    __table_args__ = (UniqueConstraint("usuario_id", "finca_id", name="uq_usuario_finca"),)

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    finca_id: Mapped[int] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), primary_key=True)
    # El supervisor puede ver de solo lectura otras fincas de la misma cuenta
    solo_lectura: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="fincas")
    finca: Mapped[Finca] = relationship()


class Sesion(Base):
    """Cada inicio de sesion con su token de refresco."""

    __tablename__ = "sesiones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    huella: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    finca_id: Mapped[int | None] = mapped_column(ForeignKey("fincas.id", ondelete="SET NULL"))
    ip: Mapped[str | None] = mapped_column(String(45))
    agente: Mapped[str | None] = mapped_column(String(255))
    expira_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revocada_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    usuario: Mapped["Usuario"] = relationship()


class RecuperacionClave(Base):
    __tablename__ = "recuperacion_clave"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usado_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    usuario: Mapped["Usuario"] = relationship()
