"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Lote, MetodoPago, Pagina, ProductoVenta, PuntoVenta, Turno, Venta } from "@/lib/tipos";
import {
  Aviso,
  Boton,
  Campo,
  Cargando,
  Encabezado,
  Insignia,
  Lista,
  Modal,
  Paginador,
  Tabla,
  Tarjeta,
  Vacio,
} from "@/componentes/ui";
import { Icono } from "@/componentes/iconos";
import { fecha, hora } from "@/lib/formato";
import { type AjustesVentas } from "@/componentes/tope-descuento";
import { avisar, useDialogos } from "@/componentes/dialogos";

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
  const { pedirTexto } = useDialogos();
  const { sesion, puede } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;
  const [recargas, setRecargas] = useState(0);

  const {
    datos: turno,
    cargando,
    recargar: recargarTurno,
  } = useDatos<Turno | null>("/caja/turno", `${finca}-${recargas}`);
  const { datos: puntos } = useDatos<PuntoVenta[]>("/puntos-venta", finca);
  const { datos: productos } = useDatos<ProductoVenta[]>("/productos-venta", `${finca}-${recargas}`);
  const { datos: metodos } = useDatos<MetodoPago[]>("/metodos-pago", finca);
  const { datos: lotes } = useDatos<Lote[]>("/lotes?solo_activos=true", `${finca}-${recargas}`);
  const [paginaVentas, setPaginaVentas] = useState(1);
  const { datos: ajustes } = useDatos<AjustesVentas>("/ventas/ajustes");
  const tope = ajustes?.tengo_tope ? ajustes.descuento_maximo : 100;
  const { datos: ventas, recargar: recargarVentas } = useDatos<Pagina<Venta>>(
    turno ? `/ventas?turno_id=${turno.id}&pagina=${paginaVentas}&tamano=12` : null,
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
    () => lineas.reduce((suma, linea) => suma + Number(linea.cantidad || 0) * Number(linea.producto.precio ?? 0), 0),
    [lineas],
  );
  const porcentaje = Math.min(tope, Math.max(0, Number(descuento || 0)));
  const valorDescuento = Math.round((subtotal * porcentaje) / 100);
  const total = Math.max(0, subtotal - valorDescuento);

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
          pagos: metodoId ? [{ metodo_pago_id: Number(metodoId), monto: total, referencia: referencia || null }] : [],
          descuento_porcentaje: porcentaje || null,
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
    const motivo = await pedirTexto({
      titulo: `Anular la venta ${venta.numero}`,
      mensaje: "Lo vendido vuelve al inventario. La venta queda en el historial como anulada.",
      etiqueta: "Por que se anula?",
      placeholder: "Ej: se registro la cantidad equivocada",
      aceptar: "Anular venta",
      peligro: true,
      requerido: true,
    });
    if (!motivo) return;
    if (motivo.trim().length < 10) {
      avisar.error("Explica el motivo en al menos 10 letras");
      return;
    }
    try {
      await api(`/ventas/${venta.id}/anular`, { metodo: "POST", cuerpo: { motivo } });
      setRecargas((n) => n + 1);
      await Promise.all([recargarTurno(), recargarVentas()]);
      avisar.bien(`Venta ${venta.numero} anulada`);
    } catch (error) {
      avisar.error(mensajeDeError(error));
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
      avisar.error(mensajeDeError(error));
    }
  }

  // Botones de mas y menos: parten de la cantidad vigente para no perder toques seguidos
  function sumar(indice: number, paso: number) {
    setLineas((actuales) =>
      actuales.map((l, i) =>
        i === indice ? { ...l, cantidad: String(Math.max(1, Number(l.cantidad || 0) + paso)) } : l,
      ),
    );
  }

  if (cargando) return <Cargando />;

  if (!turno) {
    return (
      <>
        <Encabezado titulo="Caja" descripcion="Abre la caja para empezar a vender" />

        <Tarjeta titulo="Abrir la caja" className="max-w-2xl">
          {!puede("caja", "crear") ? (
            <Aviso tipo="info">Tu rol no puede abrir la caja.</Aviso>
          ) : (
            <form onSubmit={abrirCaja} className="space-y-5">
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
                  inputMode="numeric"
                  className="cifra"
                  value={base}
                  onChange={(e) => setBase(e.target.value)}
                />
              </div>
              {fallo ? <Aviso>{fallo}</Aviso> : null}
              <Boton type="submit" tamano="grande" icono="caja" className="w-full sm:w-auto">
                Abrir caja
              </Boton>
            </form>
          )}
        </Tarjeta>
      </>
    );
  }

  const unidades = lineas.length;

  return (
    <>
      <Encabezado
        titulo={turno.punto_venta_nombre}
        antes={<p className="text-base font-semibold text-galpon">Caja abierta</p>}
        descripcion={`Turno de ${turno.usuario_nombre ?? "sin nombre"}, ${turno.ventas} venta(s), vendido ${moneda(turno.total_vendido)}`}
        acciones={
          puede("caja", "editar") ? (
            <Boton tono="peligro" icono="llave" onClick={() => setCerrando(true)}>
              Cerrar caja
            </Boton>
          ) : null
        }
      />

      <div
        className={`grid gap-5 lg:grid-cols-[minmax(0,1fr)_23rem] xl:grid-cols-[minmax(0,1fr)_26rem] [&>*]:min-w-0 ${
          unidades ? "pb-28 lg:pb-0" : ""
        }`}
      >
        <Tarjeta titulo="Productos" descripcion="Toca un producto para agregarlo a la venta" className="lg:col-start-1 lg:row-start-1">
          {!productos || productos.length === 0 ? (
            <Vacio>No hay productos configurados. Creálos en Productos y precios.</Vacio>
          ) : (
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 2xl:grid-cols-4">
              {productos.map((producto) => (
                <button
                  key={producto.id}
                  onClick={() => agregar(producto)}
                  disabled={producto.precio === null}
                  className="flex min-h-28 flex-col justify-between gap-2 rounded-xl border-[1.5px] border-linea bg-superficie p-3.5 text-left transition hover:border-galpon active:bg-cal disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-linea"
                >
                  <span className="min-w-0">
                    <span className="block text-base leading-snug font-bold break-words text-tinta">{producto.nombre}</span>
                    <span className="mt-0.5 block text-sm text-tinta-2">
                      {NOMBRE_PRESENTACION[producto.presentacion]}
                      {producto.disponible !== null && producto.disponible !== undefined
                        ? `, quedan ${producto.disponible.toLocaleString("es-CO", { maximumFractionDigits: 1 })}`
                        : ""}
                    </span>
                  </span>
                  <span className="cifra text-[1.35rem] leading-none font-bold text-tinta [font-stretch:110%]">
                    {producto.precio !== null ? moneda(producto.precio) : "Sin precio"}
                    {producto.cobro_por === "kg" ? <span className="text-base font-semibold text-tinta-2"> / kg</span> : null}
                  </span>
                </button>
              ))}
            </div>
          )}
        </Tarjeta>

        <aside className="space-y-5 self-start lg:sticky lg:top-20 lg:col-start-2 lg:row-span-2 lg:row-start-1">
          <section id="venta-actual" aria-label="Venta actual" className="scroll-mt-20 rounded-xl border border-linea bg-superficie">
            <header className="flex items-center justify-between gap-3 px-5 pt-4 pb-1">
              <h2 className="font-cifra text-lg font-bold text-tinta [font-stretch:105%]">Venta actual</h2>
              {unidades ? <Insignia>{unidades} producto(s)</Insignia> : null}
            </header>
            <div className="p-5 pt-3">
              {lineas.length === 0 ? (
                <Vacio icono="caja">Toca un producto para agregarlo.</Vacio>
              ) : (
                <div className="space-y-4">
                  <ul className="divide-y divide-linea-suave">
                    {lineas.map((linea, indice) => (
                      <LineaVenta
                        key={indice}
                        linea={linea}
                        lotes={lotes ?? []}
                        alCambiar={(campo, valor) => cambiar(indice, campo, valor)}
                        alSumar={(paso) => sumar(indice, paso)}
                        alQuitar={() => setLineas((actuales) => actuales.filter((_, i) => i !== indice))}
                      />
                    ))}
                  </ul>

                  <div className="space-y-4 border-t-2 border-linea pt-4">
                    <div className="flex justify-between text-base">
                      <span className="text-tinta-2">Subtotal</span>
                      <span className="cifra">{moneda(subtotal)}</span>
                    </div>

                    <div>
                      <span className="text-sm font-semibold text-tinta">
                        Descuento
                        {ajustes?.tengo_tope ? (
                          <span className="ml-1 font-normal text-tinta-2">(maximo {ajustes.descuento_maximo} %)</span>
                        ) : null}
                      </span>
                      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                        {[0, 5, 10].filter((valor) => valor <= tope).map((valor) => (
                          <button
                            key={valor}
                            type="button"
                            aria-pressed={porcentaje === valor}
                            onClick={() => setDescuento(String(valor))}
                            className={`min-h-11 rounded-lg px-3.5 text-base font-semibold transition ${
                              porcentaje === valor
                                ? "bg-galpon text-white"
                                : "bg-superficie text-tinta ring-[1.5px] ring-linea ring-inset hover:bg-cal"
                            }`}
                          >
                            {valor === 0 ? "Sin descuento" : `${valor} %`}
                          </button>
                        ))}
                        <label className="flex min-h-11 items-center gap-1 rounded-lg bg-superficie px-2.5 ring-[1.5px] ring-linea ring-inset focus-within:ring-2 focus-within:ring-galpon">
                          <input
                            type="number"
                            min={0}
                            max={tope}
                            step="0.5"
                            value={descuento}
                            onChange={(e) => setDescuento(e.target.value)}
                            aria-label="Otro porcentaje de descuento"
                            className="cifra w-14 border-0 bg-transparent text-right text-base focus:ring-0 focus:outline-none"
                          />
                          <span className="text-base text-tinta-2">%</span>
                        </label>
                      </div>
                      {valorDescuento > 0 ? (
                        <div className="mt-2 flex justify-between text-base text-tinta-2">
                          <span>Descuento {porcentaje} %</span>
                          <span className="cifra">-{moneda(valorDescuento)}</span>
                        </div>
                      ) : null}
                    </div>

                    <Lista etiqueta="Forma de pago" value={metodoId} onChange={(e) => setMetodoId(e.target.value)}>
                      <option value="">Efectivo</option>
                      {(metodos ?? []).map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.nombre}
                        </option>
                      ))}
                    </Lista>
                    {metodoId && !metodos?.find((m) => String(m.id) === metodoId)?.es_efectivo ? (
                      <Campo etiqueta="Referencia" value={referencia} onChange={(e) => setReferencia(e.target.value)} />
                    ) : null}

                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-lg font-semibold text-tinta">Total</span>
                      <span className="cifra text-[2.25rem] leading-none font-extrabold text-tinta [font-stretch:115%]">
                        {moneda(total)}
                      </span>
                    </div>
                  </div>

                  {fallo ? <Aviso>{fallo}</Aviso> : null}

                  <Boton onClick={cobrar} disabled={guardando} tamano="cobrar" className="w-full">
                    {guardando ? "Cobrando..." : `Cobrar ${moneda(total)}`}
                  </Boton>
                </div>
              )}
            </div>
          </section>

          <Tarjeta titulo="Estado de la caja">
            <dl className="space-y-2.5 text-base">
              <FilaCaja texto="Base inicial" valor={turno.base_inicial} />
              <FilaCaja texto="Vendido" valor={turno.total_vendido} />
              <FilaCaja texto="Recibido en efectivo" valor={turno.total_efectivo} />
              <div className="flex items-baseline justify-between gap-3 border-t border-linea pt-2.5">
                <dt className="font-semibold text-tinta">Debe haber en caja</dt>
                <dd className="cifra text-xl font-bold text-tinta">{moneda(turno.esperado_en_caja)}</dd>
              </div>
            </dl>
          </Tarjeta>
        </aside>

        <Tarjeta
          titulo="Ventas del turno"
          descripcion={ventas ? `${ventas.total} venta(s) en este turno` : undefined}
          className="lg:col-start-1 lg:row-start-2"
        >
          {!ventas || ventas.datos.length === 0 ? (
            <Vacio>Todavia no hay ventas en este turno.</Vacio>
          ) : (
            <>
              <Tabla columnas={["Venta", "Hora", "Pago", "Estado", "Total", ""]} numericas={[4]}>
                {ventas.datos.map((venta) => (
                  <tr
                    key={venta.id}
                    className={venta.estado === "anulada" ? "text-tinta-3 [&_td:nth-child(5)]:line-through" : ""}
                  >
                    <td className="cifra px-3 font-semibold">{venta.numero}</td>
                    <td className="px-3 text-sm whitespace-nowrap text-tinta-2">{hora(venta.creado_en)}</td>
                    <td className="px-3 text-sm">{venta.pagos.map((p) => p.metodo_nombre).join(", ")}</td>
                    <td className="px-3">
                      {venta.estado === "anulada" ? (
                        <Insignia tono="rojo">Anulada</Insignia>
                      ) : (
                        <Insignia tono="verde">Activa</Insignia>
                      )}
                    </td>
                    <td className="cifra px-3 text-right font-semibold whitespace-nowrap">{moneda(venta.total)}</td>
                    <td className="px-3 text-right">
                      <div className="flex justify-end gap-2">
                        <Boton tono="suave" tamano="compacto" onClick={() => setRecibo(venta)}>
                          Ver
                        </Boton>
                        {puede("ventas", "editar") && venta.estado === "activa" ? (
                          <Boton tono="peligro" tamano="compacto" onClick={() => anular(venta)}>
                            Anular
                          </Boton>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </Tabla>
              <Paginador
                pagina={ventas.pagina}
                paginas={Math.max(1, Math.ceil(ventas.total / ventas.tamano))}
                total={ventas.total}
                porPagina={ventas.tamano}
                setPagina={setPaginaVentas}
                nombre="ventas"
              />
            </>
          )}
        </Tarjeta>
      </div>

      {/* En el celular, el total y el boton de cobrar quedan al alcance del pulgar */}
      {unidades ? (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-linea bg-superficie px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] shadow-[0_-8px_24px_-12px_rgb(22_58_44/0.3)] lg:hidden">
          <div className="mb-2 flex items-center justify-between gap-3 text-base text-tinta-2">
            <span>
              {unidades} producto(s), {metodos?.find((m) => String(m.id) === metodoId)?.nombre ?? "Efectivo"}
            </span>
            <a href="#venta-actual" className="inline-flex min-h-10 items-center font-semibold text-galpon">
              Revisar
            </a>
          </div>
          {fallo ? (
            <p role="alert" className="mb-2 rounded-lg border-l-4 border-alerta bg-alerta-suave px-3 py-2 text-base text-tinta">
              {fallo}
            </p>
          ) : null}
          <Boton onClick={cobrar} disabled={guardando} tamano="cobrar" className="w-full">
            {guardando ? "Cobrando..." : `Cobrar ${moneda(total)}`}
          </Boton>
        </div>
      ) : null}

      <Modal titulo={`Venta ${recibo?.numero ?? ""}`} abierto={Boolean(recibo)} onCerrar={() => setRecibo(null)}>
        {recibo ? (
          <div className="space-y-3 text-base">
            <p className="text-tinta-2">
              {fecha(recibo.fecha)}, {recibo.punto_venta_nombre}, {recibo.usuario_nombre}
            </p>
            <ul className="divide-y divide-linea-suave">
              {recibo.detalles.map((detalle) => (
                <li key={detalle.id} className="flex justify-between gap-3 py-2.5">
                  <span>
                    {detalle.descripcion}
                    <span className="block text-sm text-tinta-2">
                      {detalle.cantidad} x {moneda(detalle.precio_unitario)}
                      {detalle.unidades ? `, ${detalle.unidades} unidades` : ""}
                    </span>
                  </span>
                  <span className="cifra whitespace-nowrap">{moneda(detalle.subtotal)}</span>
                </li>
              ))}
            </ul>
            <div className="space-y-1.5 border-t-2 border-linea pt-3">
              <div className="flex justify-between text-tinta-2">
                <span>Subtotal</span>
                <span className="cifra">{moneda(recibo.subtotal)}</span>
              </div>
              {recibo.descuento ? (
                <div className="flex justify-between text-tinta-2">
                  <span>Descuento {Math.round((recibo.descuento * 1000) / recibo.subtotal) / 10} %</span>
                  <span className="cifra">-{moneda(recibo.descuento)}</span>
                </div>
              ) : null}
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-semibold">Total</span>
                <span className="cifra text-2xl font-bold">{moneda(recibo.total)}</span>
              </div>
              <div className="text-sm text-tinta-2">
                Pago: {recibo.pagos.map((p) => `${p.metodo_nombre} ${moneda(p.monto)}`).join(", ")}
              </div>
              {recibo.estado === "anulada" ? (
                <Aviso>
                  Anulada por {recibo.anulada_por}: {recibo.motivo_anulacion}
                </Aviso>
              ) : null}
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal titulo="Cerrar la caja" abierto={cerrando} onCerrar={() => setCerrando(false)}>
        <form onSubmit={cerrarCaja} className="space-y-4">
          <div className="flex items-baseline justify-between gap-3 rounded-lg bg-cal px-4 py-3">
            <span className="text-tinta-2">Debe haber en caja</span>
            <span className="cifra text-2xl font-bold text-tinta">{moneda(turno.esperado_en_caja)}</span>
          </div>
          <Campo
            etiqueta="Efectivo contado"
            type="number"
            min={0}
            inputMode="numeric"
            className="cifra text-lg"
            required
            value={contado}
            onChange={(e) => setContado(e.target.value)}
          />
          {contado ? (
            <Aviso tipo={Number(contado) === turno.esperado_en_caja ? "bien" : "info"}>
              Diferencia: <span className="cifra font-semibold">{moneda(Number(contado) - turno.esperado_en_caja)}</span>
            </Aviso>
          ) : null}
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
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

function FilaCaja({ texto, valor }: { texto: string; valor: number }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-tinta-2">{texto}</dt>
      <dd className="cifra">{moneda(valor)}</dd>
    </div>
  );
}

function LineaVenta({
  linea,
  lotes,
  alCambiar,
  alSumar,
  alQuitar,
}: {
  linea: Linea;
  lotes: Lote[];
  alCambiar: (campo: keyof Linea, valor: string) => void;
  alSumar: (paso: number) => void;
  alQuitar: () => void;
}) {
  const porKilo = linea.producto.cobro_por === "kg";
  const pideLote = linea.producto.clase !== "huevo" && linea.producto.clase !== "otro";
  const botonCantidad =
    "grid h-11 w-11 shrink-0 place-items-center rounded-lg font-cifra text-2xl font-bold text-tinta ring-[1.5px] ring-linea ring-inset transition hover:bg-cal active:bg-cal-honda";

  return (
    <li className="space-y-3 py-3.5 first:pt-0">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-base font-bold text-tinta">{linea.producto.nombre}</p>
          <p className="text-sm text-tinta-2">
            {moneda(linea.producto.precio ?? 0)}
            {porKilo ? " por kg" : ` por ${NOMBRE_PRESENTACION[linea.producto.presentacion]}`}
          </p>
        </div>
        <button
          onClick={alQuitar}
          className="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-tinta-2 transition hover:bg-alerta-suave hover:text-alerta"
          aria-label={`Quitar ${linea.producto.nombre}`}
        >
          <Icono nombre="cerrar" className="h-5 w-5" />
        </button>
      </div>

      <div className="flex items-end justify-between gap-3">
        {porKilo ? (
          <div className="w-32">
            <Campo
              etiqueta="Kilos"
              type="number"
              min={0}
              step="0.001"
              inputMode="decimal"
              className="cifra"
              value={linea.cantidad}
              onChange={(e) => alCambiar("cantidad", e.target.value)}
            />
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <button type="button" className={botonCantidad} onClick={() => alSumar(-1)} aria-label="Quitar uno">
              −
            </button>
            <input
              type="number"
              min={0}
              step="1"
              inputMode="numeric"
              aria-label="Cantidad"
              value={linea.cantidad}
              onChange={(e) => alCambiar("cantidad", e.target.value)}
              className="cifra h-11 w-16 rounded-lg border-[1.5px] border-linea bg-superficie text-center text-lg font-bold text-tinta focus:border-galpon focus:ring-3 focus:ring-galpon/15 focus:outline-none"
            />
            <button type="button" className={botonCantidad} onClick={() => alSumar(1)} aria-label="Agregar uno">
              +
            </button>
          </div>
        )}
        <p className="cifra pb-2 text-lg font-bold text-tinta">
          {moneda(Number(linea.cantidad || 0) * Number(linea.producto.precio ?? 0))}
        </p>
      </div>

      {linea.producto.clase === "ave_engorde" || pideLote ? (
        <div className="grid gap-2 sm:grid-cols-2">
          {linea.producto.clase === "ave_engorde" ? (
            <Campo
              etiqueta="Cuantas aves"
              type="number"
              min={1}
              inputMode="numeric"
              value={linea.aves}
              onChange={(e) => alCambiar("aves", e.target.value)}
            />
          ) : null}
          {pideLote ? (
            <Lista etiqueta="Lote" value={linea.lote_id} onChange={(e) => alCambiar("lote_id", e.target.value)}>
              <option value="">Elige el lote</option>
              {lotes
                .filter((l) => (linea.producto.clase === "ave_descarte" ? l.aves_descarte > 0 : l.proposito === "engorde"))
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
      ) : null}
    </li>
  );
}
