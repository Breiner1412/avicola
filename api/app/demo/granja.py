"""El dia a dia de las aves: alimento, mortalidad, huevos, pesajes, sanidad y lotes."""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select

from app.esquemas.aves import (
    CerrarLote,
    ConsumoCrear,
    DetalleProduccion,
    LoteCrear,
    MovimientoAvesCrear,
    PesajeCrear,
    ProduccionCrear,
    SanidadCrear,
)
from app.esquemas.inventario import ItemEntrada, MovimientoCrear
from app.esquemas.ventas import AbrirTurno, ItemVenta, PagoVenta
from app.modelos.aves import Lote
from app.modelos.inventario import Articulo, Bodega
from app.rutas import aves as r_aves
from app.rutas import movimientos as r_mov
from app.rutas import produccion as r_prod
from app.rutas import sanidad as r_san
from app.rutas import ventas as r_ven
from app.demo.datos import (
    COMERCIALES,
    COMPRADORES_POLLO,
    poisson,
    redondear,
    interpolar,
    PESO_POLLO,
    PESO_POLLITA,
    GRAMOS_POLLITA,
    postura,
    tamanos,
)


class GranjaMixin:
    """El dia a dia de las aves: alimento, mortalidad, huevos, pesajes, sanidad y lotes."""

    # ------------------------------------------------------------ inventario
    def precio(self, articulo: Articulo, dia: date) -> float:
        base = self.costos[articulo.id]
        subidas = (dia - self.inicio).days // 60
        return round(base * (1.015 ** subidas) * random.uniform(0.99, 1.01), 0 if base > 100 else 1)

    def compra(self, dia, bodega, proveedor, lineas, hora=9) -> None:
        if not self.a_las(dia, hora, random.randint(0, 50)):
            return
        items = []
        for articulo, cantidad in lineas:
            venc = dia + timedelta(days=random.randint(90, 360)) if articulo.categoria_id and articulo.unidad in ("dosis", "litro") else None
            items.append(ItemEntrada(
                articulo_id=articulo.id, cantidad=cantidad, costo_unitario=self.precio(articulo, dia),
                lote=f"L{random.randint(2400, 9800)}" if venc else None, vencimiento=venc,
            ))
        self.hacer("compra", r_mov.crear, MovimientoCrear(
            tipo="entrada", fecha=dia, bodega_id=bodega.id, proveedor_id=proveedor.id,
            documento=f"FV-{random.randint(10000, 99999)}", items=items,
        ), ctx=self.ctx(self.diana, None))

    def traslado(self, dia, origen, destino, lineas, hora=13) -> None:
        if not self.a_las(dia, hora, random.randint(0, 50)):
            return
        self.hacer("traslado", r_mov.crear, MovimientoCrear(
            tipo="traslado", fecha=dia, bodega_id=origen.id, bodega_destino_id=destino.id,
            observaciones="Envio a finca", items=[ItemEntrada(articulo_id=a.id, cantidad=c) for a, c in lineas],
        ), ctx=self.ctx(self.diana, None))

    def asegurar(self, dia, bodega, articulo, cantidad) -> None:
        """Si en la bodega de la finca no alcanza, se trae de la central (y si alli tampoco, se compra)."""
        falta = cantidad - self.existencia(bodega, articulo)
        if falta <= 0:
            return
        paso = 1000 if articulo.unidad == "dosis" else 5
        pedir = redondear(max(falta, cantidad * 3), paso)
        if self.existencia(self.central, articulo) < pedir:
            proveedor = {self.a_viruta.id: self.solla, self.a_bombillo.id: self.ferreteria,
                         self.a_bebedero.id: self.ferreteria, self.a_cubetas.id: self.empaques}.get(articulo.id, self.agrovet)
            self.compra(dia, self.central, proveedor, [(articulo, redondear(pedir * 3, paso))], hora=6)
        self.traslado(dia, self.central, bodega, [(articulo, pedir)], hora=7)

    def alimento_semanal(self, dia) -> None:
        """Cada lunes se pide el alimento de las proximas dos semanas."""
        necesidades: dict[tuple[int, int], float] = defaultdict(float)
        for lote_id in self.lotes_activos():
            lote = self.db.get(Lote, lote_id)
            articulo, kg = self.racion(lote, dia)
            bodega = self.b_esp if lote.finca_id == self.esperanza.id else self.b_rec
            necesidades[(bodega.id, articulo.id)] += kg * 15
        for (bodega_id, articulo_id), kg in necesidades.items():
            bodega = self.db.get(Bodega, bodega_id)
            articulo = self.db.get(Articulo, articulo_id)
            falta = kg - self.existencia(bodega, articulo)
            if falta > 200:
                proveedor = self.italcol if bodega.id == self.b_esp.id else self.solla
                self.compra(dia, bodega, proveedor, [(articulo, redondear(falta, 40))], hora=9)

    # ------------------------------------------------------------ aves
    def lotes_activos(self) -> list[int]:
        return list(self.db.scalars(select(Lote.id).where(Lote.cuenta_id == self.cuenta.id, Lote.estado == "activo")).all())

    def edad(self, lote: Lote, dia: date) -> int:
        return lote.edad_dias_ingreso + (dia - lote.fecha_ingreso).days

    def racion(self, lote: Lote, dia: date) -> tuple[Articulo, float]:
        edad = self.edad(lote, dia)
        aves = lote.aves_actuales + lote.aves_descarte
        if lote.proposito == "engorde":
            gramos = 22 + 4.1 * edad
            return (self.a_inicio if edad <= 21 else self.a_engorde), aves * gramos / 1000
        semana = edad // 7
        if semana < len(GRAMOS_POLLITA) and semana < 19:
            return self.a_levante, aves * GRAMOS_POLLITA[semana] / 1000
        return self.a_postura, aves * random.uniform(0.108, 0.116)

    def alimentar(self, dia, lote_id, usuario, finca) -> None:
        lote = self.db.get(Lote, lote_id)
        if lote.aves_actuales + lote.aves_descarte == 0:
            return
        articulo, kg = self.racion(lote, dia)
        kg = max(1, round(kg))
        bodega = self.b_esp if finca.id == self.esperanza.id else self.b_rec
        if self.existencia(bodega, articulo) < kg:
            proveedor = self.italcol if bodega.id == self.b_esp.id else self.solla
            self.compra(dia, bodega, proveedor, [(articulo, redondear(kg * 10, 40))], hora=6)
        if self.a_las(dia, 6, random.randint(0, 40)):
            self.hacer("alimento", r_aves.nuevo_consumo, ConsumoCrear(
                lote_id=lote_id, fecha=dia, articulo_id=articulo.id, bodega_id=bodega.id, cantidad=kg,
            ), ctx=self.ctx(usuario, finca))

    def mortalidad(self, dia, lote_id, usuario, finca) -> None:
        lote = self.db.get(Lote, lote_id)
        edad = self.edad(lote, dia)
        if lote.proposito == "engorde":
            tasa = 0.0016 if edad <= 7 else (0.0005 if edad <= 28 else 0.0009)
            motivos = ["Muerte natural", "Ascitis", "Muerte subita", "Aplastamiento", "Problema de patas"]
        elif edad < 126:
            tasa = 0.0012 if edad <= 10 else 0.00018
            motivos = ["Muerte natural", "Pollita debil", "Picaje", "Aplastamiento"]
        else:
            tasa = 0.00011 + 0.0000003 * edad
            motivos = ["Muerte natural", "Prolapso", "Picaje", "Peritonitis", "Muerte natural"]
        muertas = min(poisson(lote.aves_actuales * tasa), lote.aves_actuales)
        if muertas and self.a_las(dia, 7, random.randint(0, 50)):
            self.hacer("mortalidad", r_aves.nuevo_movimiento, MovimientoAvesCrear(
                lote_id=lote_id, fecha=dia, tipo="muerte", cantidad=muertas, motivo=random.choice(motivos),
            ), ctx=self.ctx(usuario, finca))

    def recoleccion(self, dia, lote_id) -> None:
        lote = self.db.get(Lote, lote_id)
        edad = self.edad(lote, dia)
        porcentaje = postura(edad) * random.uniform(0.975, 1.02)
        if lote.galpon_id == self.g2.id and self.calor(dia):
            porcentaje *= 0.94  # el galpon 2 se calienta y baja la postura
        huevos = int(lote.aves_actuales * porcentaje)
        if huevos <= 0:
            return
        sucios = int(huevos * random.uniform(0.01, 0.02))
        rotos = int(huevos * random.uniform(0.005, 0.009 + edad / 70000))
        buenos = huevos - sucios - rotos
        detalles = []
        repartido = 0
        for tipo, peso in zip(COMERCIALES, tamanos(edad)):
            cantidad = int(buenos * peso * random.uniform(0.93, 1.07))
            repartido += cantidad
            detalles.append((tipo, cantidad))
        detalles[2] = ("AA", detalles[2][1] + buenos - repartido)
        detalles += [("Sucio", sucios), ("Roto", rotos)]
        usuario = random.choice([self.luis, self.andres])
        if self.a_las(dia, 15, random.randint(10, 55)):
            self.hacer("produccion", r_prod.registrar_produccion, ProduccionCrear(
                lote_id=lote_id, fecha=dia,
                detalles=[DetalleProduccion(tipo_huevo_id=self.tipos[t], cantidad=max(0, c)) for t, c in detalles],
            ), ctx=self.ctx(usuario, self.esperanza))

    def pesaje(self, dia, lote_id, usuario, finca, muestra) -> None:
        lote = self.db.get(Lote, lote_id)
        edad = self.edad(lote, dia)
        if lote.proposito == "engorde":
            promedio = interpolar(PESO_POLLO, edad)
        else:
            promedio = interpolar(PESO_POLLITA, edad / 7)
        total = round(muestra * promedio * random.uniform(0.96, 1.04), 2)
        if self.a_las(dia, 10, random.randint(0, 50)):
            self.hacer("pesaje", r_aves.nuevo_pesaje, PesajeCrear(
                lote_id=lote_id, fecha=dia, aves_muestra=muestra, peso_total_kg=total,
                observaciones=random.choice([None, None, "Lote parejo", "Algunas aves pequenas en la esquina", "Buena uniformidad"]),
            ), ctx=self.ctx(usuario, finca))

    def vacuna(self, dia, lote_id, finca, articulo, producto, via, refuerzo_dias=None, tipo="vacuna", dosis="1 dosis por ave", cantidad=None) -> None:
        lote = self.db.get(Lote, lote_id)
        aves = lote.aves_actuales + lote.aves_descarte
        if aves == 0:
            return
        bodega = self.b_esp if finca.id == self.esperanza.id else self.b_rec
        usada = cantidad if cantidad is not None else redondear(aves, 100)
        if articulo is not None:
            self.asegurar(dia, bodega, articulo, usada)
        if self.a_las(dia, 8, random.randint(0, 50)):
            self.hacer("sanidad", r_san.crear, SanidadCrear(
                fecha=dia, tipo=tipo, producto=producto, lote_id=lote_id, galpon_id=lote.galpon_id,
                articulo_id=articulo.id if articulo else None, bodega_id=bodega.id if articulo else None,
                cantidad_usada=usada if articulo else None, lote_producto=f"S{random.randint(1000, 9999)}",
                dosis=dosis, via=via, aves_tratadas=aves, responsable="Jorge Cardenas",
                proximo_refuerzo=dia + timedelta(days=refuerzo_dias) if refuerzo_dias else None,
            ), ctx=self.ctx(self.jorge, finca))

    def desinfeccion(self, dia, galpon_, finca, litros=8, refuerzo=30) -> None:
        bodega = self.b_esp if finca.id == self.esperanza.id else self.b_rec
        self.asegurar(dia, bodega, self.a_desinfectante, litros)
        if self.a_las(dia, 9, random.randint(0, 50)):
            self.hacer("sanidad", r_san.crear, SanidadCrear(
                fecha=dia, tipo="desinfeccion", producto="Desinfectante yodado", galpon_id=galpon_.id,
                articulo_id=self.a_desinfectante.id, bodega_id=bodega.id, cantidad_usada=litros,
                dosis="10 ml por litro de agua", via="aspersion", responsable="Jorge Cardenas",
                proximo_refuerzo=dia + timedelta(days=refuerzo) if refuerzo else None,
            ), ctx=self.ctx(self.jorge, finca))

    # ------------------------------------------------------------ clima
    def calor(self, dia: date) -> bool:
        # Temporadas secas del Eje Cafetero: diciembre-febrero y julio-agosto
        return dia.month in (1, 2, 7, 8) and (dia.toordinal() * 7919) % 5 < 2

    # ------------------------------------------------------------ ventas
    def stock_huevos(self) -> dict[str, int]:
        from app.modelos.aves import StockHuevos

        filas = self.db.scalars(select(StockHuevos).where(StockHuevos.finca_id == self.esperanza.id)).all()
        por_id = {f.tipo_huevo_id: f.cantidad for f in filas}
        return {t: por_id.get(self.tipos[t], 0) for t in COMERCIALES}

    # ------------------------------------------------------------ descarte (galpon 3)
    def descarte(self, dia) -> None:
        dias = (dia - self.inicio).days
        plan = {68: 450, 84: 650, 99: 700, 108: None}
        lote = self.db.get(Lote, self.po3)
        if dias in plan and lote.estado == "activo" and self.a_las(dia, 10, 30):
            cantidad = plan[dias] or lote.aves_actuales
            cantidad = min(cantidad, lote.aves_actuales)
            if cantidad:
                self.hacer("descarte", r_aves.nuevo_movimiento, MovimientoAvesCrear(
                    lote_id=self.po3, fecha=dia, tipo="descarte", cantidad=cantidad,
                    motivo="Baja postura, fin de ciclo" if plan[dias] else "Descarte final del lote",
                ), ctx=self.ctx(self.jorge, self.esperanza))
        if dias - 1 in plan or dias - 2 in plan:
            lote = self.db.get(Lote, self.po3)
            aves = lote.aves_descarte if dias - 2 in plan else lote.aves_descarte // 2
            if aves and self.a_las(dia, 10, 50):
                ctx = self.ctx(self.jorge, self.esperanza)
                if self.hacer("caja", r_ven.abrir, AbrirTurno(punto_venta_id=self.pv1.id, base_inicial=0,
                                                               observaciones="Venta de gallina de descarte"), ctx=ctx):
                    self.venta_aves(dia, ctx, "descarte", self.po3, aves, aves * random.uniform(1.85, 2.0),
                                    "Comercializadora Avicola del Cafe", 11)
                    self.cerrar_caja(dia, self.jorge, ctx, 11, 45)
        if dias == 111:
            lote = self.db.get(Lote, self.po3)
            if lote.estado == "activo" and lote.aves_actuales + lote.aves_descarte == 0 and self.a_las(dia, 16):
                self.hacer("cierre", r_aves.cerrar, self.po3, CerrarLote(
                    fecha=dia, observaciones="Lote descartado y vendido completo"), ctx=self.ctx(self.diana, self.esperanza))
        if dias == 113:
            self.desinfeccion(dia, self.g3, self.esperanza, litros=16)
            self.asegurar(dia, self.b_esp, self.a_cal, 60)
        if dias == 122:
            self.desinfeccion(dia, self.g4, self.esperanza, litros=12, refuerzo=None)
        if dias == 120 and self.a_las(dia, 9, 15):
            lote4 = self.db.get(Lote, self.po4)
            self.hacer("traslado", r_aves.nuevo_movimiento, MovimientoAvesCrear(
                lote_id=self.po4, fecha=dia, tipo="traslado", cantidad=lote4.aves_actuales + lote4.aves_descarte,
                galpon_destino_id=self.g3.id, motivo="Pasan a postura",
                observaciones="Pollitas de 17 semanas, peso dentro de la tabla",
            ), ctx=self.ctx(self.jorge, self.esperanza))

    # ------------------------------------------------------------ pollo de engorde
    def engorde(self, dia) -> None:
        dias = (dia - self.inicio).days
        ctx_diana = self.ctx(self.diana, self.recreo)
        # Ingresos: el galpon E1 cada 56 dias desde el dia 0; el E2 desde el dia 21
        for galpon_, desde in ((self.e1, 0), (self.e2, 21)):
            if dias >= desde and (dias - desde) % 56 == 0 and self.a_las(dia, 8, 10):
                numero = len(self.engordes) + 1
                raza = "Ross 308" if numero % 2 else "Cobb 500"
                self.compra(dia, self.b_rec, self.solla, [(self.a_viruta, 60)], hora=7)
                if self.a_las(dia, 7, 30):
                    usar = min(60, int(self.existencia(self.b_rec, self.a_viruta)))
                    self.hacer("salida", r_mov.crear, MovimientoCrear(
                        tipo="salida", fecha=dia, bodega_id=self.b_rec.id, motivo="Consumo en galpones",
                        observaciones=f"Cama para el {galpon_.nombre}", items=[ItemEntrada(articulo_id=self.a_viruta.id, cantidad=usar)],
                    ), ctx=self.ctx(self.yuliana, self.recreo))
                salida = self.hacer("lote", r_aves.nuevo_lote, LoteCrear(
                    codigo=f"PE-{numero:02d}", galpon_id=galpon_.id, raza_id=self.razas[raza], proposito="engorde",
                    fecha_ingreso=dia, edad_dias_ingreso=1, aves_iniciales=random.choice([1500, 1550, 1600]),
                    costo_ave=random.choice([2900, 3000, 3100]), observaciones="Pollito de un dia de la incubadora del Valle",
                ), ctx=ctx_diana)
                if salida:
                    self.engordes.append({"id": salida.id, "inicio": dia, "galpon": galpon_})

        for datos in self.engordes:
            lote = self.db.get(Lote, datos["id"])
            if lote.estado != "activo":
                continue
            edad = (dia - datos["inicio"]).days + 1
            if edad in (7, 14, 21, 28, 35) and self.a_las(dia, 10):
                self.pesaje(dia, lote.id, self.yuliana, self.recreo, 50)
            if edad == 7:
                self.vacuna(dia, lote.id, self.recreo, self.a_newcastle, "Newcastle + Bronquitis", "ocular", 14)
                self.vacuna(dia, lote.id, self.recreo, self.a_bronquitis, "Bronquitis Mass", "ocular")
            if edad == 14:
                self.vacuna(dia, lote.id, self.recreo, self.a_gumboro, "Gumboro intermedia", "agua")
            if edad == 21:
                self.vacuna(dia, lote.id, self.recreo, self.a_newcastle, "Newcastle refuerzo", "agua")
            if edad == 24:
                self.vacuna(dia, lote.id, self.recreo, self.a_vitaminas, "Vitaminas antiestres", "agua", tipo="vitamina",
                            dosis="1 ml por litro", cantidad=2)
            # Venta en tres dias (41, 42 y 43)
            if edad in (41, 42, 43):
                if not self.a_las(dia, 7, 45):
                    continue
                if self.hacer("caja", r_ven.abrir, AbrirTurno(punto_venta_id=self.pv2.id, base_inicial=50000), ctx=ctx_diana) is None:
                    continue
                lote = self.db.get(Lote, lote.id)
                aves = lote.aves_actuales if edad == 43 else lote.aves_actuales // (44 - edad)
                peso = interpolar(PESO_POLLO, edad) * random.uniform(0.97, 1.03)
                self.venta_aves(dia, ctx_diana, "pollo", lote.id, aves, aves * peso, COMPRADORES_POLLO[edad - 41], 8)
                if edad == 43 and self.a_las(dia, 11):
                    bultos = random.randint(55, 80)
                    precio = float(self.precio_vigente(self.productos["gallinaza"]["id"]))
                    self.vender(ctx_diana, [ItemVenta(producto_id=self.productos["gallinaza"]["id"], cantidad=bultos)],
                                [PagoVenta(metodo_pago_id=self.pagos["Efectivo"], monto=bultos * precio)],
                                obs="Gallinaza para cultivo de cafe")
                self.cerrar_caja(dia, self.diana, ctx_diana, 12, 30)
            if edad == 45:
                lote = self.db.get(Lote, lote.id)
                if lote.aves_actuales + lote.aves_descarte == 0 and self.a_las(dia, 15):
                    self.hacer("cierre", r_aves.cerrar, lote.id, CerrarLote(fecha=dia, observaciones="Lote vendido completo"), ctx=ctx_diana)
                    self.desinfeccion(dia + timedelta(days=0), datos["galpon"], self.recreo, litros=10)

    # ------------------------------------------------------------ plan de sanidad de ponedoras
    def sanidad_ponedoras(self, dia) -> None:
        dias = (dia - self.inicio).days
        # Revacunacion de Newcastle cada 90 dias, escalonada por lote
        for lote_id, desfase in ((self.po1, 20), (self.po2, 45), (self.po3, 5)):
            if dias >= desfase and (dias - desfase) % 90 == 0:
                self.vacuna(dia, lote_id, self.esperanza, self.a_newcastle, "Newcastle revacunacion", "agua", 90)
        # Vitaminas el primer lunes de cada mes
        if dia.weekday() == 0 and dia.day <= 7:
            for lote_id in (self.po1, self.po2, self.po3, self.po4):
                lote = self.db.get(Lote, lote_id)
                if lote.estado == "activo":
                    litros = max(1, round((lote.aves_actuales + lote.aves_descarte) / 1000))
                    self.vacuna(dia, lote_id, self.esperanza, self.a_vitaminas, "Vitaminas y electrolitos", "agua",
                                tipo="vitamina", dosis="1 ml por litro, 3 dias", cantidad=litros)
        # Desinfeccion mensual
        if dia.day == 1:
            for galpon_ in (self.g1, self.g2, self.g4 if dias < 120 else self.g3):
                self.desinfeccion(dia, galpon_, self.esperanza)
        # Plan de la pollita (PO-04)
        edad = 1 + dias
        plan = {
            7: (self.a_newcastle, "Newcastle + Bronquitis", "ocular", 14),
            8: (self.a_bronquitis, "Bronquitis Mass", "ocular", None),
            14: (self.a_gumboro, "Gumboro intermedia", "agua", 14),
            21: (self.a_newcastle, "Newcastle refuerzo", "agua", 35),
            28: (self.a_gumboro, "Gumboro refuerzo", "agua", None),
            56: (self.a_viruela, "Viruela aviar", "inyectado", None),
            84: (self.a_newcastle, "Newcastle refuerzo", "agua", 28),
            112: (self.a_newcastle, "Newcastle + Bronquitis pre postura", "aspersion", 90),
            113: (self.a_bronquitis, "Bronquitis pre postura", "aspersion", None),
        }
        if edad in plan:
            articulo, producto, via, refuerzo = plan[edad]
            self.vacuna(dia, self.po4, self.esperanza, articulo, producto, via, refuerzo)
        # Pesajes: pollitas cada 14 dias, ponedoras cada mes
        if edad % 14 == 0 and edad <= 140:
            self.pesaje(dia, self.po4, self.jorge, self.esperanza, 50)
        if dia.day == 15:
            for lote_id in (self.po1, self.po2, self.po3):
                lote = self.db.get(Lote, lote_id)
                if lote.estado == "activo" and lote.aves_actuales:
                    self.pesaje_ponedora(dia, lote_id)

    def pesaje_ponedora(self, dia, lote_id) -> None:
        total = round(30 * random.uniform(1.92, 2.05), 2)
        if self.a_las(dia, 10, random.randint(0, 50)):
            self.hacer("pesaje", r_aves.nuevo_pesaje, PesajeCrear(
                lote_id=lote_id, fecha=dia, aves_muestra=30, peso_total_kg=total), ctx=self.ctx(self.jorge, self.esperanza))

    def hay_pollo(self, dia: date) -> bool:
        dias = (dia - self.inicio).days
        return dias >= 0 and dias % 56 < 46
