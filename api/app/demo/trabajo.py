"""Rutinas, tareas, novedades e inventario de rutina."""

from __future__ import annotations

import random
from datetime import timedelta

from sqlalchemy import select

from app.esquemas.inventario import ItemEntrada, MovimientoCrear
from app.esquemas.trabajo import (
    CerrarNovedad,
    GenerarTareas,
    NovedadCrear,
    RutinaCrear,
    TareaActualizar,
    TareaCrear,
)
from app.modelos.acceso import Usuario
from app.modelos.aves import Lote
from app.modelos.trabajo import Tarea
from app.rutas import movimientos as r_mov
from app.rutas import trabajo as r_tra


class TrabajoMixin:
    """Rutinas, tareas, novedades e inventario de rutina."""

    TAREAS_SUELTAS = [
        ("Reparar malla lateral del galpon 2", "alta", "g2", "andres"),
        ("Cambiar bombillos fundidos del galpon 1", "media", "g1", "luis"),
        ("Revisar fuga en el tanque de agua", "alta", None, "luis"),
        ("Pintar comederos del galpon de levante", "baja", "g4", "andres"),
        ("Cambiar viruta humeda cerca a los bebederos", "media", "g1", "luis"),
        ("Arreglar puerta de la bodega", "baja", None, "andres"),
        ("Limpiar canales del techo", "media", None, "luis"),
        ("Revisar criadoras a gas", "alta", "g4", "andres"),
        ("Fumigar contra moscas alrededor de los galpones", "media", None, "luis"),
        ("Organizar cubetas en la bodega", "baja", None, "andres"),
        ("Rozar el pasto alrededor de los galpones", "baja", None, "luis"),
        ("Ajustar altura de comederos", "media", "g3", "andres"),
    ]

    # ------------------------------------------------------------ tareas y rutinas
    def rutinas(self, dia) -> None:
        ctx_esp = self.ctx(self.jorge, self.esperanza)
        ctx_rec = self.ctx(self.jorge, self.recreo)
        lista = [
            (ctx_esp, "Suministrar alimento a los galpones", "diaria", [], None, "06:00", "alta", self.luis, None),
            (ctx_esp, "Recoger huevos (manana)", "diaria", [], None, "09:00", "alta", self.luis, None),
            (ctx_esp, "Recoger huevos (tarde)", "diaria", [], None, "14:30", "alta", self.andres, None),
            (ctx_esp, "Clasificar y empacar huevo", "diaria", [], None, "15:30", "media", self.andres, None),
            (ctx_esp, "Revisar temperatura y manejo de cortinas", "diaria", [], None, "12:00", "media", self.jorge, None),
            (ctx_esp, "Lavar bebederos", "semanal", [0, 3], None, "10:00", "media", self.andres, None),
            (ctx_esp, "Remover cama y agregar cal", "semanal", [4], None, "11:00", "baja", self.luis, None),
            (ctx_esp, "Desinfeccion general de galpones", "mensual", [], 1, "09:00", "media", self.jorge, None),
            (ctx_esp, "Conteo fisico de bodega", "mensual", [], 28, "16:00", "media", self.jorge, None),
            (ctx_rec, "Alimentar y revisar pollos", "diaria", [], None, "06:30", "alta", self.yuliana, None),
            (ctx_rec, "Revisar bebederos y camas de engorde", "diaria", [], None, "13:00", "media", self.yuliana, None),
        ]
        for ctx, titulo, frecuencia, dias_semana, dia_mes, hora, prioridad, usuario, galpon_ in lista:
            self.hacer("rutina", r_tra.crear_rutina, RutinaCrear(
                titulo=titulo, frecuencia=frecuencia, dias_semana=dias_semana, dia_mes=dia_mes, hora=hora,
                prioridad=prioridad, asignado_a=usuario.id, galpon_id=galpon_.id if galpon_ else None,
            ), ctx=ctx)

    def tareas_del_dia(self, dia) -> None:
        for finca in (self.esperanza, self.recreo):
            if self.a_las(dia, 5, 55):
                self.hacer("generar", r_tra.generar, GenerarTareas(fecha=dia), ctx=self.ctx(self.jorge, finca))

    def cerrar_tareas(self, dia) -> None:
        """Al final del dia cada quien marca lo que hizo."""
        tareas = self.db.scalars(
            select(Tarea).where(Tarea.cuenta_id == self.cuenta.id, Tarea.fecha == dia, Tarea.estado.in_(("pendiente", "en_proceso")))
        ).all()
        faltan = (self.hoy - dia).days
        normales = [t for t in tareas if t.prioridad != "alta"]
        sin_hacer = {t.id for t in random.sample(normales, k=min(2, len(normales)))} if faltan == 1 else set()
        for tarea in tareas:
            hora, minuto = (int(x) for x in (tarea.hora or "10:00").split(":"))
            hora_fin = min(18, hora + random.choice([0, 1, 1, 2]))
            azar = random.random()
            if tarea.id in sin_hacer:
                continue  # ayer quedaron un par sin hacer: aparecen como atrasadas
            if faltan == 0:
                if not self.a_las(dia, hora_fin, random.randint(0, 59)):
                    continue
            elif not self.a_las(dia, hora_fin, random.randint(0, 59)):
                continue
            usuario = self.db.get(Usuario, tarea.asignado_a) if tarea.asignado_a else self.jorge
            finca = self.esperanza if tarea.finca_id == self.esperanza.id else self.recreo
            if azar < 0.03:
                self.hacer("tarea", r_tra.editar_tarea, tarea.id, TareaActualizar(
                    estado="cancelada", notas=random.choice(["Llovio todo el dia", "Se paso para manana", "No habia insumo"])),
                    ctx=self.ctx(self.jorge, finca))
            else:
                nota = random.choice([None] * 8 + ["Sin novedad", "Todo en orden", "Se reviso tambien el tanque"])
                self.hacer("tarea", r_tra.editar_tarea, tarea.id, TareaActualizar(estado="hecha", notas=nota), ctx=self.ctx(usuario, finca))

    def tarea_suelta(self, dia) -> None:
        if random.random() > 0.3 or not self.a_las(dia, 7, random.randint(0, 50)):
            return
        titulo, prioridad, galpon_, quien = random.choice(self.TAREAS_SUELTAS)
        usuario = self.luis if quien == "luis" else self.andres
        galpon_obj = getattr(self, galpon_) if galpon_ else None
        para = dia + timedelta(days=random.choice([0, 1, 1, 2, 3]))
        tarea = self.hacer("tarea", r_tra.crear_tarea, TareaCrear(
            titulo=titulo, fecha=para, hora=random.choice(["08:00", "10:00", "14:00", None]), prioridad=prioridad,
            asignado_a=usuario.id, galpon_id=galpon_obj.id if galpon_obj else None,
            descripcion=random.choice([None, "Llevar la herramienta de la bodega", "Avisar cuando quede listo"]),
        ), ctx=self.ctx(self.jorge, self.esperanza))
        self.cuentas["tareas_sueltas"] += 1 if tarea else 0

    # ------------------------------------------------------------ novedades
    def novedades(self) -> dict[int, list[dict]]:
        n = {}

        def agregar(dia, **datos):
            n.setdefault(dia, []).append(datos)

        agregar(9, categoria="servicios", subtipo="Corte de energia", titulo="Corte de luz de 5 horas en la vereda",
                gravedad="media", galpon="g1", costo=0, acciones="Se prendio la planta electrica para las bombas de agua", cerrar=0)
        agregar(17, categoria="animales", subtipo="Zarigueya", titulo="Zarigueya entro al galpon 3 de noche",
                gravedad="alta", galpon="g3", lote="po3", aves=9, costo=0, acciones="Se reforzo la malla y se puso trampa", cerrar=2)
        agregar(26, categoria="infraestructura", subtipo="Bebederos", titulo="Bebedero de campana roto en el galpon 2",
                gravedad="baja", galpon="g2", costo=38000, acciones="Se cambio por uno nuevo de la bodega", cerrar=1)
        agregar(33, categoria="clima", subtipo="Lluvia fuerte", titulo="Aguacero con granizo, se mojo la cama del galpon 1",
                gravedad="media", galpon="g1", costo=120000, acciones="Se cambio la viruta mojada y se reviso el techo", cerrar=3)
        agregar(41, categoria="salud", subtipo="Respiratorio", titulo="Aves con estornudos en el galpon 2",
                gravedad="alta", galpon="g2", lote="po2", costo=250000,
                acciones="Visita del veterinario, tratamiento con enrofloxacina 5 dias", cerrar=6, tratamiento="po2")
        agregar(55, categoria="seguridad", subtipo="Robo", titulo="Faltaron 4 panales de huevo de la bodega",
                gravedad="media", costo=66000, acciones="Se puso candado nuevo y se revisan las llaves", cerrar=4)
        agregar(63, categoria="servicios", subtipo="Agua", titulo="Falla de la bomba de agua",
                gravedad="alta", costo=380000, acciones="Se reparo el motor de la bomba", cerrar=1)
        agregar(78, categoria="animales", subtipo="Ratas", titulo="Presencia de ratas en la bodega de alimento",
                gravedad="media", costo=45000, acciones="Se pusieron cebos y se sellaron huecos", cerrar=7)
        agregar(90, categoria="clima", subtipo="Calor", titulo="Dia muy caluroso, jadeo en el galpon 2",
                gravedad="media", galpon="g2", lote="po2", aves=6, costo=0, acciones="Se abrieron cortinas y se dieron electrolitos", cerrar=1)
        agregar(97, categoria="infraestructura", subtipo="Techo", titulo="Teja rota en el galpon de levante",
                gravedad="media", galpon="g4", costo=85000, acciones="Se cambiaron dos tejas", cerrar=2)
        agregar(118, categoria="salud", subtipo="Picaje", titulo="Picaje en pollitas del galpon de levante",
                gravedad="media", galpon="g4", lote="po4", aves=4, costo=0, acciones="Se bajo la intensidad de luz", cerrar=5)
        agregar(131, categoria="servicios", subtipo="Corte de energia", titulo="Se quemo el transformador de la finca",
                gravedad="alta", costo=950000, acciones="La empresa de energia cambio el transformador", cerrar=3)
        agregar(146, categoria="infraestructura", subtipo="Cortinas", titulo="Cortina del galpon 3 rasgada por el viento",
                gravedad="baja", galpon="g3", costo=160000, acciones="Se cosio y se cambio el tramo roto", cerrar=4)
        agregar(158, categoria="animales", subtipo="Perros", titulo="Perros de la vereda rondando los galpones",
                gravedad="baja", costo=0, acciones="Se hablo con los vecinos", cerrar=2)
        agregar(167, categoria="infraestructura", subtipo="Techo", titulo="Goteras en el techo del galpon 2",
                gravedad="alta", galpon="g2", costo=300000, acciones=None, cerrar=None)
        agregar(174, categoria="clima", subtipo="Lluvia fuerte", titulo="Barro en la entrada, el camion de alimento no pudo subir",
                gravedad="media", costo=0, acciones=None, cerrar=None)
        agregar(178, categoria="salud", subtipo="Diarrea", titulo="Heces liquidas en algunas aves del galpon 1",
                gravedad="media", galpon="g1", lote="po1", costo=0, acciones=None, cerrar=None)
        return n

    def registrar_novedades(self, dia, pendientes: list) -> None:
        dias = (dia - self.inicio).days
        for datos in self.plan_novedades.get(dias, []):
            if not self.a_las(dia, random.randint(7, 11), random.randint(0, 59)):
                continue
            galpon_ = getattr(self, datos["galpon"]) if datos.get("galpon") else None
            lote_id = getattr(self, datos["lote"]) if datos.get("lote") else None
            if lote_id:
                lote = self.db.get(Lote, lote_id)
                if lote.estado != "activo":
                    lote_id = None
            quien = random.choice([self.jorge, self.luis, self.andres])
            novedad = self.hacer("novedad", r_tra.crear_novedad, NovedadCrear(
                fecha=dia, categoria=datos["categoria"], subtipo=datos["subtipo"], titulo=datos["titulo"],
                gravedad=datos["gravedad"], galpon_id=galpon_.id if galpon_ else None, lote_id=lote_id,
                aves_afectadas=datos.get("aves", 0) if lote_id else 0, descontar_aves=bool(datos.get("aves")) and bool(lote_id),
                costo_estimado=datos["costo"], descripcion="Reportado por " + quien.nombres,
            ), ctx=self.ctx(quien, self.esperanza))
            if novedad and datos.get("cerrar") is not None:
                pendientes.append((dia + timedelta(days=datos["cerrar"]), novedad.id, datos["acciones"]))
            if novedad and datos.get("tratamiento"):
                self.vacuna(dia, getattr(self, datos["tratamiento"]), self.esperanza, self.a_antibiotico,
                            "Enrofloxacina 10%", "agua", tipo="medicamento", dosis="1 ml por litro, 5 dias", cantidad=3)
        for pendiente in [p for p in pendientes if p[0] == dia]:
            if self.a_las(dia, 16, random.randint(0, 59)):
                self.hacer("novedad", r_tra.cerrar_novedad, pendiente[1], CerrarNovedad(acciones=pendiente[2]),
                           ctx=self.ctx(self.jorge, self.esperanza))
            pendientes.remove(pendiente)

    # ------------------------------------------------------------ inventario de rutina
    def inventario_rutina(self, dia) -> None:
        dias = (dia - self.inicio).days
        # Cada sabado se sacan las cubetas usadas
        if dia.weekday() == 5 and self.a_las(dia, 17, 55):
            usadas = random.randint(900, 1300)
            usadas = min(usadas, int(self.existencia(self.b_esp, self.a_cubetas)))
            if usadas > 0:
                self.hacer("salida", r_mov.crear, MovimientoCrear(
                    tipo="salida", fecha=dia, bodega_id=self.b_esp.id, motivo="Empaque de huevo",
                    items=[ItemEntrada(articulo_id=self.a_cubetas.id, cantidad=usadas)],
                ), ctx=self.ctx(self.jorge, self.esperanza))
        if dia.weekday() == 0 and self.existencia(self.b_esp, self.a_cubetas) < 1600:
            self.compra(dia, self.b_esp, self.empaques, [(self.a_cubetas, 3000)], hora=10)
        # Cal y viruta de los jueves
        if dia.weekday() == 4:
            self.asegurar(dia, self.b_esp, self.a_cal, 25)
            if self.a_las(dia, 11, 30):
                self.hacer("salida", r_mov.crear, MovimientoCrear(
                    tipo="salida", fecha=dia, bodega_id=self.b_esp.id, motivo="Consumo en galpones",
                    observaciones="Cal para la cama", items=[ItemEntrada(articulo_id=self.a_cal.id, cantidad=25)],
                ), ctx=self.ctx(self.luis, self.esperanza))
        # Conteo de fin de mes (dia 28): pequenas diferencias
        if dia.day == 28 and self.a_las(dia, 16, 40):
            items = []
            for articulo in (self.a_cubetas, self.a_cal, self.a_postura):
                actual = self.existencia(self.b_esp, articulo)
                contado = max(0, round(actual + random.choice([-1, -1, 0, 1]) * random.uniform(0, 0.004) * actual))
                items.append(ItemEntrada(articulo_id=articulo.id, cantidad=contado))
            self.hacer("ajuste", r_mov.crear, MovimientoCrear(
                tipo="ajuste", fecha=dia, bodega_id=self.b_esp.id, motivo="Conteo fisico de fin de mes", items=items,
            ), ctx=self.ctx(self.jorge, self.esperanza))
        # Viruta nueva para las ponedoras cada mes
        if dia.day == 3:
            self.asegurar(dia, self.b_esp, self.a_viruta, 18)
            if self.a_las(dia, 11, 10):
                self.hacer("salida", r_mov.crear, MovimientoCrear(
                    tipo="salida", fecha=dia, bodega_id=self.b_esp.id, motivo="Consumo en galpones",
                    observaciones="Cambio de cama en nidos y zonas humedas", items=[ItemEntrada(articulo_id=self.a_viruta.id, cantidad=18)],
                ), ctx=self.ctx(self.luis, self.esperanza))
        # Bombillos que se funden
        if dias % 23 == 11:
            self.asegurar(dia, self.b_esp, self.a_bombillo, 2)
            if self.a_las(dia, 14, 20):
                self.hacer("salida", r_mov.crear, MovimientoCrear(
                    tipo="salida", fecha=dia, bodega_id=self.b_esp.id, motivo="Reposicion",
                    observaciones="Cambio de bombillos fundidos", items=[ItemEntrada(articulo_id=self.a_bombillo.id, cantidad=2)],
                ), ctx=self.ctx(self.luis, self.esperanza))
