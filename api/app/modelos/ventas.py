"""Puntos de venta, productos, precios, turnos de caja y ventas."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modelos.aves import TipoHuevo
from app.modelos.base import Base, Marcas

CLASES_PRODUCTO = ("huevo", "ave_descarte", "ave_engorde", "otro")
PRESENTACIONES = ("unidad", "docena", "medio_panal", "panal", "kg")
COBRO_POR = ("unidad", "kg")
ESTADOS_VENTA = ("activa", "anulada")
ESTADOS_TURNO = ("abierto", "cerrado")

# Cuantos huevos trae cada presentacion
UNIDADES_POR_PRESENTACION = {"unidad": 1, "docena": 12, "medio_panal": 15, "panal": 30, "kg": 1}


class PuntoVenta(Base, Marcas):
    """Donde se vende: en una finca o un punto central."""

    __tablename__ = "puntos_venta"
    __table_args__ = (UniqueConstraint("cuenta_id", "codigo", name="uq_punto_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int | None] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(10), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(200))
    # Numeracion de las ventas: PV1-000123
    prefijo: Mapped[str] = mapped_column(String(10), default="PV", nullable=False)
    consecutivo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UsuarioPuntoVenta(Base):
    """Cajeros habilitados en un punto de venta."""

    __tablename__ = "usuario_puntos_venta"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    punto_venta_id: Mapped[int] = mapped_column(ForeignKey("puntos_venta.id", ondelete="CASCADE"), primary_key=True)


class MetodoPago(Base):
    __tablename__ = "metodos_pago"
    __table_args__ = (UniqueConstraint("cuenta_id", "nombre", name="uq_metodo_pago_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(40), nullable=False)
    # El efectivo es lo unico que se cuenta al cerrar la caja
    es_efectivo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProductoVenta(Base, Marcas):
    """Lo que se vende y como se cobra."""

    __tablename__ = "productos_venta"
    __table_args__ = (UniqueConstraint("cuenta_id", "nombre", name="uq_producto_venta_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    clase: Mapped[str] = mapped_column(Enum(*CLASES_PRODUCTO, name="clase_producto"), nullable=False)
    tipo_huevo_id: Mapped[int | None] = mapped_column(ForeignKey("tipos_huevo.id"))
    presentacion: Mapped[str] = mapped_column(Enum(*PRESENTACIONES, name="presentacion"), default="unidad", nullable=False)
    # Cuantas unidades salen del inventario por cada uno que se vende
    factor: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cobro_por: Mapped[str] = mapped_column(Enum(*COBRO_POR, name="cobro_por"), default="unidad", nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tipo_huevo: Mapped["TipoHuevo | None"] = relationship(lazy="joined")


class Precio(Base):
    """Historial de precios. El vigente es el que no tiene fecha de fin."""

    __tablename__ = "precios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos_venta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    punto_venta_id: Mapped[int | None] = mapped_column(ForeignKey("puntos_venta.id", ondelete="CASCADE"))
    precio: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date)
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TurnoCaja(Base):
    """Cada jornada de un cajero en un punto de venta."""

    __tablename__ = "turnos_caja"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    punto_venta_id: Mapped[int] = mapped_column(ForeignKey("puntos_venta.id"), nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS_TURNO, name="estado_turno"), default="abierto", nullable=False)
    base_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    abierto_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime)
    efectivo_contado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    diferencia: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    observaciones: Mapped[str | None] = mapped_column(String(255))


class Venta(Base):
    """Una venta. No se borra: se anula y queda registrada."""

    __tablename__ = "ventas"
    __table_args__ = (UniqueConstraint("punto_venta_id", "numero", name="uq_venta_numero"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int | None] = mapped_column(ForeignKey("fincas.id", ondelete="SET NULL"), index=True)
    punto_venta_id: Mapped[int] = mapped_column(ForeignKey("puntos_venta.id"), nullable=False, index=True)
    turno_id: Mapped[int | None] = mapped_column(ForeignKey("turnos_caja.id"), index=True)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    descuento: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS_VENTA, name="estado_venta"), default="activa", nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(255))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    anulada_en: Mapped[datetime | None] = mapped_column(DateTime)
    anulada_por: Mapped[str | None] = mapped_column(String(160))
    motivo_anulacion: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    detalles: Mapped[list["VentaDetalle"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan", lazy="selectin"
    )
    pagos: Mapped[list["VentaPago"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan", lazy="selectin"
    )
    punto: Mapped["PuntoVenta"] = relationship(lazy="joined")


class VentaDetalle(Base):
    __tablename__ = "venta_detalles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False, index=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos_venta.id"), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(120), nullable=False)
    clase: Mapped[str] = mapped_column(String(20), nullable=False)
    # Lo que se cobra: cantidad de presentaciones, o kilos si se cobra por kg
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    # Lo que sale del inventario
    unidades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    peso_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    tipo_huevo_id: Mapped[int | None] = mapped_column(ForeignKey("tipos_huevo.id"))
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id"))
    movimiento_aves_id: Mapped[int | None] = mapped_column(ForeignKey("movimientos_aves.id", ondelete="SET NULL"))

    venta: Mapped["Venta"] = relationship(back_populates="detalles")


class VentaPago(Base):
    __tablename__ = "venta_pagos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False, index=True)
    metodo_pago_id: Mapped[int] = mapped_column(ForeignKey("metodos_pago.id"), nullable=False)
    metodo_nombre: Mapped[str] = mapped_column(String(40), nullable=False)
    es_efectivo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    referencia: Mapped[str | None] = mapped_column(String(60))

    venta: Mapped["Venta"] = relationship(back_populates="pagos")
