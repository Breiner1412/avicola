"""La caja: ventas de huevos y aves, precios y cierre del dia."""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.esquemas.ventas import (
    AbrirTurno,
    AnularVenta,
    CerrarTurno,
    ItemVenta,
    PagoVenta,
    PrecioCrear,
    VentaCrear,
)
from app.modelos.ventas import TurnoCaja
from app.rutas import ventas as r_ven
from app.demo.datos import COMERCIALES, CLIENTES_MAYORISTAS


class TiendaMixin:
    """La caja: ventas de huevos y aves, precios y cierre del dia."""

    def vender(self, ctx, items, pagos=None, descuento=0.0, obs=None):
        return self.hacer("venta", r_ven.vender, VentaCrear(items=items, pagos=pagos or [], descuento=descuento, observaciones=obs), ctx=ctx)

    def jornada_tienda(self, dia) -> None:
        if dia.weekday() == 6:  # domingo cerrado
            return
        ctx = self.ctx(self.paola, self.esperanza)
        if not self.a_las(dia, 7, random.randint(25, 40)):
            return
        if self.hacer("caja", r_ven.abrir, AbrirTurno(punto_venta_id=self.pv1.id, base_inicial=100000), ctx=ctx) is None:
            return

        # Mayoristas en la manana: se llevan lo de ayer y dejan algo para el mostrador
        stock = self.stock_huevos()
        clientes = random.sample(CLIENTES_MAYORISTAS, k=random.randint(2, 4) + (1 if dia.weekday() == 0 else 0))
        for n, cliente in enumerate(clientes):
            if not self.a_las(dia, 8 + n, random.randint(0, 50)):
                break
            items, total = [], 0.0
            for tipo in COMERCIALES:
                reserva = 240 if tipo in ("AA", "A") else 60
                panales = max(0, (stock[tipo] - reserva) // 30 // (len(clientes) - n))
                if panales:
                    producto = self.productos[f"panal_{tipo}"]
                    items.append(ItemVenta(producto_id=producto["id"], cantidad=panales))
                    total += panales * float(self.precio_vigente(producto["id"]))
                    stock[tipo] -= panales * 30
            if not items:
                continue
            metodo = "Credito" if random.random() < 0.35 else "Transferencia"
            self.vender(ctx, items, [PagoVenta(metodo_pago_id=self.pagos[metodo], monto=total,
                                               referencia=f"Factura {random.randint(1000, 9999)}" if metodo == "Credito" else f"Bancolombia {random.randint(100000, 999999)}")],
                        obs=cliente)

        # Mostrador
        catalogo = [("panal_AA", 30), ("panal_A", 15), ("medio_AA", 14), ("docena_AA", 14), ("unidad_AA", 8),
                    ("panal_AAA", 9), ("medio_AAA", 5), ("docena_A", 6), ("unidad_A", 4), ("panal_B", 5), ("panal_Super", 3)]
        claves, pesos = zip(*catalogo)
        clientes_dia = random.randint(14, 24) + (10 if dia.weekday() == 5 else 0)
        stock = self.stock_huevos()
        for n in range(clientes_dia):
            minuto = 8 * 60 + int(n * (9 * 60) / clientes_dia) + random.randint(0, 15)
            if not self.a_las(dia, minuto // 60, minuto % 60):
                break
            items, total = [], 0
            for clave in set(random.choices(claves, weights=pesos, k=random.choice([1, 1, 1, 2]))):
                producto = self.productos[clave]
                if clave.startswith("unidad"):
                    cantidad = random.choice([5, 6, 10, 10, 15, 20])
                elif clave.startswith("panal"):
                    cantidad = random.choice([1, 1, 1, 2, 2, 3])
                else:
                    cantidad = random.choice([1, 1, 2])
                if stock[producto["tipo"]] < cantidad * producto["factor"]:
                    continue
                stock[producto["tipo"]] -= cantidad * producto["factor"]
                items.append(ItemVenta(producto_id=producto["id"], cantidad=cantidad))
                total += cantidad * producto["precio"] * self.factor_precio(dia)
            if not items:
                continue
            descuento = 1000 if total > 40000 and random.random() < 0.08 else 0
            venta = self.vender(ctx, items, None, descuento)
            if venta is not None and random.random() < 0.015:
                self.hacer("anulacion", r_ven.anular, venta.id, AnularVenta(
                    motivo=random.choice(["Se registro la cantidad equivocada", "El cliente cambio de producto", "Venta repetida por error"])),
                    ctx=ctx)

        # Pagos por transferencia del mostrador (Nequi / Daviplata)
        for _ in range(random.randint(2, 6)):
            clave = random.choice(["panal_AA", "panal_AAA", "medio_AA", "panal_A"])
            producto = self.productos[clave]
            cantidad = random.choice([1, 2])
            if stock[producto["tipo"]] < cantidad * producto["factor"]:
                continue
            if not self.a_las(dia, random.randint(9, 16), random.randint(0, 59)):
                continue
            stock[producto["tipo"]] -= cantidad * producto["factor"]
            precio = float(self.precio_vigente(producto["id"]))
            self.vender(ctx, [ItemVenta(producto_id=producto["id"], cantidad=cantidad)],
                        [PagoVenta(metodo_pago_id=self.pagos["Transferencia"], monto=precio * cantidad,
                                   referencia=f"{random.choice(['Nequi', 'Daviplata'])} {random.randint(100000, 999999)}")])

        # Cierre de caja
        if dia == self.hoy:
            return  # la caja de hoy sigue abierta
        if not self.a_las(dia, 17, random.randint(20, 50)):
            return
        turno = self.db.scalars(select(TurnoCaja).where(TurnoCaja.usuario_id == self.paola.id, TurnoCaja.estado == "abierto")).first()
        if turno is None:
            return
        from app.servicios.ventas import totales_turno

        esperado = totales_turno(self.db, turno)["esperado_en_caja"]
        azar = random.random()
        diferencia = 0 if azar < 0.8 else (-random.choice([500, 1000, 2000, 5000]) if azar < 0.92 else random.choice([200, 500, 1000]))
        self.hacer("caja", r_ven.cerrar, CerrarTurno(
            efectivo_contado=esperado + diferencia,
            observaciones=None if diferencia == 0 else ("Faltante, se revisa con la cajera" if diferencia < 0 else "Sobrante, un cliente no recibio vueltas"),
        ), ctx=ctx)

    def cerrar_caja(self, dia, usuario, ctx, hora, minuto) -> None:
        from app.servicios.ventas import totales_turno

        if not self.a_las(dia, hora, minuto):
            return
        turno = self.db.scalars(select(TurnoCaja).where(TurnoCaja.usuario_id == usuario.id, TurnoCaja.estado == "abierto")).first()
        if turno:
            self.hacer("caja", r_ven.cerrar, CerrarTurno(efectivo_contado=totales_turno(self.db, turno)["esperado_en_caja"]), ctx=ctx)

    def precio_vigente(self, producto_id: int) -> Decimal:
        from app.servicios.ventas import precio_vigente

        return precio_vigente(self.db, producto_id, self.pv1.id)

    def factor_precio(self, dia: date) -> float:
        return 1.06 if self.subida_precio and dia >= self.subida_precio else 1.0

    def subir_precios(self, dia) -> None:
        """A mitad del periodo sube el huevo un 6%."""
        if not self.a_las(dia, 6, 30):
            return
        ctx = self.ctx(self.diana, self.esperanza)
        for producto in self.productos.values():
            if producto["tipo"] is None:
                continue
            nuevo = round(producto["precio"] * 1.06, -2)
            self.hacer("precio", r_ven.poner_precio, PrecioCrear(producto_id=producto["id"], precio=nuevo, desde=dia), ctx=ctx)
        self.subida_precio = dia

    def venta_aves(self, dia, ctx, producto, lote_id, aves, kilos, cliente, hora) -> None:
        if aves <= 0 or not self.a_las(dia, hora, random.randint(0, 50)):
            return
        precio = float(self.precio_vigente(self.productos[producto]["id"]))
        total = round(kilos, 1) * precio
        self.vender(ctx, [ItemVenta(producto_id=self.productos[producto]["id"], cantidad=round(kilos, 1), lote_id=lote_id, aves=aves)],
                    [PagoVenta(metodo_pago_id=self.pagos["Transferencia"], monto=round(total, 2), referencia=f"Bancolombia {random.randint(100000, 999999)}")],
                    obs=cliente)
