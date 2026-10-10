"""Mediciones de los sensores."""

from __future__ import annotations

import math
import random
from datetime import datetime, time, timedelta

from app.modelos.sensores import LecturaSensor, Sensor, TipoSensor
from app.rutas.sensores import estado_de
from app.demo.datos import DESFASE
from app.demo.base import DemoBase


class SensoresMixin:
    """Mediciones de los sensores."""

    # ------------------------------------------------------------ sensores
    def lecturas(self) -> int:
        """Una medicion cada 30 minutos de los ultimos 20 dias y cada 3 horas de antes."""
        filas = []
        creado = datetime.utcnow()
        limite_detalle = self.hoy - timedelta(days=20)
        silo = 3200.0
        momento = datetime.combine(self.inicio, time(0))
        while momento <= self.ahora_local:
            paso = timedelta(minutes=30) if momento.date() >= limite_detalle else timedelta(hours=3)
            hora = momento.hour + momento.minute / 60
            dia = momento.date()
            # Clima de montana: minima al amanecer, maxima a las 2 de la tarde
            onda = math.sin((hora - 8) / 24 * 2 * math.pi)
            calor = 2.6 if self.calor(dia) else 0
            estacion = 1.2 * math.sin((dia.toordinal() % 365) / 365 * 2 * math.pi)
            ruido = random.gauss(0, 0.5)
            t_base = 21.5 + 4.2 * onda + estacion + ruido
            valores = {
                "t1": t_base + calor * max(onda, 0),
                "t2": t_base + 0.9 + (calor + 0.8) * max(onda, 0),
                "t3": t_base - 0.3 + calor * max(onda, 0),
                "h1": 68 - 12 * onda + random.gauss(0, 2.5),
                "h2": 66 - 12 * onda + random.gauss(0, 2.5),
                "a1": 9 + 4 * math.sin(dia.toordinal() / 5) + (7 if (dia.toordinal() % 29) in (0, 1) else 0) + random.gauss(0, 1.2),
                "te1": 27 + 3.5 * onda + ruido,
                "he1": 64 - 10 * onda + random.gauss(0, 2.5),
            }
            # Silo: baja con el consumo y se llena los lunes
            if momento.weekday() == 0 and momento.hour == 9 and momento.minute == 0:
                silo = 3900.0
            silo = max(150.0, silo - (340 / 24) * paso.total_seconds() / 3600 * random.uniform(0.8, 1.2))
            valores["silo"] = silo
            # Ultima lectura del galpon 2: se esta calentando ahora
            if momento + paso > self.ahora_local:
                valores["t2"] = max(valores["t2"], 29.4)
            for clave, valor in valores.items():
                sensor = self.sensores[clave]
                if clave == "te1" and not self.hay_pollo(dia):
                    continue
                valor = round(valor, 1 if clave != "silo" else 0)
                minimo = float(sensor.min_ok) if sensor.min_ok is not None else sensor_tipo_min(self, sensor)
                maximo = float(sensor.max_ok) if sensor.max_ok is not None else sensor_tipo_max(self, sensor)
                filas.append(LecturaSensor(
                    sensor_id=sensor.id, valor=valor, medido_en=momento + DESFASE,
                    fuera_rango=estado_de(valor, minimo, maximo) != "ok", origen="dispositivo", creado_en=creado,
                ))
            if len(filas) > 5000:
                self.db.add_all(filas)
                self.db.commit()
                self.cuentas["lecturas"] += len(filas)
                filas = []
            momento += paso
        self.db.add_all(filas)
        self.db.commit()
        self.cuentas["lecturas"] += len(filas)
        return self.cuentas["lecturas"]


def sensor_tipo_min(demo: DemoBase, sensor: Sensor) -> float | None:
    tipo = demo.db.get(TipoSensor, sensor.tipo_id)
    return float(tipo.min_ok) if tipo.min_ok is not None else None


def sensor_tipo_max(demo: DemoBase, sensor: Sensor) -> float | None:
    tipo = demo.db.get(TipoSensor, sensor.tipo_id)
    return float(tipo.max_ok) if tipo.max_ok is not None else None
