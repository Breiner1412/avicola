"""Lo comun: sesion, reloj simulado, contexto y llamadas a la API."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException

from app.core.contexto import Contexto
from app.core.db import SesionLocal
from app.modelos.acceso import Usuario
from app.modelos.inventario import Articulo, Bodega, Existencia
from app.modelos.organizacion import Finca
from app.demo.datos import log, DESFASE


class DemoBase:
    """Lo comun: sesion, reloj simulado, contexto y llamadas a la API."""

    def __init__(self, dias: int):
        self.db = SesionLocal()
        ahora_real = datetime.utcnow() - DESFASE
        self.ahora_local = ahora_real.replace(second=0, microsecond=0)
        self.hoy = self.ahora_local.date()
        self.inicio = self.hoy - timedelta(days=dias)
        self.errores: Counter[str] = Counter()
        self.cuentas: Counter[str] = Counter()
        self.reloj = None

    # ------------------------------------------------------------ reloj
    def a_las(self, dia: date, hora: int, minuto: int = 0) -> bool:
        """Mueve el reloj del sistema a esa hora local. Devuelve False si todavia no ha llegado."""
        momento = datetime.combine(dia, time(hora, minuto))
        if momento > self.ahora_local:
            return False
        self.reloj.move_to(momento + DESFASE)
        return True

    # ------------------------------------------------------------ llamadas
    def ctx(self, usuario: Usuario, finca: Finca | None) -> Contexto:
        return Contexto(
            usuario=usuario,
            rol=usuario.rol.clave,
            cuenta_id=self.cuenta.id,
            finca_id=finca.id if finca else None,
            solo_lectura=False,
            ip="192.168.1.20",
            sesion_id=None,
            cuenta_activa_id=self.cuenta.id,
        )

    def hacer(self, que: str, funcion, *args, **kwargs):
        try:
            resultado = funcion(*args, db=self.db, **kwargs)
            self.cuentas[que] += 1
            return resultado
        except HTTPException as error:
            self.db.rollback()
            self.errores[que] += 1
            if self.errores[que] <= 3:
                log.warning("%s: %s", que, error.detail)
            return None

    def existencia(self, bodega: Bodega, articulo: Articulo) -> float:
        fila = self.db.get(Existencia, (bodega.id, articulo.id))
        return float(fila.cantidad) if fila else 0.0
