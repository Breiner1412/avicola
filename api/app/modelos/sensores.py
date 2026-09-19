"""Sensores de los galpones y sus lecturas."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modelos.base import Base

ORIGENES = ("manual", "dispositivo")


class TipoSensor(Base):
    """Que mide el sensor: temperatura, humedad, amoniaco, agua..."""

    __tablename__ = "tipos_sensor"
    __table_args__ = (UniqueConstraint("cuenta_id", "nombre", name="uq_tipo_sensor_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    unidad: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    # Rango en el que todo esta bien (se puede cambiar por sensor)
    min_ok: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    max_ok: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))


class Sensor(Base):
    __tablename__ = "sensores"
    __table_args__ = (UniqueConstraint("finca_id", "codigo", name="uq_sensor_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), nullable=False, index=True)
    galpon_id: Mapped[int | None] = mapped_column(ForeignKey("galpones.id", ondelete="SET NULL"), index=True)
    tipo_id: Mapped[int] = mapped_column(ForeignKey("tipos_sensor.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    ubicacion: Mapped[str | None] = mapped_column(String(120))
    min_ok: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    max_ok: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    tipo: Mapped["TipoSensor"] = relationship(lazy="joined")


class LecturaSensor(Base):
    __tablename__ = "lecturas_sensor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensores.id", ondelete="CASCADE"), nullable=False, index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    medido_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    fuera_rango: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    origen: Mapped[str] = mapped_column(Enum(*ORIGENES, name="origen_lectura"), default="manual", nullable=False)
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
