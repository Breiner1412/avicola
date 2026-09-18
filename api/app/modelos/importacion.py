"""Importaciones desde Excel: archivo analizado, filas y plantillas de mapeo."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modelos.base import Base

TIPOS_IMPORTACION = ("articulos", "entrada_inventario", "proveedores", "sanidad", "produccion")
ESTADOS_IMPORTACION = ("pendiente", "aplicada", "revertida")
ESTADOS_FILA = ("pendiente", "ok", "error", "aplicada", "revertida")


class PlantillaImportacion(Base):
    """Un mapeo guardado para no volver a emparejar las columnas cada vez."""

    __tablename__ = "plantillas_importacion"
    __table_args__ = (UniqueConstraint("cuenta_id", "tipo", "nombre", name="uq_plantilla_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS_IMPORTACION, name="tipo_importacion"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    # {campo del sistema: nombre de la columna del archivo}
    mapeo: Mapped[dict] = mapped_column(JSON, nullable=False)
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Importacion(Base):
    __tablename__ = "importaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int | None] = mapped_column(ForeignKey("fincas.id", ondelete="SET NULL"), index=True)
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS_IMPORTACION, name="tipo_importacion_arch"), nullable=False)
    archivo: Mapped[str] = mapped_column(String(200), nullable=False)
    hoja: Mapped[str | None] = mapped_column(String(80))
    estado: Mapped[str] = mapped_column(
        Enum(*ESTADOS_IMPORTACION, name="estado_importacion"), default="pendiente", nullable=False
    )
    columnas: Mapped[list] = mapped_column(JSON, nullable=False)
    mapeo: Mapped[dict | None] = mapped_column(JSON)
    opciones: Mapped[dict | None] = mapped_column(JSON)
    resumen: Mapped[dict | None] = mapped_column(JSON)
    filas_totales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filas_ok: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filas_error: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    usuario_nombre: Mapped[str | None] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    aplicada_en: Mapped[datetime | None] = mapped_column(DateTime)
    revertida_en: Mapped[datetime | None] = mapped_column(DateTime)
    revertida_por: Mapped[str | None] = mapped_column(String(160))

    filas: Mapped[list["FilaImportacion"]] = relationship(
        back_populates="importacion", cascade="all, delete-orphan"
    )


class FilaImportacion(Base):
    __tablename__ = "importacion_filas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importacion_id: Mapped[int] = mapped_column(
        ForeignKey("importaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    datos: Mapped[dict] = mapped_column(JSON, nullable=False)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS_FILA, name="estado_fila"), default="pendiente", nullable=False)
    error: Mapped[str | None] = mapped_column(String(255))
    # Que se creo con esta fila, para poder deshacerlo
    entidad: Mapped[str | None] = mapped_column(String(40))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    creado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    importacion: Mapped["Importacion"] = relationship(back_populates="filas")
