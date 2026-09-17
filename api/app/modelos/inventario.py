"""Bodegas, articulos, proveedores, existencias y movimientos de inventario."""

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

from app.modelos.base import Base, Marcas

CLASES_ARTICULO = ("alimento", "medicamento", "vacuna", "herramienta", "repuesto", "insumo", "otro")
UNIDADES = ("unidad", "kg", "litro", "bulto", "dosis", "metro")
TIPOS_MOVIMIENTO = ("entrada", "salida", "traslado", "ajuste")


class Bodega(Base, Marcas):
    """Una bodega central de la cuenta (finca_id vacio) o la bodega de una finca."""

    __tablename__ = "bodegas"
    __table_args__ = (UniqueConstraint("cuenta_id", "codigo", name="uq_bodega_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int | None] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    ubicacion: Mapped[str | None] = mapped_column(String(150))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def es_central(self) -> bool:
        return self.finca_id is None


class CategoriaArticulo(Base):
    """Categorias del sistema (cuenta_id vacio) y las que agrega cada cuenta."""

    __tablename__ = "categorias_articulo"
    __table_args__ = (UniqueConstraint("cuenta_id", "nombre", name="uq_categoria_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    clase: Mapped[str] = mapped_column(Enum(*CLASES_ARTICULO, name="clase_articulo"), default="insumo", nullable=False)


class Articulo(Base, Marcas):
    __tablename__ = "articulos"
    __table_args__ = (UniqueConstraint("cuenta_id", "codigo", name="uq_articulo_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias_articulo.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    unidad: Mapped[str] = mapped_column(Enum(*UNIDADES, name="unidad_articulo"), default="unidad", nullable=False)
    # Para alimento que se compra por bultos y se consume por kilos
    kg_por_bulto: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    stock_minimo: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    categoria: Mapped["CategoriaArticulo"] = relationship(lazy="joined")


class Proveedor(Base, Marcas):
    __tablename__ = "proveedores"
    __table_args__ = (UniqueConstraint("cuenta_id", "nombre", name="uq_proveedor_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    documento: Mapped[str | None] = mapped_column(String(30))
    telefono: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))
    direccion: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Existencia(Base):
    """Cuanto hay de cada articulo en cada bodega."""

    __tablename__ = "existencias"

    bodega_id: Mapped[int] = mapped_column(ForeignKey("bodegas.id", ondelete="CASCADE"), primary_key=True)
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id", ondelete="CASCADE"), primary_key=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0, nullable=False)
    costo_promedio: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime)


class MovimientoInventario(Base):
    """Entrada, salida, traslado o ajuste. Nunca se borra: se anula."""

    __tablename__ = "movimientos_inventario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int | None] = mapped_column(ForeignKey("fincas.id", ondelete="SET NULL"), index=True)
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS_MOVIMIENTO, name="tipo_movimiento"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    bodega_id: Mapped[int] = mapped_column(ForeignKey("bodegas.id"), nullable=False, index=True)
    bodega_destino_id: Mapped[int | None] = mapped_column(ForeignKey("bodegas.id"))
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedores.id"))
    motivo: Mapped[str | None] = mapped_column(String(60))
    documento: Mapped[str | None] = mapped_column(String(60))
    observaciones: Mapped[str | None] = mapped_column(String(255))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    anulado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime)
    anulado_por: Mapped[str | None] = mapped_column(String(160))
    motivo_anulacion: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    items: Mapped[list["MovimientoItem"]] = relationship(
        back_populates="movimiento", cascade="all, delete-orphan", lazy="selectin"
    )
    bodega: Mapped["Bodega"] = relationship(foreign_keys=[bodega_id], lazy="joined")
    bodega_destino: Mapped["Bodega | None"] = relationship(foreign_keys=[bodega_destino_id], lazy="joined")
    proveedor: Mapped["Proveedor | None"] = relationship(lazy="joined")


class MovimientoItem(Base):
    __tablename__ = "movimiento_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movimiento_id: Mapped[int] = mapped_column(
        ForeignKey("movimientos_inventario.id", ondelete="CASCADE"), nullable=False, index=True
    )
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id"), nullable=False, index=True)
    # En los ajustes esta es la cantidad contada; en los demas, la que entra o sale.
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    # Diferencia aplicada a la existencia (util sobre todo en los ajustes)
    cantidad_aplicada: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0, nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    lote: Mapped[str | None] = mapped_column(String(40))
    vencimiento: Mapped[date | None] = mapped_column(Date)

    movimiento: Mapped["MovimientoInventario"] = relationship(back_populates="items")
    articulo: Mapped["Articulo"] = relationship(lazy="joined")
