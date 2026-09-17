"""Lotes de aves, movimientos, produccion de huevos, pesajes, alimentacion y sanidad."""

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
from app.modelos.inventario import Articulo

PROPOSITOS = ("postura", "engorde", "levante")
ESTADOS_LOTE = ("activo", "cerrado")
# Lo que le puede pasar a las aves de un lote
TIPOS_MOVIMIENTO_AVES = ("ingreso", "muerte", "descarte", "fuga", "robo", "venta", "traslado", "consumo", "regalo")
# Movimientos que sacan aves del lote (el descarte pasa a salvamento)
TIPOS_SALIDA = ("muerte", "descarte", "fuga", "robo", "venta", "consumo", "regalo")
TIPOS_SANIDAD = ("vacuna", "medicamento", "vitamina", "desinfeccion", "otro")
VIAS = ("agua", "ocular", "aspersion", "inyectado", "alimento", "otro")


class Raza(Base):
    __tablename__ = "razas"
    __table_args__ = (UniqueConstraint("cuenta_id", "nombre", name="uq_raza_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    proposito: Mapped[str] = mapped_column(Enum(*PROPOSITOS, name="proposito_raza"), default="postura", nullable=False)


class Lote(Base, Marcas):
    """Un grupo de aves que entra junto a un galpon."""

    __tablename__ = "lotes"
    __table_args__ = (UniqueConstraint("finca_id", "codigo", name="uq_lote_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), nullable=False, index=True)
    galpon_id: Mapped[int] = mapped_column(ForeignKey("galpones.id"), nullable=False, index=True)
    raza_id: Mapped[int | None] = mapped_column(ForeignKey("razas.id"))
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    proposito: Mapped[str] = mapped_column(Enum(*PROPOSITOS, name="proposito_lote"), default="postura", nullable=False)
    fecha_ingreso: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    edad_dias_ingreso: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    aves_iniciales: Mapped[int] = mapped_column(Integer, nullable=False)
    aves_actuales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Gallinas que ya no producen y quedan para venta de salvamento
    aves_descarte: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    costo_ave: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS_LOTE, name="estado_lote"), default="activo", nullable=False)
    fecha_cierre: Mapped[date | None] = mapped_column(Date)
    observaciones: Mapped[str | None] = mapped_column(String(255))

    raza: Mapped["Raza | None"] = relationship(lazy="joined")


class MovimientoAves(Base):
    """Cada entrada o salida de aves del lote. No se borra: se anula."""

    __tablename__ = "movimientos_aves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS_MOVIMIENTO_AVES, name="tipo_mov_aves"), nullable=False, index=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    galpon_destino_id: Mapped[int | None] = mapped_column(ForeignKey("galpones.id"))
    peso_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    motivo: Mapped[str | None] = mapped_column(String(80))
    observaciones: Mapped[str | None] = mapped_column(String(255))
    # Una venta puede salir de las aves de descarte o de las que estan en produccion
    desde_descarte: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    anulado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime)
    anulado_por: Mapped[str | None] = mapped_column(String(160))
    motivo_anulacion: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    lote: Mapped["Lote"] = relationship(lazy="joined")


class TipoHuevo(Base):
    __tablename__ = "tipos_huevo"
    __table_args__ = (UniqueConstraint("cuenta_id", "nombre", name="uq_tipo_huevo_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(40), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Los no comerciales (rotos, sucios) no suman al stock que se vende
    comercial: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProduccionHuevos(Base):
    """Recoleccion de un dia, por lote y tipo de huevo."""

    __tablename__ = "produccion_huevos"
    __table_args__ = (UniqueConstraint("lote_id", "fecha", "tipo_huevo_id", name="uq_produccion_dia"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), nullable=False, index=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_huevo_id: Mapped[int] = mapped_column(ForeignKey("tipos_huevo.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cantidad: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    tipo: Mapped["TipoHuevo"] = relationship(lazy="joined")


class StockHuevos(Base):
    """Huevos disponibles por finca y tipo (suman al recolectar, restan al vender)."""

    __tablename__ = "stock_huevos"

    finca_id: Mapped[int] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), primary_key=True)
    tipo_huevo_id: Mapped[int] = mapped_column(ForeignKey("tipos_huevo.id", ondelete="CASCADE"), primary_key=True)
    cantidad: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime)


class Pesaje(Base):
    """Peso promedio del lote, sobre todo en engorde."""

    __tablename__ = "pesajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    aves_muestra: Mapped[int] = mapped_column(Integer, nullable=False)
    peso_total_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    peso_promedio_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    edad_dias: Mapped[int | None] = mapped_column(Integer)
    observaciones: Mapped[str | None] = mapped_column(String(255))
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ConsumoAlimento(Base):
    """Alimento que se le da a un lote. Sale de una bodega."""

    __tablename__ = "consumos_alimento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id"), nullable=False)
    bodega_id: Mapped[int] = mapped_column(ForeignKey("bodegas.id"), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    costo: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    movimiento_id: Mapped[int | None] = mapped_column(
        ForeignKey("movimientos_inventario.id", ondelete="SET NULL")
    )
    observaciones: Mapped[str | None] = mapped_column(String(255))
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    articulo: Mapped["Articulo"] = relationship(lazy="joined")


class AplicacionSanitaria(Base):
    """Vacunas, medicamentos y tratamientos aplicados a un lote o galpon."""

    __tablename__ = "aplicaciones_sanitarias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), nullable=False, index=True)
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id", ondelete="SET NULL"), index=True)
    galpon_id: Mapped[int | None] = mapped_column(ForeignKey("galpones.id", ondelete="SET NULL"))
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS_SANIDAD, name="tipo_sanidad"), default="vacuna", nullable=False)
    producto: Mapped[str] = mapped_column(String(150), nullable=False)
    articulo_id: Mapped[int | None] = mapped_column(ForeignKey("articulos.id"))
    cantidad_usada: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    costo: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    bodega_id: Mapped[int | None] = mapped_column(ForeignKey("bodegas.id"))
    movimiento_id: Mapped[int | None] = mapped_column(
        ForeignKey("movimientos_inventario.id", ondelete="SET NULL")
    )
    lote_producto: Mapped[str | None] = mapped_column(String(60))
    dosis: Mapped[str | None] = mapped_column(String(60))
    via: Mapped[str] = mapped_column(Enum(*VIAS, name="via_sanidad"), default="agua", nullable=False)
    aves_tratadas: Mapped[int | None] = mapped_column(Integer)
    responsable: Mapped[str | None] = mapped_column(String(120))
    proximo_refuerzo: Mapped[date | None] = mapped_column(Date)
    observaciones: Mapped[str | None] = mapped_column(String(255))
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
