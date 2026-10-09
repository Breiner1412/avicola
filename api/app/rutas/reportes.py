"""Reportes: numeros del periodo y descarga en CSV."""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import datos_invalidos
from app.servicios import reportes

router = APIRouter(prefix="/reportes", tags=["Reportes"])

TIPOS_CSV = tuple(reportes.CSV_POR_TIPO)


@router.get("/resumen", summary="Numeros del periodo")
def resumen(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("reportes", "ver")),
):
    return reportes.resumen(reportes.periodo(db, ctx, desde, hasta))


INICIOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def _celda_segura(valor):
    """Un texto que empieza como formula (=, +, -, @) se abre en Excel como texto.

    Evita que, por ejemplo, una novedad titulada =HYPERLINK(...) se ejecute al abrir
    el reporte. Los numeros se dejan tal cual.
    """
    if isinstance(valor, str) and valor.startswith(INICIOS_DE_FORMULA):
        return "'" + valor
    return valor


def _csv(nombre: str, encabezados: list[str], filas: list[list]) -> StreamingResponse:
    memoria = io.StringIO()
    escritor = csv.writer(memoria, delimiter=";")
    escritor.writerow(encabezados)
    escritor.writerows([_celda_segura(valor) for valor in fila] for fila in filas)
    memoria.seek(0)
    # BOM para que Excel abra bien las tildes
    contenido = io.BytesIO(("﻿" + memoria.getvalue()).encode("utf-8"))
    return StreamingResponse(
        contenido,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}.csv"'},
    )


@router.get("/csv", summary="Descargar un reporte en CSV")
def descargar(
    tipo: str = Query(..., description="produccion, ventas, aves, alimento, existencias, novedades o tareas"),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("reportes", "ver")),
):
    armar = reportes.CSV_POR_TIPO.get(tipo)
    if armar is None:
        raise datos_invalidos(f"Reporte no valido. Opciones: {', '.join(TIPOS_CSV)}")
    nombre, encabezados, filas = armar(reportes.periodo(db, ctx, desde, hasta))
    return _csv(nombre, encabezados, filas)
