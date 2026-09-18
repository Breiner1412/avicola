"""Tareas del dia a dia, rutinas que se repiten y novedades de la finca."""

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
    Text,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modelos.base import Base

PRIORIDADES = ("baja", "media", "alta")
ESTADOS_TAREA = ("pendiente", "en_proceso", "hecha", "cancelada")
FRECUENCIAS = ("diaria", "semanal", "mensual")
# Lo que suele pasar en una finca y no es parte del trabajo normal
CATEGORIAS_NOVEDAD = ("infraestructura", "clima", "animales", "servicios", "seguridad", "salud", "otro")
GRAVEDADES = ("baja", "media", "alta")
ESTADOS_NOVEDAD = ("abierta", "en_proceso", "cerrada")


class Rutina(Base):
    """Una tarea que se repite: se generan las tareas del dia a partir de ella."""

    __tablename__ = "rutinas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    frecuencia: Mapped[str] = mapped_column(Enum(*FRECUENCIAS, name="frecuencia_rutina"), default="diaria", nullable=False)
    # Para las semanales: [0..6] empezando en lunes
    dias_semana: Mapped[list | None] = mapped_column(JSON)
    dia_mes: Mapped[int | None] = mapped_column(Integer)
    hora: Mapped[str | None] = mapped_column(String(5))
    prioridad: Mapped[str] = mapped_column(Enum(*PRIORIDADES, name="prioridad_rutina"), default="media", nullable=False)
    asignado_a: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    galpon_id: Mapped[int | None] = mapped_column(ForeignKey("galpones.id", ondelete="SET NULL"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ultima_generacion: Mapped[date | None] = mapped_column(Date)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Tarea(Base):
    __tablename__ = "tareas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    prioridad: Mapped[str] = mapped_column(Enum(*PRIORIDADES, name="prioridad_tarea"), default="media", nullable=False)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS_TAREA, name="estado_tarea"), default="pendiente", nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora: Mapped[str | None] = mapped_column(String(5))
    asignado_a: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    asignado_nombre: Mapped[str | None] = mapped_column(String(160))
    galpon_id: Mapped[int | None] = mapped_column(ForeignKey("galpones.id", ondelete="SET NULL"))
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id", ondelete="SET NULL"))
    rutina_id: Mapped[int | None] = mapped_column(ForeignKey("rutinas.id", ondelete="SET NULL"), index=True)
    creado_por: Mapped[str | None] = mapped_column(String(160))
    terminada_en: Mapped[datetime | None] = mapped_column(DateTime)
    terminada_por: Mapped[str | None] = mapped_column(String(160))
    notas: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    rutina: Mapped["Rutina | None"] = relationship(lazy="joined")


class Novedad(Base):
    """Algo fuera de lo normal: un dano, un evento de clima, un problema de servicios."""

    __tablename__ = "novedades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, index=True)
    finca_id: Mapped[int] = mapped_column(ForeignKey("fincas.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    categoria: Mapped[str] = mapped_column(
        Enum(*CATEGORIAS_NOVEDAD, name="categoria_novedad"), default="otro", nullable=False, index=True
    )
    # Texto libre: cada finca nombra las cosas a su manera
    subtipo: Mapped[str | None] = mapped_column(String(80))
    titulo: Mapped[str] = mapped_column(String(140), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    gravedad: Mapped[str] = mapped_column(Enum(*GRAVEDADES, name="gravedad_novedad"), default="media", nullable=False)
    estado: Mapped[str] = mapped_column(
        Enum(*ESTADOS_NOVEDAD, name="estado_novedad"), default="abierta", nullable=False, index=True
    )
    galpon_id: Mapped[int | None] = mapped_column(ForeignKey("galpones.id", ondelete="SET NULL"))
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id", ondelete="SET NULL"))
    aves_afectadas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    movimiento_aves_id: Mapped[int | None] = mapped_column(ForeignKey("movimientos_aves.id", ondelete="SET NULL"))
    costo_estimado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    acciones: Mapped[str | None] = mapped_column(Text)
    reportado_por: Mapped[str | None] = mapped_column(String(160))
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime)
    cerrada_por: Mapped[str | None] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
