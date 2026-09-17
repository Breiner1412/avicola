"""Registro de todo lo que se hace en el sistema (no se edita ni se borra)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.base import Base


class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        Index("ix_auditoria_cuenta_fecha", "cuenta_id", "creado_en"),
        Index("ix_auditoria_entidad", "entidad", "entidad_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id", ondelete="SET NULL"))
    finca_id: Mapped[int | None] = mapped_column(ForeignKey("fincas.id", ondelete="SET NULL"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    accion: Mapped[str] = mapped_column(String(40), nullable=False)
    entidad: Mapped[str] = mapped_column(String(50), nullable=False)
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    datos: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(45))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
