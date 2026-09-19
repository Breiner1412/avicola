"""Avisos que salen en la campana: lo que hay que mirar hoy."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.base import Base

TIPOS_ALERTA = ("stock", "sensor", "sanidad", "tarea", "novedad", "caja", "lote")
NIVELES = ("info", "aviso", "critico")


class Alerta(Base):
    __tablename__ = "alertas"
    __table_args__ = (UniqueConstraint("cuenta_id", "clave", name="uq_alerta_clave"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int | None] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), index=True)
    # Identifica la situacion para no repetir el mismo aviso
    clave: Mapped[str] = mapped_column(String(80), nullable=False)
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS_ALERTA, name="tipo_alerta"), nullable=False, index=True)
    nivel: Mapped[str] = mapped_column(Enum(*NIVELES, name="nivel_alerta"), default="aviso", nullable=False)
    titulo: Mapped[str] = mapped_column(String(140), nullable=False)
    detalle: Mapped[str | None] = mapped_column(String(255))
    ruta: Mapped[str | None] = mapped_column(String(80))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime)
