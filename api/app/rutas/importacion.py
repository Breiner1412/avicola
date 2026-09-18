"""Subir un archivo de Excel o CSV y cargar sus datos al sistema."""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import conflicto, datos_invalidos, no_encontrado
from app.esquemas.comunes import Mensaje
from app.esquemas.importacion import (
    AnalisisSalida,
    CampoInfo,
    DetalleFila,
    ErrorFila,
    ImportacionDetalle,
    ImportacionSalida,
    MapeoEntrada,
    PlantillaCrear,
    PlantillaSalida,
    TipoInfo,
    ValidacionSalida,
)
from app.modelos.importacion import (
    TIPOS_IMPORTACION,
    FilaImportacion,
    Importacion,
    PlantillaImportacion,
)
from app.servicios.alcance import cuenta_filtro, cuenta_objetivo
from app.servicios.importacion import (
    CAMPOS,
    ETIQUETAS_TIPO,
    MAX_FILAS,
    ahora,
    aplicar_mapeo,
    leer_archivo,
    sugerir_mapeo,
    validar_fila,
)
from app.servicios.importacion_datos import aplicar as aplicar_datos
from app.servicios.importacion_datos import revertir as revertir_datos

router = APIRouter(prefix="/importacion", tags=["Importar desde Excel"])

MAX_BYTES = 5 * 1024 * 1024


def _campos(tipo: str) -> list[CampoInfo]:
    return [
        CampoInfo(clave=clave, etiqueta=etiqueta, obligatorio=obligatorio)
        for clave, etiqueta, obligatorio, _sinonimos in CAMPOS[tipo]
    ]


def _salida(importacion: Importacion) -> ImportacionSalida:
    return ImportacionSalida(
        id=importacion.id,
        tipo=importacion.tipo,
        etiqueta_tipo=ETIQUETAS_TIPO.get(importacion.tipo, importacion.tipo),
        archivo=importacion.archivo,
        hoja=importacion.hoja,
        estado=importacion.estado,
        filas_totales=importacion.filas_totales,
        filas_ok=importacion.filas_ok,
        filas_error=importacion.filas_error,
        resumen=importacion.resumen,
        usuario_nombre=importacion.usuario_nombre,
        creado_en=importacion.creado_en,
        aplicada_en=importacion.aplicada_en,
        revertida_en=importacion.revertida_en,
        revertida_por=importacion.revertida_por,
    )


def _importacion_de(db: Session, ctx: Contexto, importacion_id: int) -> Importacion:
    importacion = db.get(Importacion, importacion_id)
    cuenta = cuenta_filtro(ctx)
    if importacion is None or (cuenta is not None and importacion.cuenta_id != cuenta):
        raise no_encontrado("Esa importacion no existe")
    return importacion


@router.get("/tipos", response_model=list[TipoInfo], summary="Que se puede importar")
def tipos(ctx: Contexto = Depends(requiere("importacion", "ver"))):
    return [
        TipoInfo(clave=clave, etiqueta=ETIQUETAS_TIPO[clave], campos=_campos(clave)) for clave in TIPOS_IMPORTACION
    ]


@router.get("/plantillas", response_model=list[PlantillaSalida], summary="Plantillas guardadas")
def listar_plantillas(
    tipo: str | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("importacion", "ver")),
):
    consulta = select(PlantillaImportacion).where(PlantillaImportacion.cuenta_id == cuenta_filtro(ctx))
    if tipo:
        consulta = consulta.where(PlantillaImportacion.tipo == tipo)
    return db.scalars(consulta.order_by(PlantillaImportacion.nombre)).all()


@router.post("/plantillas", response_model=PlantillaSalida, status_code=201, summary="Guardar el emparejamiento")
def crear_plantilla(
    datos: PlantillaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("importacion", "crear")),
):
    if datos.tipo not in TIPOS_IMPORTACION:
        raise datos_invalidos("Ese tipo de importacion no existe")

    cuenta_id = cuenta_objetivo(ctx, None)
    if db.scalars(
        select(PlantillaImportacion.id).where(
            PlantillaImportacion.cuenta_id == cuenta_id,
            PlantillaImportacion.tipo == datos.tipo,
            PlantillaImportacion.nombre == datos.nombre,
        )
    ).first():
        raise conflicto("Ya existe una plantilla con ese nombre")

    plantilla = PlantillaImportacion(
        cuenta_id=cuenta_id,
        tipo=datos.tipo,
        nombre=datos.nombre,
        mapeo=datos.mapeo,
        usuario_nombre=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(plantilla)
    db.flush()
    registrar(db, ctx, "crear", "plantillas_importacion", plantilla.id, f"Guardo la plantilla {plantilla.nombre}")
    db.commit()
    db.refresh(plantilla)
    return plantilla


@router.delete("/plantillas/{plantilla_id}", response_model=Mensaje, summary="Borrar una plantilla")
def borrar_plantilla(
    plantilla_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("importacion", "borrar")),
):
    plantilla = db.get(PlantillaImportacion, plantilla_id)
    if plantilla is None or plantilla.cuenta_id != cuenta_filtro(ctx):
        raise no_encontrado("La plantilla no existe")
    db.delete(plantilla)
    db.commit()
    return Mensaje(mensaje="Plantilla borrada")


@router.post("/analizar", response_model=AnalisisSalida, status_code=201, summary="Leer el archivo")
async def analizar(
    tipo: str = Form(...),
    archivo: UploadFile = File(...),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("importacion", "crear", con_finca=True)),
):
    if tipo not in TIPOS_IMPORTACION:
        raise datos_invalidos("Ese tipo de importacion no existe")

    contenido = await archivo.read()
    if len(contenido) > MAX_BYTES:
        raise datos_invalidos("El archivo pesa mas de 5 MB. Divide la informacion en varios archivos.")

    try:
        hoja, columnas, filas = leer_archivo(contenido, archivo.filename or "archivo")
    except ValueError as error:
        raise datos_invalidos(str(error)) from error
    except Exception as error:  # noqa: BLE001 - archivo dañado o formato raro
        raise datos_invalidos("No se pudo leer el archivo. Revisa que sea un Excel o un CSV valido.") from error

    if not filas:
        raise datos_invalidos("El archivo no tiene filas con datos")

    importacion = Importacion(
        cuenta_id=cuenta_objetivo(ctx, None),
        finca_id=ctx.finca_id,
        tipo=tipo,
        archivo=(archivo.filename or "archivo")[:200],
        hoja=hoja,
        estado="pendiente",
        columnas=columnas,
        filas_totales=len(filas),
        usuario_id=ctx.usuario.id,
        usuario_nombre=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(importacion)
    db.flush()

    for numero, datos_fila in enumerate(filas, start=1):
        db.add(FilaImportacion(importacion_id=importacion.id, numero=numero, datos=datos_fila, estado="pendiente"))

    plantillas = db.scalars(
        select(PlantillaImportacion).where(
            PlantillaImportacion.cuenta_id == importacion.cuenta_id, PlantillaImportacion.tipo == tipo
        )
    ).all()

    registrar(
        db, ctx, "crear", "importaciones", importacion.id,
        f"Subio el archivo {importacion.archivo} ({len(filas)} filas)",
    )
    db.commit()

    return AnalisisSalida(
        id=importacion.id,
        tipo=tipo,
        etiqueta_tipo=ETIQUETAS_TIPO[tipo],
        archivo=importacion.archivo,
        hoja=hoja,
        columnas=columnas,
        filas_totales=len(filas),
        vista_previa=filas[:8],
        mapeo_sugerido=sugerir_mapeo(tipo, columnas),
        campos=_campos(tipo),
        plantillas=[PlantillaSalida.model_validate(p) for p in plantillas],
    )


def _preparar(db: Session, importacion: Importacion, mapeo: dict[str, str]):
    """Devuelve (filas validas, errores) sin tocar nada todavia."""
    filas = db.scalars(
        select(FilaImportacion)
        .where(FilaImportacion.importacion_id == importacion.id)
        .order_by(FilaImportacion.numero)
    ).all()

    validas: list[tuple[FilaImportacion, dict]] = []
    errores: list[ErrorFila] = []

    for fila in filas:
        valores = aplicar_mapeo(importacion.tipo, mapeo, fila.datos)
        try:
            limpio = validar_fila(importacion.tipo, valores)
        except ValueError as error:
            fila.estado, fila.error = "error", str(error)[:255]
            errores.append(ErrorFila(numero=fila.numero, error=str(error)))
            continue
        fila.estado, fila.error = "ok", None
        validas.append((fila, limpio))

    return validas, errores


def _revisar_obligatorios(tipo: str, mapeo: dict[str, str]) -> None:
    faltan = [
        etiqueta for clave, etiqueta, obligatorio, _s in CAMPOS[tipo] if obligatorio and not mapeo.get(clave)
    ]
    if faltan:
        raise datos_invalidos(f"Falta indicar que columna corresponde a: {', '.join(faltan)}")


@router.post("/{importacion_id}/validar", response_model=ValidacionSalida, summary="Revisar antes de guardar")
def validar(
    importacion_id: int,
    datos: MapeoEntrada,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("importacion", "crear")),
):
    importacion = _importacion_de(db, ctx, importacion_id)
    if importacion.estado != "pendiente":
        raise datos_invalidos("Esa importacion ya fue aplicada")

    _revisar_obligatorios(importacion.tipo, datos.mapeo)
    validas, errores = _preparar(db, importacion, datos.mapeo)

    importacion.mapeo = datos.mapeo
    importacion.opciones = datos.opciones
    importacion.filas_ok = len(validas)
    importacion.filas_error = len(errores)
    db.commit()

    return ValidacionSalida(
        filas_totales=importacion.filas_totales,
        filas_ok=len(validas),
        filas_error=len(errores),
        errores=errores[:50],
        vista_previa=[
            {clave: (valor.isoformat() if hasattr(valor, "isoformat") else float(valor) if hasattr(valor, "quantize") else valor)
             for clave, valor in valores.items() if not clave.startswith("_")}
            for _fila, valores in validas[:8]
        ],
    )


@router.post("/{importacion_id}/aplicar", response_model=ImportacionSalida, summary="Guardar los datos")
def aplicar(
    importacion_id: int,
    datos: MapeoEntrada,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("importacion", "crear")),
):
    importacion = _importacion_de(db, ctx, importacion_id)
    if importacion.estado != "pendiente":
        raise datos_invalidos("Esa importacion ya fue aplicada")

    _revisar_obligatorios(importacion.tipo, datos.mapeo)
    validas, errores = _preparar(db, importacion, datos.mapeo)
    if not validas:
        raise datos_invalidos("Ninguna fila quedo lista para guardar. Revisa el emparejamiento de columnas.")

    resumen = aplicar_datos(db, ctx, importacion, validas, datos.opciones or {})

    importacion.mapeo = datos.mapeo
    importacion.opciones = datos.opciones
    importacion.estado = "aplicada"
    importacion.aplicada_en = ahora()
    importacion.filas_ok = int(resumen.get("creados", 0))
    importacion.filas_error = len(errores) + int(resumen.get("omitidos", 0))
    importacion.resumen = resumen

    registrar(
        db, ctx, "importar", "importaciones", importacion.id,
        f"Importo {resumen.get('creados', 0)} registro(s) de {importacion.archivo}",
        resumen,
    )
    db.commit()
    db.refresh(importacion)
    return _salida(importacion)


@router.post("/{importacion_id}/revertir", response_model=ImportacionSalida, summary="Deshacer una importacion")
def revertir(
    importacion_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("importacion", "editar")),
):
    importacion = _importacion_de(db, ctx, importacion_id)
    if importacion.estado != "aplicada":
        raise datos_invalidos("Solo se puede deshacer una importacion que ya fue aplicada")

    resumen = revertir_datos(db, ctx, importacion)
    importacion.estado = "revertida"
    importacion.revertida_en = ahora()
    importacion.revertida_por = ctx.usuario.nombre_completo
    importacion.resumen = {**(importacion.resumen or {}), "reversion": resumen}

    registrar(
        db, ctx, "revertir", "importaciones", importacion.id,
        f"Deshizo la importacion de {importacion.archivo}", resumen,
    )
    db.commit()
    db.refresh(importacion)
    return _salida(importacion)


@router.get("", response_model=list[ImportacionSalida], summary="Historial de importaciones")
def historial(
    limite: int = Query(30, ge=1, le=200),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("importacion", "ver")),
):
    consulta = select(Importacion)
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(Importacion.cuenta_id == cuenta)
    filas = db.scalars(consulta.order_by(Importacion.id.desc()).limit(limite)).all()
    return [_salida(i) for i in filas]


@router.get("/{importacion_id}", response_model=ImportacionDetalle, summary="Ver una importacion")
def ver(
    importacion_id: int,
    solo_errores: bool = Query(False),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("importacion", "ver")),
):
    importacion = _importacion_de(db, ctx, importacion_id)
    consulta = select(FilaImportacion).where(FilaImportacion.importacion_id == importacion.id)
    if solo_errores:
        consulta = consulta.where(FilaImportacion.estado == "error")

    filas = db.scalars(consulta.order_by(FilaImportacion.numero).limit(200)).all()
    base = _salida(importacion)
    return ImportacionDetalle(
        **base.model_dump(),
        columnas=importacion.columnas or [],
        mapeo=importacion.mapeo,
        filas=[DetalleFila(numero=f.numero, estado=f.estado, error=f.error, datos=f.datos) for f in filas],
    )
