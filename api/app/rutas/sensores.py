"""Sensores de los galpones y sus lecturas."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import conflicto, datos_invalidos, no_encontrado
from app.esquemas.comunes import Mensaje
from app.esquemas.sensores import (
    LecturaCrear,
    LecturaSalida,
    LoteLecturas,
    ResultadoLecturas,
    SensorActualizar,
    SensorCrear,
    SensorSalida,
    TipoSensorCrear,
    TipoSensorSalida,
)
from app.modelos.organizacion import Galpon
from app.modelos.sensores import LecturaSensor, Sensor, TipoSensor
from app.servicios.alcance import cuenta_filtro, cuenta_objetivo, ids_fincas_visibles

router = APIRouter(tags=["Sensores"])


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _sin_zona(momento: datetime) -> datetime:
    """Las fechas se guardan en UTC sin zona."""
    if momento.tzinfo is not None:
        momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
    return momento


def estado_de(valor: float | None, minimo: float | None, maximo: float | None) -> str:
    if valor is None:
        return "sin_datos"
    if maximo is not None and valor > maximo:
        return "alto"
    if minimo is not None and valor < minimo:
        return "bajo"
    return "ok"


def limites(sensor: Sensor) -> tuple[float | None, float | None]:
    minimo = sensor.min_ok if sensor.min_ok is not None else (sensor.tipo.min_ok if sensor.tipo else None)
    maximo = sensor.max_ok if sensor.max_ok is not None else (sensor.tipo.max_ok if sensor.tipo else None)
    return (float(minimo) if minimo is not None else None, float(maximo) if maximo is not None else None)


def _salida(db: Session, sensor: Sensor, con_historial: bool = False) -> SensorSalida:
    ultima = db.scalars(
        select(LecturaSensor)
        .where(LecturaSensor.sensor_id == sensor.id)
        .order_by(LecturaSensor.medido_en.desc(), LecturaSensor.id.desc())
        .limit(1)
    ).first()
    minimo, maximo = limites(sensor)
    galpon = db.get(Galpon, sensor.galpon_id) if sensor.galpon_id else None

    historial: list[float] = []
    if con_historial:
        filas = db.scalars(
            select(LecturaSensor)
            .where(LecturaSensor.sensor_id == sensor.id)
            .order_by(LecturaSensor.medido_en.desc(), LecturaSensor.id.desc())
            .limit(24)
        ).all()
        historial = [float(f.valor) for f in reversed(filas)]

    return SensorSalida(
        id=sensor.id,
        finca_id=sensor.finca_id,
        galpon_id=sensor.galpon_id,
        galpon_nombre=galpon.nombre if galpon else None,
        tipo_id=sensor.tipo_id,
        tipo=sensor.tipo.nombre if sensor.tipo else "",
        unidad=sensor.tipo.unidad if sensor.tipo else "",
        codigo=sensor.codigo,
        nombre=sensor.nombre,
        ubicacion=sensor.ubicacion,
        min_ok=minimo,
        max_ok=maximo,
        activo=sensor.activo,
        estado=estado_de(float(ultima.valor) if ultima else None, minimo, maximo),
        ultimo_valor=float(ultima.valor) if ultima else None,
        ultima_medicion=ultima.medido_en if ultima else None,
        historial=historial,
    )


def sensores_visibles(db: Session, ctx: Contexto, incluir_inactivos: bool = False) -> list[Sensor]:
    consulta = select(Sensor)
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(Sensor.cuenta_id == cuenta)
    if ctx.finca_id is not None:
        consulta = consulta.where(Sensor.finca_id == ctx.finca_id)
    else:
        consulta = consulta.where(Sensor.finca_id.in_(ids_fincas_visibles(db, ctx) or [0]))
    if not incluir_inactivos:
        consulta = consulta.where(Sensor.activo.is_(True))
    return db.scalars(consulta.order_by(Sensor.nombre)).unique().all()


def sensor_de(db: Session, ctx: Contexto, sensor_id: int) -> Sensor:
    sensor = db.get(Sensor, sensor_id)
    cuenta = cuenta_filtro(ctx)
    if sensor is None or (cuenta is not None and sensor.cuenta_id != cuenta):
        raise no_encontrado("El sensor no existe")
    if sensor.finca_id not in ids_fincas_visibles(db, ctx):
        raise no_encontrado("El sensor no existe")
    return sensor


@router.get("/tipos-sensor", response_model=list[TipoSensorSalida], summary="Que se puede medir")
def listar_tipos(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("sensores", "ver"))):
    cuenta = cuenta_filtro(ctx)
    return db.scalars(
        select(TipoSensor)
        .where(or_(TipoSensor.cuenta_id.is_(None), TipoSensor.cuenta_id == cuenta))
        .order_by(TipoSensor.nombre)
    ).all()


@router.post("/tipos-sensor", response_model=TipoSensorSalida, status_code=201, summary="Agregar un tipo de sensor")
def crear_tipo(
    datos: TipoSensorCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sensores", "crear")),
):
    cuenta_id = cuenta_objetivo(ctx, None)
    tipo = TipoSensor(cuenta_id=cuenta_id, **datos.model_dump())
    db.add(tipo)
    db.flush()
    registrar(db, ctx, "crear", "tipos_sensor", tipo.id, f"Agrego el tipo de sensor {tipo.nombre}")
    db.commit()
    db.refresh(tipo)
    return tipo


@router.get("/sensores", response_model=list[SensorSalida], summary="Sensores de la finca")
def listar(
    incluir_inactivos: bool = Query(False),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sensores", "ver")),
):
    return [_salida(db, s, con_historial=True) for s in sensores_visibles(db, ctx, incluir_inactivos)]


@router.post("/sensores", response_model=SensorSalida, status_code=201, summary="Registrar un sensor")
def crear(
    datos: SensorCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sensores", "crear", con_finca=True)),
):
    tipo = db.get(TipoSensor, datos.tipo_id)
    if tipo is None:
        raise datos_invalidos("Ese tipo de sensor no existe")
    if datos.galpon_id:
        galpon = db.get(Galpon, datos.galpon_id)
        if galpon is None or galpon.finca_id != ctx.finca_id:
            raise datos_invalidos("El galpon no existe en esta finca")
    if db.scalars(
        select(Sensor.id).where(Sensor.finca_id == ctx.finca_id, Sensor.codigo == datos.codigo)
    ).first():
        raise conflicto(f"Ya existe un sensor con el codigo {datos.codigo}")

    sensor = Sensor(
        cuenta_id=ctx.cuenta_activa_id or ctx.cuenta_id,
        finca_id=ctx.finca_id,
        creado_en=ahora(),
        **datos.model_dump(),
    )
    db.add(sensor)
    db.flush()
    registrar(db, ctx, "crear", "sensores", sensor.id, f"Registro el sensor {sensor.nombre}")
    db.commit()
    db.refresh(sensor)
    return _salida(db, sensor)


@router.patch("/sensores/{sensor_id}", response_model=SensorSalida, summary="Editar un sensor")
def editar(
    sensor_id: int,
    datos: SensorActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sensores", "editar")),
):
    sensor = sensor_de(db, ctx, sensor_id)
    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(sensor, campo, valor)
    registrar(db, ctx, "editar", "sensores", sensor.id, f"Edito el sensor {sensor.nombre}", cambios)
    db.commit()
    db.refresh(sensor)
    return _salida(db, sensor)


@router.delete("/sensores/{sensor_id}", response_model=Mensaje, summary="Desactivar un sensor")
def desactivar(
    sensor_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sensores", "borrar")),
):
    sensor = sensor_de(db, ctx, sensor_id)
    sensor.activo = False
    registrar(db, ctx, "desactivar", "sensores", sensor.id, f"Desactivo el sensor {sensor.nombre}")
    db.commit()
    return Mensaje(mensaje="Sensor desactivado")


@router.post(
    "/sensores/lecturas",
    response_model=ResultadoLecturas,
    status_code=201,
    summary="Recibir varias mediciones de los equipos (por codigo de sensor)",
)
def recibir_lecturas(
    datos: LoteLecturas,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sensores", "crear", con_finca=True)),
):
    """Los equipos envian sus mediciones con el codigo del sensor en la finca activa."""
    codigos = {l.codigo for l in datos.lecturas}
    sensores = {
        s.codigo: s
        for s in db.scalars(
            select(Sensor).where(Sensor.finca_id == ctx.finca_id, Sensor.codigo.in_(codigos), Sensor.activo.is_(True))
        ).all()
    }
    guardadas = 0
    desconocidos: set[str] = set()
    for dato in datos.lecturas:
        sensor = sensores.get(dato.codigo)
        if sensor is None:
            desconocidos.add(dato.codigo)
            continue
        minimo, maximo = limites(sensor)
        db.add(
            LecturaSensor(
                sensor_id=sensor.id,
                valor=dato.valor,
                medido_en=_sin_zona(dato.medido_en) if dato.medido_en else ahora(),
                fuera_rango=estado_de(dato.valor, minimo, maximo) in ("alto", "bajo"),
                origen="dispositivo",
                usuario_nombre=ctx.usuario.nombre_completo,
                creado_en=ahora(),
            )
        )
        guardadas += 1
    db.commit()
    return ResultadoLecturas(guardadas=guardadas, codigos_desconocidos=sorted(desconocidos))


@router.get("/sensores/{sensor_id}/lecturas", response_model=list[LecturaSalida], summary="Lecturas del sensor")
def lecturas(
    sensor_id: int,
    horas: int = Query(48, ge=1, le=24 * 400),
    desde: datetime | None = Query(None, description="Inicio del periodo (UTC). Si se da, se ignora 'horas'"),
    hasta: datetime | None = Query(None, description="Fin del periodo (UTC)"),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sensores", "ver")),
):
    sensor = sensor_de(db, ctx, sensor_id)
    inicio = _sin_zona(desde) if desde else ahora() - timedelta(hours=horas)
    consulta = select(LecturaSensor).where(LecturaSensor.sensor_id == sensor.id, LecturaSensor.medido_en >= inicio)
    if hasta:
        consulta = consulta.where(LecturaSensor.medido_en < _sin_zona(hasta))
    filas = db.scalars(
        consulta.order_by(LecturaSensor.medido_en.desc(), LecturaSensor.id.desc()).limit(10000)
    ).all()
    return [
        LecturaSalida(
            id=f.id,
            sensor_id=f.sensor_id,
            valor=float(f.valor),
            medido_en=f.medido_en,
            fuera_rango=f.fuera_rango,
            origen=f.origen,
            usuario_nombre=f.usuario_nombre,
        )
        for f in filas
    ]


@router.post("/sensores/{sensor_id}/lecturas", response_model=LecturaSalida, status_code=201, summary="Anotar una medicion")
def anotar(
    sensor_id: int,
    datos: LecturaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sensores", "crear")),
):
    sensor = sensor_de(db, ctx, sensor_id)
    minimo, maximo = limites(sensor)
    fuera = estado_de(datos.valor, minimo, maximo) in ("alto", "bajo")

    lectura = LecturaSensor(
        sensor_id=sensor.id,
        valor=datos.valor,
        medido_en=(_sin_zona(datos.medido_en) if datos.medido_en else ahora()),
        fuera_rango=fuera,
        origen="dispositivo",
        usuario_nombre=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(lectura)
    db.flush()
    db.commit()
    db.refresh(lectura)
    return LecturaSalida(
        id=lectura.id,
        sensor_id=lectura.sensor_id,
        valor=float(lectura.valor),
        medido_en=lectura.medido_en,
        fuera_rango=lectura.fuera_rango,
        origen=lectura.origen,
        usuario_nombre=lectura.usuario_nombre,
    )
