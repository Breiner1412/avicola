"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Lote, MetodoPago, Pagina, ProductoVenta, PuntoVenta, Turno, Venta } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

type Linea = {
  producto: ProductoVenta;
  cantidad: string;
  lote_id: string;
  aves: string;
};

const moneda = (valor: number) => `$${Math.round(valor).toLocaleString("es-CO")}`;

const NOMBRE_PRESENTACION: Record<string, string> = {
  unidad: "unidad",
  docena: "docena (12)",
  medio_panal: "medio panal (15)",
  panal: "panal (30)",
  kg: "kilo",
};

export default function Caja() {
  const { sesion, puede } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;
  const [recargas, setRecargas] = useState(0);

  const { datos: turno, cargando, recargar: recargarTurno } = useDatos<Turno | null>("/caja/turno", `${finca}-${recargas}`);
  const { datos: puntos } = useDatos<PuntoVenta[]>("/puntos-venta", finca);
  const { datos: productos } = useDatos<ProductoVenta[]>("/productos-venta", `${finca}-${recargas}`);
  const { datos: metodos } = useDatos<MetodoPago[]>("/metodos-pago", finca);
  const { datos: lotes } = useDatos<Lote[]>("/lotes?solo_activos=true", `${finca}-${recargas}`);
  const { datos: ventas, recargar: recargarVentas } = useDatos<Pagina<Venta>>(
    turno ? `/ventas?turno_id=${turno.id}&tamano=50` : null,
    `${turno?.id ?? 0}-${recargas}`,
  );

  const [puntoId, setPuntoId] = useState("");
  const [base, setBase] = useState("0");
  const [lineas, setLineas] = useState<Linea[]>([]);
  const [descuento, setDescuento] = useState("0");
  const [metodoId, setMetodoId] = useState("");
  const [referencia, setReferencia] = useState("");
  const [fallo, setFallo] = useState("");
  const [recibo, setRecibo] = useState<Venta | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [cerrando, setCerrando] = useState(false);
  const [contado, setContado] = useState("");

  const subtotal = useMemo(
    () =>
      lineas.reduce((suma, linea) => suma + Number(linea.cantidad || 0) * Number(linea.producto.precio ?? 0), 0),
    [lineas],
  );
  const total = Math.max(0, subtotal - Number(descuento || 0));

  function agregar(producto: ProductoVenta) {
    setFallo("");
    setLineas((actuales) => {
      const existente = actuales.findIndex((l) => l.producto.id === producto.id && producto.clase === "huevo");
      if (existente >= 0) {
        const copia = [...actuales];
        copia[existente] = { ...copia[existente], cantidad: String(Number(copia[existente].cantidad || 0) + 1) };
        return copia;
      }
      return [...actuales, { producto, cantidad: "1", lote_id: "", aves: "" }];
    });
  }

  function cambiar(indice: number, campo: keyof Linea, valor: string) {
    setLineas((actuales) => actuales.map((l, i) => (i === indice ? { ...l, [campo]: valor } : l)));
  }

  async function abrirCaja(evento: React.FormEvent) {
    evento.preventDefault();
    setFallo("");
    try {
      await api("/caja/abrir", {
        metodo: "POST",
        cuerpo: { punto_venta_id: Number(puntoId), base_inicial: Number(base || 0) },
      });
      setRecargas((n) => n + 1);
      await recargarTurno();
    } catch (error) {
      setFallo(mensajeDeError(error));
    }
  }

  async function cobrar() {
    setFallo("");
    if (lineas.length === 0) {
      setFallo("Agrega al menos un producto");
      return;
    }
    setGuardando(true);
    try {
      const venta = await api<Venta>("/ventas", {
        metodo: "POST",
        cuerpo: {
          items: lineas.map((l) => ({
            producto_id: l.producto.id,
            cantidad: Number(l.cantidad),
            lote_id: l.lote_id ? Number(l.lote_id) : null,
            aves: l.aves ? Number(l.aves) : null,
          })),
          pagos: metodoId
            ? [{ metodo_pago_id: Number(metodoId), monto: total, referencia: referencia || null }]
            : [],
          descuento: Number(descuento || 0),
        },
      });
      setRecibo(venta);
      setLineas([]);
      setDescuento("0");
      setReferencia("");
      setRecargas((n) => n + 1);
      await Promise.all([recargarTurno(), recargarVentas()]);
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function anular(venta: Venta) {
    const motivo = prompt(`Por que se anula la venta ${venta.numero}?`);
    if (!motivo || motivo.trim().length < 3) return;
    try {
      await api(`/ventas/${venta.id}/anular`, { metodo: "POST", cuerpo: { motivo: motivo.trim() } });
      setRecargas((n) => n + 1);
      await Promise.all([recargarTurno(), recargarVentas()]);
    } catch (error) {
      alert(mensajeDeError(error));
    }
  }

  async function cerrarCaja(evento: React.FormEvent) {
    evento.preventDefault();
    try {
      await api("/caja/cerrar", { metodo: "POST", cuerpo: { efectivo_contado: Number(contado || 0) } });
      setCerrando(false);
      setContado("");
      setRecargas((n) => n + 1);
      await recargarTurno();
    } catch (error) {
      alert(mensajeDeError(error));
    }
  }

  if (cargando) return <Cargando />;

  if (!turno) {
    return (
      <>
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Caja</h1>
          <p className="text-sm text-slate-500">Abre la caja para empezar a vender</p>
        </div>

        <Tarjeta titulo="Abrir la caja">
          {!puede("caja", "crear") ? (
            <Aviso tipo="info">Tu rol no puede abrir la caja.</Aviso>
          ) : (
            <form onSubmit={abrirCaja} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Lista etiqueta="Punto de venta" required value={puntoId} onChange={(e) => setPuntoId(e.target.value)}>
                  <option value="">Elige el punto</option>
                  {(puntos ?? []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nombre}
                      {p.es_central ? " (central)" : ""}
                    </option>
                  ))}
                </Lista>
                <Campo
                  etiqueta="Base inicial en efectivo"
                  type="number"
                  min={0}
                  value={base}
                  onChange={(e) => setBase(e.target.value)}
                />
              </div>
              {fallo ? <Aviso>{fallo}</Aviso> : null}
              <Boton type="submit">Abrir caja</Boton>
            </form>
          )}
        </Tarjeta>
      </>
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Caja · {turno.punto_venta_nombre}</h1>
          <p className="text-sm text-slate-500">
            Turno abierto por {turno.usuario_nombre} · {turno.ventas} venta(s) · vendido{" "}
            {moneda(turno.total_vendido)}
          </p>
        </div>
        {puede("caja", "editar") ? (
          <Boton tono="peligro" onClick={() => setCerrando(true)}>
            Cerrar caja
          </Boton>
        ) : null}
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="min-w-0 space-y-5 lg:col-span-2">
          <Tarjeta titulo="Productos">
            {!productos || productos.length === 0 ? (
              <Vacio>No hay productos configurados. Creálos en Productos y precios.</Vacio>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {productos.map((producto) => (
                  <button
                    key={producto.id}
                    onClick={() => agregar(producto)}
                    disabled={producto.precio === null}
                    className="rounded-xl border border-slate-200 p-3 text-left transition hover:border-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
                  >
                    <span className="block break-words font-medium text-slate-800">{producto.nombre}</span>
                    <span className="block text-xs text-slate-500">
                      {NOMBRE_PRESENTACION[producto.presentacion]}
                      {producto.disponible !== null && producto.disponible !== undefined
                        ? ` · quedan ${producto.disponible}`
                        : ""}
                    </span>
                    <span className="mt-1 block text-sm font-semibold text-emerald-800">
                      {producto.precio !== null ? moneda(producto.precio) : "sin precio"}
                      {producto.cobro_por === "kg" ? " / kg" : ""}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </Tarjeta>

          <Tarjeta titulo="Ventas del turno">
            {!ventas || ventas.datos.length === 0 ? (
              <Vacio>Todavia no hay ventas en este turno.</Vacio>
            ) : (
              <Tabla columnas={["Numero", "Hora", "Total", "Pago", "Estado", ""]}>
                {ventas.datos.map((venta) => (
                  <tr key={venta.id} className={venta.estado === "anulada" ? "text-slate-400" : "hover:bg-slate-50"}>
                    <td className="px-3 py-2 font-medium text-slate-700">{venta.numero}</td>
                    <td className="px-3 py-2 text-xs text-slate-500">
                      {new Date(venta.creado_en).toLocaleTimeString("es-CO")}
                    </td>
                    <td className="px-3 py-2">{moneda(venta.total)}</td>
                    <td className="px-3 py-2 text-xs">{venta.pagos.map((p) => p.metodo_nombre).join(", ")}</td>
                    <td className="px-3 py-2">
                      {venta.estado === "anulada" ? (
                        <Insignia tono="rojo">Anulada</Insignia>
                      ) : (
                        <Insignia tono="verde">Activa</Insignia>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex justify-end gap-2">
                        <Boton tono="suave" onClick={() => setRecibo(venta)}>
                          Ver
                        </Boton>
                        {puede("ventas", "editar") && venta.estado === "activa" ? (
                          <Boton tono="peligro" onClick={() => anular(venta)}>
                            Anular
                          </Boton>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </Tabla>
            )}
          </Tarjeta>
        </div>

        <div className="min-w-0 space-y-5">
          <Tarjeta titulo="Venta actual">
            {lineas.length === 0 ? (
              <Vacio>Toca un producto para agregarlo.</Vacio>
            ) : (
              <div className="space-y-3">
                {lineas.map((linea, indice) => (
                  <div key={indice} className="rounded-lg border border-slate-200 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium text-slate-800">{linea.producto.nombre}</p>
                        <p className="text-xs text-slate-500">
                          {moneda(linea.producto.precio ?? 0)}
                          {linea.producto.cobro_por === "kg" ? " por kg" : ` por ${NOMBRE_PRESENTACION[linea.producto.presentacion]}`}
                        </p>
                      </div>
                      <button
                        onClick={() => setLineas((actuales) => actuales.filter((_, i) => i !== indice))}
                        className="rounded p-1 text-slate-400 hover:bg-slate-100"
                        aria-label="Quitar"
                      >
                        ✕
                      </button>
                    </div>

                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      <Campo
                        etiqueta={linea.producto.cobro_por === "kg" ? "Kilos" : "Cantidad"}
                        type="number"
                        min={0}
                        step={linea.producto.cobro_por === "kg" ? "0.001" : "1"}
                        value={linea.cantidad}
                        onChange={(e) => cambiar(indice, "cantidad", e.target.value)}
                      />
                      {linea.producto.clase === "ave_engorde" ? (
                        <Campo
                          etiqueta="Cuantas aves"
                          type="number"
                          min={1}
                          value={linea.aves}
                          onChange={(e) => cambiar(indice, "aves", e.target.value)}
                        />
                      ) : null}
                      {linea.producto.clase !== "huevo" && linea.producto.clase !== "otro" ? (
                        <Lista
                          etiqueta="Lote"
                          value={linea.lote_id}
                          onChange={(e) => cambiar(indice, "lote_id", e.target.value)}
                        >
                          <option value="">Elige el lote</option>
                          {(lotes ?? [])
                            .filter((l) =>
                              linea.producto.clase === "ave_descarte" ? l.aves_descarte > 0 : l.proposito === "engorde",
                            )
                            .map((l) => (
                              <option key={l.id} value={l.id}>
                                {l.codigo}
                                {linea.producto.clase === "ave_descarte"
                                  ? ` (${l.aves_descarte} de descarte)`
                                  : ` (${l.aves_actuales} aves)`}
                              </option>
                            ))}
                        </Lista>
                      ) : null}
                    </div>

                    <p className="mt-2 text-right text-sm font-medium text-slate-700">
                      {moneda(Number(linea.cantidad || 0) * Number(linea.producto.precio ?? 0))}
                    </p>
                  </div>
                ))}

                <div className="space-y-2 border-t border-slate-200 pt-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Subtotal</span>
                    <span>{moneda(subtotal)}</span>
                  </div>
                  <Campo
                    etiqueta="Descuento"
                    type="number"
                    min={0}
                    value={descuento}
                    onChange={(e) => setDescuento(e.target.value)}
                  />
                  <Lista etiqueta="Forma de pago" value={metodoId} onChange={(e) => setMetodoId(e.target.value)}>
                    <option value="">Efectivo</option>
                    {(metodos ?? []).map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.nombre}
                      </option>
                    ))}
                  </Lista>
                  {metodoId && !metodos?.find((m) => String(m.id) === metodoId)?.es_efectivo ? (
                    <Campo
                      etiqueta="Referencia"
                      value={referencia}
                      onChange={(e) => setReferencia(e.target.value)}
                    />
                  ) : null}
                  <div className="flex justify-between text-base font-semibold text-slate-800">
                    <span>Total</span>
                    <span>{moneda(total)}</span>
                  </div>
                </div>

                {fallo ? <Aviso>{fallo}</Aviso> : null}

                <Boton onClick={cobrar} disabled={guardando} className="w-full">
                  {guardando ? "Cobrando..." : `Cobrar ${moneda(total)}`}
                </Boton>
              </div>
            )}
          </Tarjeta>

          <Tarjeta titulo="Estado de la caja">
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">Base inicial</dt>
                <dd>{moneda(turno.base_inicial)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Vendido</dt>
                <dd>{moneda(turno.total_vendido)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Recibido en efectivo</dt>
                <dd>{moneda(turno.total_efectivo)}</dd>
              </div>
              <div className="flex justify-between font-semibold text-slate-800">
                <dt>Debe haber en caja</dt>
                <dd>{moneda(turno.esperado_en_caja)}</dd>
              </div>
            </dl>
          </Tarjeta>
        </div>
      </div>

      <Modal titulo={`Venta ${recibo?.numero ?? ""}`} abierto={Boolean(recibo)} onCerrar={() => setRecibo(null)}>
        {recibo ? (
          <div className="space-y-3 text-sm">
            <p className="text-slate-500">
              {recibo.fecha} · {recibo.punto_venta_nombre} · {recibo.usuario_nombre}
            </p>
            <ul className="divide-y divide-slate-100">
              {recibo.detalles.map((detalle) => (
                <li key={detalle.id} className="flex justify-between py-2">
                  <span>
                    {detalle.descripcion}
                    <span className="block text-xs text-slate-500">
                      {detalle.cantidad} x {moneda(detalle.precio_unitario)}
                      {detalle.unidades ? ` · ${detalle.unidades} unidades` : ""}
                    </span>
                  </span>
                  <span>{moneda(detalle.subtotal)}</span>
                </li>
              ))}
            </ul>
            <div className="space-y-1 border-t border-slate-200 pt-2">
              <div className="flex justify-between text-slate-500">
                <span>Subtotal</span>
                <span>{moneda(recibo.subtotal)}</span>
              </div>
              {recibo.descuento ? (
                <div className="flex justify-between text-slate-500">
                  <span>Descuento</span>
                  <span>-{moneda(recibo.descuento)}</span>
                </div>
              ) : null}
              <div className="flex justify-between text-base font-semibold text-slate-800">
                <span>Total</span>
                <span>{moneda(recibo.total)}</span>
              </div>
              <div className="text-xs text-slate-500">
                Pago: {recibo.pagos.map((p) => `${p.metodo_nombre} ${moneda(p.monto)}`).join(" · ")}
              </div>
              {recibo.estado === "anulada" ? (
                <Aviso>Anulada por {recibo.anulada_por}: {recibo.motivo_anulacion}</Aviso>
              ) : null}
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal titulo="Cerrar la caja" abierto={cerrando} onCerrar={() => setCerrando(false)}>
        <form onSubmit={cerrarCaja} className="space-y-4">
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Debe haber en caja</dt>
              <dd className="font-semibold">{moneda(turno.esperado_en_caja)}</dd>
            </div>
          </dl>
          <Campo
            etiqueta="Efectivo contado"
            type="number"
            min={0}
            required
            value={contado}
            onChange={(e) => setContado(e.target.value)}
          />
          {contado ? (
            <Aviso tipo={Number(contado) === turno.esperado_en_caja ? "bien" : "info"}>
              Diferencia: {moneda(Number(contado) - turno.esperado_en_caja)}
            </Aviso>
          ) : null}
          <div className="flex justify-end gap-2">
            <Boton type="button" tono="suave" onClick={() => setCerrando(false)}>
              Cancelar
            </Boton>
            <Boton type="submit">Cerrar caja</Boton>
          </div>
        </form>
      </Modal>
    </>
  );
}
