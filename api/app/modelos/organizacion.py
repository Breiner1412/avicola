"""Cuentas (empresa o persona), fincas y galpones."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modelos.base import Base, Marcas

if TYPE_CHECKING:
    from app.modelos.acceso import Usuario

TIPOS_CUENTA = ("empresa", "persona")
TIPOS_GALPON = ("postura", "levante", "engorde", "cria")


class Cuenta(Base, Marcas):
    """Empresa o persona duena de una o varias fincas."""

    __tablename__ = "cuentas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS_CUENTA, name="tipo_cuenta"), default="empresa", nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    documento: Mapped[str | None] = mapped_column(String(30), unique=True)
    email_contacto: Mapped[str | None] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(30))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    fincas: Mapped[list["Finca"]] = relationship(back_populates="cuenta", cascade="all, delete-orphan")
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="cuenta")


class Finca(Base, Marcas):
    __tablename__ = "fincas"
    __table_args__ = (UniqueConstraint("cuenta_id", "codigo", name="uq_finca_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    municipio: Mapped[str | None] = mapped_column(String(100))
    departamento: Mapped[str | None] = mapped_column(String(100))
    direccion: Mapped[str | None] = mapped_column(String(200))
    telefono: Mapped[str | None] = mapped_column(String(30))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cuenta: Mapped["Cuenta"] = relationship(back_populates="fincas")
    galpones: Mapped[list["Galpon"]] = relationship(back_populates="finca", cascade="all, delete-orphan")


class Galpon(Base, Marcas):
    __tablename__ = "galpones"
    __table_args__ = (UniqueConstraint("finca_id", "codigo", name="uq_galpon_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finca_id: Mapped[int] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS_GALPON, name="tipo_galpon"), default="postura", nullable=False)
    capacidad: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aves_actuales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    finca: Mapped["Finca"] = relationship(back_populates="galpones")
