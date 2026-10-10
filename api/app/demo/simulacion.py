"""La simulacion completa, armada con las partes de cada area."""

from __future__ import annotations

import random
from datetime import datetime, time, timedelta

from freezegun import freeze_time
from sqlalchemy import select

from app.modelos.aves import Lote
from app.modelos.organizacion import Cuenta
from app.modelos.trabajo import Tarea
from app.demo.datos import log, NOMBRE_CUENTA, DESFASE
from app.demo.base import DemoBase
from app.demo.estructura import EstructuraMixin
from app.demo.granja import GranjaMixin
from app.demo.tienda import TiendaMixin
from app.demo.trabajo import TrabajoMixin
from app.demo.sensores import SensoresMixin


def demo_cargada() -> bool:
    """Si la cuenta de ejemplo ya existe en la base."""
    from app.core.db import SesionLocal

    with SesionLocal() as db:
        return db.scalars(select(Cuenta.id).where(Cuenta.nombre == NOMBRE_CUENTA)).first() is not None


class Demo(EstructuraMixin, GranjaMixin, TiendaMixin, TrabajoMixin, SensoresMixin, DemoBase):
    """La granja completa: arma la estructura y simula cada dia del periodo."""

    # ------------------------------------------------------------ todo junto
    def correr(self) -> None:
        random.seed(2026)
        self.subida_precio = None
        existente = self.db.scalars(select(Cuenta.id).where(Cuenta.nombre == NOMBRE_CUENTA)).first()
        if existente:
            raise SystemExit(
                f"Ya existe la cuenta '{NOMBRE_CUENTA}'. Los datos de ejemplo se cargan una sola vez; "
                "para empezar de cero borra la base de datos."
            )
        self.crear_estructura()
        self.plan_novedades = self.novedades()
        pendientes: list = []

        congelador = freeze_time(datetime.combine(self.inicio, time(6)) + DESFASE, tick=False)
        self.reloj = congelador.start()
        try:
            self.arrancar()
            dia = self.inicio
            while dia <= self.hoy:
                numero = (dia - self.inicio).days
                if numero and numero % 15 == 0:
                    log.info("Dia %s de %s (%s)", numero, (self.hoy - self.inicio).days, dia.isoformat())
                if numero == (self.hoy - self.inicio).days // 2:
                    self.subir_precios(dia)
                self.tareas_del_dia(dia)
                if dia.weekday() == 0:
                    self.alimento_semanal(dia)
                for lote_id in self.lotes_activos():
                    lote = self.db.get(Lote, lote_id)
                    finca = self.esperanza if lote.finca_id == self.esperanza.id else self.recreo
                    usuario = self.luis if finca.id == self.esperanza.id else self.yuliana
                    self.alimentar(dia, lote_id, usuario, finca)
                    self.mortalidad(dia, lote_id, usuario, finca)
                self.sanidad_ponedoras(dia)
                self.engorde(dia)
                self.descarte(dia)
                self.tarea_suelta(dia)
                self.registrar_novedades(dia, pendientes)
                self.jornada_tienda(dia)
                for lote_id in (self.po1, self.po2, self.po3, self.po4):
                    lote = self.db.get(Lote, lote_id)
                    if lote.estado == "activo":
                        self.recoleccion(dia, lote_id)
                self.inventario_rutina(dia)
                self.cerrar_tareas(dia)
                dia += timedelta(days=1)
        finally:
            congelador.stop()

        # Tareas de dias pasados creadas a mano que nadie cerro: se marcan hechas
        viejas = self.db.scalars(
            select(Tarea).where(Tarea.cuenta_id == self.cuenta.id, Tarea.fecha < self.hoy - timedelta(days=1),
                                Tarea.estado.in_(("pendiente", "en_proceso")))
        ).all()
        for tarea in viejas:
            tarea.estado = "hecha"
            tarea.terminada_por = tarea.asignado_nombre
            tarea.terminada_en = datetime.combine(tarea.fecha, time(17)) + DESFASE
        # Ultimo ingreso de cada usuario
        for usuario in (self.carlos, self.diana, self.jorge, self.luis, self.andres, self.yuliana, self.paola):
            usuario.ultimo_ingreso = datetime.utcnow() - timedelta(hours=random.randint(1, 30))
        self.db.commit()

        log.info("Guardando mediciones de los sensores...")
        self.lecturas()
