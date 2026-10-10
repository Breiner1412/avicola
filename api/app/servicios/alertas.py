"""Calcula los avisos de la campana a partir de lo que esta pasando en la finca."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select, true
from sqlalchemy.orm import Session

from app.core.contexto import Contexto
from app.core.db import bloquear
from app.core.tiempo import hoy as hoy_en_la_granja, inicio_del_dia
from app.modelos.alertas import Alerta
from app.modelos.aves import AplicacionSanitaria
from app.modelos.inventario import Articulo, Bodega, Existencia
from app.modelos.organizacion import Cuenta
from app.modelos.sensores import LecturaSensor, Sensor
from app.modelos.trabajo import Novedad, Tarea
from app.modelos.ventas import PuntoVenta, TurnoCaja
from app.servicios.alcance import cuenta_filtro, ids_fincas_visibles
from app.servicios.aves import refuerzos_pendientes

DIAS_REFUERZO = 7
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def _fecha(dia: date | datetime) -> str:
    """18 sep 2026"""
    return f"{dia.day} {MESES[dia.month - 1]} {dia.year}"


def _numero(valor: float) -> str:
    """1.234,5 al estilo colombiano."""
    texto = f"{valor:,.2f}".rstrip("0").rstrip(".")
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def _unidad(unidad: str) -> str:
    return "°C" if unidad == "C" else unidad


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _stock_bajo(db: Session, cuenta_id: int, fincas: list[int]) -> list[dict]:
    """Articulos por debajo del minimo en las bodegas centrales o de estas fincas."""
    encontradas: list[dict] = []
    bodegas = [
        b.id
        for b in db.scalars(
            select(Bodega).where(
                Bodega.cuenta_id == cuenta_id,
                (Bodega.finca_id.is_(None)) | (Bodega.finca_id.in_(fincas or [0])),
            )
        ).all()
    ]
    if bodegas:
        filas = db.execute(
            select(Articulo.id, Articulo.nombre, Articulo.unidad, Articulo.stock_minimo,
                   func.coalesce(func.sum(Existencia.cantidad), 0))
            .join(Existencia, (Existencia.articulo_id == Articulo.id) & (Existencia.bodega_id.in_(bodegas)), isouter=True)
            .where(Articulo.cuenta_id == cuenta_id, Articulo.activo.is_(True), Articulo.stock_minimo > 0)
            .group_by(Articulo.id, Articulo.nombre, Articulo.unidad, Articulo.stock_minimo)
        ).all()
        # Un articulo que solo se maneja en la bodega de otra finca no es asunto de esta
        propias = set(
            db.scalars(
                select(Existencia.articulo_id)
                .join(Bodega, Bodega.id == Existencia.bodega_id)
                .where(Bodega.cuenta_id == cuenta_id, Bodega.finca_id.in_(fincas or [0]))
            ).all()
        )
        de_otras = set(
            db.scalars(
                select(Existencia.articulo_id)
                .join(Bodega, Bodega.id == Existencia.bodega_id)
                .where(Bodega.cuenta_id == cuenta_id, Bodega.finca_id.is_not(None), Bodega.finca_id.not_in(fincas or [0]))
            ).all()
        )
        for articulo_id, nombre, unidad, minimo, hay in filas:
            if articulo_id not in propias and articulo_id in de_otras:
                continue  # ese articulo solo se usa en otra finca
            if float(hay or 0) < float(minimo):
                encontradas.append(
                    {
                        "clave": f"stock:{articulo_id}",
                        "tipo": "stock",
                        "nivel": "critico" if float(hay or 0) == 0 else "aviso",
                        "titulo": f"Queda poco {nombre}",
                        "detalle": f"Hay {_numero(float(hay or 0))} {unidad} y el minimo es {_numero(float(minimo))}",
                        "ruta": "/articulos",
                        "entidad_id": articulo_id,
                        "finca_id": None,
                    }
                )
    return encontradas


def _sensores_fuera_de_rango(db: Session, cuenta_id: int, fincas: list[int]) -> list[dict]:
    """Sensores cuya ultima medicion quedo fuera del rango normal."""
    encontradas: list[dict] = []
    sensores = db.scalars(
        select(Sensor).where(Sensor.cuenta_id == cuenta_id, Sensor.finca_id.in_(fincas), Sensor.activo.is_(True))
    ).unique().all()
    for sensor in sensores:
        ultima = db.scalars(
            select(LecturaSensor)
            .where(LecturaSensor.sensor_id == sensor.id)
            .order_by(LecturaSensor.medido_en.desc(), LecturaSensor.id.desc())
            .limit(1)
        ).first()
        if ultima is None or not ultima.fuera_rango:
            continue
        unidad = sensor.tipo.unidad if sensor.tipo else ""
        encontradas.append(
            {
                "clave": f"sensor:{sensor.id}",
                "tipo": "sensor",
                "nivel": "critico",
                "titulo": f"{sensor.nombre} fuera de rango",
                "detalle": f"Ultima medicion: {_numero(float(ultima.valor))} {_unidad(unidad)}",
                "ruta": "/sensores",
                "entidad_id": sensor.id,
                "finca_id": sensor.finca_id,
            }
        )
    return encontradas


def _refuerzos(db: Session, fincas: list[int], hoy: date) -> list[dict]:
    """Refuerzos de vacuna atrasados o de los proximos dias."""
    encontradas: list[dict] = []
    limite = hoy + timedelta(days=DIAS_REFUERZO)
    refuerzos = db.scalars(
        select(AplicacionSanitaria).where(
            AplicacionSanitaria.finca_id.in_(fincas),
            AplicacionSanitaria.proximo_refuerzo.is_not(None),
            AplicacionSanitaria.proximo_refuerzo <= limite,
        )
    ).all()
    for aplicacion in refuerzos_pendientes(db, list(refuerzos)):
        vencido = aplicacion.proximo_refuerzo < hoy
        encontradas.append(
            {
                "clave": f"sanidad:{aplicacion.id}",
                "tipo": "sanidad",
                "nivel": "critico" if vencido else "aviso",
                "titulo": f"{'Refuerzo atrasado' if vencido else 'Refuerzo proximo'}: {aplicacion.producto}",
                "detalle": f"Para el {_fecha(aplicacion.proximo_refuerzo)}",
                "ruta": "/sanidad",
                "entidad_id": aplicacion.id,
                "finca_id": aplicacion.finca_id,
            }
        )
    return encontradas


def _tareas_atrasadas(db: Session, fincas: list[int], hoy: date) -> list[dict]:
    """Tareas que ya pasaron de fecha sin terminarse."""
    encontradas: list[dict] = []
    atrasadas = db.scalars(
        select(Tarea).where(
            Tarea.finca_id.in_(fincas),
            Tarea.fecha < hoy,
            Tarea.estado.in_(("pendiente", "en_proceso")),
        )
    ).all()
    for tarea in atrasadas:
        encontradas.append(
            {
                "clave": f"tarea:{tarea.id}",
                "tipo": "tarea",
                "nivel": "aviso",
                "titulo": f"Tarea atrasada: {tarea.titulo}",
                "detalle": f"Era para el {_fecha(tarea.fecha)}" + (f" · {tarea.asignado_nombre}" if tarea.asignado_nombre else ""),
                "ruta": "/tareas",
                "entidad_id": tarea.id,
                "finca_id": tarea.finca_id,
            }
        )
    return encontradas


def _novedades_graves(db: Session, fincas: list[int]) -> list[dict]:
    """Novedades de gravedad alta sin cerrar."""
    encontradas: list[dict] = []
    novedades = db.scalars(
        select(Novedad).where(
            Novedad.finca_id.in_(fincas),
            Novedad.estado.in_(("abierta", "en_proceso")),
            Novedad.gravedad == "alta",
        )
    ).all()
    for novedad in novedades:
        encontradas.append(
            {
                "clave": f"novedad:{novedad.id}",
                "tipo": "novedad",
                "nivel": "critico",
                "titulo": f"Novedad sin resolver: {novedad.titulo}",
                "detalle": f"Reportada el {_fecha(novedad.fecha)}",
                "ruta": "/novedades",
                "entidad_id": novedad.id,
                "finca_id": novedad.finca_id,
            }
        )
    return encontradas


def _cajas_abiertas(db: Session, cuenta_id: int, fincas: list[int], hoy: date) -> list[dict]:
    """Cajas que quedaron abiertas de dias anteriores."""
    encontradas: list[dict] = []
    puntos = [
        p.id
        for p in db.scalars(
            select(PuntoVenta).where(
                PuntoVenta.cuenta_id == cuenta_id,
                (PuntoVenta.finca_id.is_(None)) | (PuntoVenta.finca_id.in_(fincas)),
            )
        ).all()
    ]
    if puntos:
        turnos = db.scalars(
            select(TurnoCaja).where(
                TurnoCaja.punto_venta_id.in_(puntos),
                TurnoCaja.estado == "abierto",
                TurnoCaja.abierto_en < inicio_del_dia(hoy),
            )
        ).all()
        for turno in turnos:
            encontradas.append(
                {
                    "clave": f"caja:{turno.id}",
                    "tipo": "caja",
                    "nivel": "aviso",
                    "titulo": "Hay una caja sin cerrar",
                    "detalle": f"Abierta desde el {_fecha(turno.abierto_en)} por {turno.usuario_nombre or ''}".strip(),
                    "ruta": "/caja",
                    "entidad_id": turno.id,
                    "finca_id": None,
                }
            )
    return encontradas


def _situaciones(db: Session, ctx: Contexto, cuenta_id: int, fincas: list[int]) -> list[dict]:
    """Todo lo que hoy merece un aviso en estas fincas."""
    hoy = hoy_en_la_granja()
    encontradas = _stock_bajo(db, cuenta_id, fincas)
    if not fincas:
        return encontradas
    return [
        *encontradas,
        *_sensores_fuera_de_rango(db, cuenta_id, fincas),
        *_refuerzos(db, fincas, hoy),
        *_tareas_atrasadas(db, fincas, hoy),
        *_novedades_graves(db, fincas),
        *_cajas_abiertas(db, cuenta_id, fincas, hoy),
    ]


def _guardar_aviso(db: Session, cuenta_id: int, alerta: Alerta | None, situacion: dict, momento: datetime) -> None:
    """Crea el aviso o, si ya existia, lo actualiza (y lo reabre si se habia cerrado)."""
    if alerta is None:
        db.add(
            Alerta(
                cuenta_id=cuenta_id,
                finca_id=situacion.get("finca_id"),
                clave=situacion["clave"],
                tipo=situacion["tipo"],
                nivel=situacion["nivel"],
                titulo=situacion["titulo"][:140],
                detalle=(situacion.get("detalle") or "")[:255] or None,
                ruta=situacion.get("ruta"),
                entidad_id=situacion.get("entidad_id"),
                activa=True,
                leida=False,
                creado_en=momento,
                actualizado_en=momento,
            )
        )
        return
    if not alerta.activa:
        alerta.activa = True
        alerta.leida = False
        alerta.resuelta_en = None
    alerta.nivel = situacion["nivel"]
    alerta.titulo = situacion["titulo"][:140]
    alerta.detalle = (situacion.get("detalle") or "")[:255] or None
    alerta.actualizado_en = momento


def avisos_visibles(db: Session, ctx: Contexto):
    """Condicion para ver o marcar avisos: los de la cuenta y los de las fincas del usuario.

    Con finca activa, solo los de esa finca; sin ella, quien no ve toda la cuenta (el
    supervisor) solo ve los de sus fincas.
    """
    if ctx.finca_id is not None:
        return or_(Alerta.finca_id.is_(None), Alerta.finca_id == ctx.finca_id)
    if ctx.es_plataforma or ctx.ve_toda_la_cuenta:
        return true()
    return or_(Alerta.finca_id.is_(None), Alerta.finca_id.in_(ids_fincas_visibles(db, ctx) or [0]))


def recalcular(db: Session, ctx: Contexto) -> list[Alerta]:
    """Actualiza la lista de avisos: agrega los nuevos y cierra los que ya se resolvieron."""
    cuenta_id = cuenta_filtro(ctx)
    if cuenta_id is None:
        return []

    # Una sola revision a la vez por cuenta: dos peticiones juntas no insertan el
    # mismo aviso dos veces (chocaban con el indice unico y respondian 500)
    bloquear(db, Cuenta, cuenta_id)

    fincas = [ctx.finca_id] if ctx.finca_id is not None else ids_fincas_visibles(db, ctx)
    situaciones = _situaciones(db, ctx, cuenta_id, fincas)
    claves = {s["clave"] for s in situaciones}

    existentes = {
        a.clave: a for a in db.scalars(select(Alerta).where(Alerta.cuenta_id == cuenta_id)).all()
    }
    revisadas = set(fincas)

    momento = ahora()
    for situacion in situaciones:
        _guardar_aviso(db, cuenta_id, existentes.get(situacion["clave"]), situacion, momento)

    # Lo que ya no esta pasando se cierra solo, pero solo en las fincas que se
    # revisaron: los avisos de otra finca no se tocan desde aqui
    for clave, alerta in existentes.items():
        if alerta.finca_id is not None and alerta.finca_id not in revisadas:
            continue
        if alerta.activa and clave not in claves:
            alerta.activa = False
            alerta.resuelta_en = momento

    db.flush()

    consulta = select(Alerta).where(Alerta.cuenta_id == cuenta_id, Alerta.activa.is_(True), avisos_visibles(db, ctx))

    orden = {"critico": 0, "aviso": 1, "info": 2}
    alertas = db.scalars(consulta).all()
    return sorted(alertas, key=lambda a: (orden.get(a.nivel, 3), a.creado_en), reverse=False)
