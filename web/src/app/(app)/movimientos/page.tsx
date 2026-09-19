"use client";

import { Fragment, useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Articulo, Bodega, Movimiento, Pagina, Proveedor, TipoMovimiento } from "@/lib/tipos";
import {
  Aviso,
  Boton,
  Campo,
  Cargando,
  Insignia,
  Lista,
  Modal,
  Paginador,
  Tabla,
  Tarjeta,
  Vacio,
} from "@/componentes/ui";
import { fecha, hoy } from "@/lib/formato";
import { avisar, useDialogos } from "@/componentes/dialogos";

type Linea = { articulo_id: string; cantidad: string; costo_unitario: string; lote: string; vencimiento: string };

const LINEA_VACIA: Linea = { articulo_id: "", cantidad: "", costo_unitario: "", lote: "", vencimiento: "" };

const TIPOS: { valor: TipoMovimiento; texto: string; ayuda: string }[] = [
  { valor: "entrada", texto: "Entrada", ayuda: "Compra o recibo de articulos" },
  { valor: "salida", texto: "Salida", ayuda: "Consumo, perdida o uso en la finca" },
  { valor: "traslado", texto: "Traslado", ayuda: "Mover articulos entre dos bodegas" },
  { valor: "ajuste", texto: "Ajuste por conteo", ayuda: "Dejar la cantidad igual a lo que se conto" },
];

const MOTIVOS_SALIDA = ["consumo", "uso en finca", "perdida", "dano", "vencido", "prestamo", "otro"];

export default function Movimientos() {
  const { pedirTexto } = useDialogos();
  const { sesion, puede } = useSesion();
  const [tipo, setTipo] = useState("");
  const [bodegaFiltro, setBodegaFiltro] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [pagina, setPagina] = useState(1);
  const [abiertoDetalle, setAbiertoDetalle] = useState<number | null>(null);

  const parametros = new URLSearchParams({ pagina: String(pagina), tamano: "25" });
  if (tipo) parametros.set("tipo", tipo);
  if (bodegaFiltro) parametros.set("bodega_id", bodegaFiltro);
  if (desde) parametros.set("desde", desde);
  if (hasta) parametros.set("hasta", hasta);
  const ruta = `/movimientos?${parametros.toString()}`;

  const { datos, cargando, error, recargar } = useDatos<Pagina<Movimiento>>(ruta, ruta);
  const { datos: bodegas } = useDatos<Bodega[]>("/bodegas", sesion?.finca_activa?.id ?? 0);
  const { datos: articulos } = useDatos<Articulo[]>("/articulos");
  const { datos: proveedores } = useDatos<Proveedor[]>(puede("proveedores", "ver") ? "/proveedores" : null);

  const [abierto, setAbierto] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [fallo, setFallo] = useState("");
  const [cabecera, setCabecera] = useState({
    tipo: "entrada" as TipoMovimiento,
    fecha: hoy(),
    bodega_id: "",
    bodega_destino_id: "",
    proveedor_id: "",
    motivo: "",
    documento: "",
    observaciones: "",
  });
  const [lineas, setLineas] = useState<Linea[]>([{ ...LINEA_VACIA }]);

  const paginas = datos ? Math.max(1, Math.ceil(datos.total / datos.tamano)) : 1;

  function abrir() {
    setFallo("");
    setCabecera({
      tipo: "entrada",
      fecha: hoy(),
      bodega_id: bodegas?.[0] ? String(bodegas[0].id) : "",
      bodega_destino_id: "",
      proveedor_id: "",
      motivo: "",
      documento: "",
      observaciones: "",
    });
    setLineas([{ ...LINEA_VACIA }]);
    setAbierto(true);
  }

  function cambiarLinea(indice: number, campo: keyof Linea, valor: string) {
    setLineas((actuales) => actuales.map((linea, i) => (i === indice ? { ...linea, [campo]: valor } : linea)));
  }

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setFallo("");

    const items = lineas
      .filter((linea) => linea.articulo_id && linea.cantidad !== "")
      .map((linea) => ({
        articulo_id: Number(linea.articulo_id),
        cantidad: Number(linea.cantidad),
        costo_unitario: Number(linea.costo_unitario || 0),
        lote: linea.lote || null,
        vencimiento: linea.vencimiento || null,
      }));

    if (items.length === 0) {
      setFallo("Agrega al menos un articulo");
      return;
    }

    setGuardando(true);
    try {
      await api("/movimientos", {
        metodo: "POST",
        cuerpo: {
          tipo: cabecera.tipo,
          fecha: cabecera.fecha,
          bodega_id: Number(cabecera.bodega_id),
          bodega_destino_id: cabecera.tipo === "traslado" ? Number(cabecera.bodega_destino_id) : null,
          proveedor_id: cabecera.tipo === "entrada" && cabecera.proveedor_id ? Number(cabecera.proveedor_id) : null,
          motivo: cabecera.motivo || null,
          documento: cabecera.documento || null,
          observaciones: cabecera.observaciones || null,
          items,
        },
      });
      setAbierto(false);
      await recargar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function anular(movimiento: Movimiento) {
    const motivo = await pedirTexto({
      titulo: "Anular el movimiento",
      mensaje: "Las existencias vuelven a quedar como estaban. El movimiento queda en el historial como anulado.",
      etiqueta: "Por que se anula?",
      aceptar: "Anular",
      peligro: true,
      requerido: true,
    });
    if (!motivo || motivo.length < 3) return;
    try {
      await api(`/movimientos/${movimiento.id}/anular`, { metodo: "POST", cuerpo: { motivo } });
      await recargar();
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  const unidadDe = (articuloId: string) => articulos?.find((a) => String(a.id) === articuloId)?.unidad ?? "";

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Entradas y salidas</h1>
          <p className="text-sm text-slate-500">Todo movimiento queda registrado; si hay un error, se anula.</p>
        </div>
        {puede("movimientos_inventario", "crear") ? <Boton onClick={abrir}>Nuevo movimiento</Boton> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        <div className="mb-4 grid gap-3 sm:grid-cols-4">
          <Lista
            etiqueta="Tipo"
            value={tipo}
            onChange={(e) => {
              setTipo(e.target.value);
              setPagina(1);
            }}
          >
            <option value="">Todos</option>
            {TIPOS.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.texto}
              </option>
            ))}
          </Lista>
          <Lista
            etiqueta="Bodega"
            value={bodegaFiltro}
            onChange={(e) => {
              setBodegaFiltro(e.target.value);
              setPagina(1);
            }}
          >
            <option value="">Todas</option>
            {(bodegas ?? []).map((bodega) => (
              <option key={bodega.id} value={bodega.id}>
                {bodega.nombre}
              </option>
            ))}
          </Lista>
          <Campo etiqueta="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
          <Campo etiqueta="Hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </div>

        {cargando ? (
          <Cargando />
        ) : !datos || datos.datos.length === 0 ? (
          <Vacio>No hay movimientos con esos filtros.</Vacio>
        ) : (
          <>
            <Tabla columnas={["Fecha", "Tipo", "Bodega", "Articulos", "Valor", "Registro", ""]}>
              {datos.datos.map((movimiento) => (
                <Fragment key={movimiento.id}>
                  <tr className={movimiento.anulado ? "bg-slate-50 text-slate-400" : "hover:bg-slate-50"}>
                    <td className="whitespace-nowrap px-3 py-2">{fecha(movimiento.fecha)}</td>
                    <td className="px-3 py-2 capitalize">
                      {movimiento.tipo}
                      {movimiento.anulado ? (
                        <span className="ml-2">
                          <Insignia tono="rojo">Anulado</Insignia>
                        </span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2">
                      {movimiento.bodega_nombre}
                      {movimiento.bodega_destino_nombre ? ` → ${movimiento.bodega_destino_nombre}` : ""}
                    </td>
                    <td className="px-3 py-2">{movimiento.items.length}</td>
                    <td className="px-3 py-2">
                      {movimiento.total ? `$${movimiento.total.toLocaleString("es-CO")}` : "-"}
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-500">{movimiento.usuario_nombre ?? "-"}</td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex justify-end gap-2">
                        <Boton
                          tono="suave"
                          onClick={() => setAbiertoDetalle(abiertoDetalle === movimiento.id ? null : movimiento.id)}
                        >
                          {abiertoDetalle === movimiento.id ? "Ocultar" : "Ver"}
                        </Boton>
                        {puede("movimientos_inventario", "editar") && !movimiento.anulado ? (
                          <Boton tono="peligro" onClick={() => anular(movimiento)}>
                            Anular
                          </Boton>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                  {abiertoDetalle === movimiento.id ? (
                    <tr>
                      <td colSpan={7} className="bg-slate-50 px-5 py-3">
                        <ul className="space-y-1 text-sm">
                          {movimiento.items.map((item) => (
                            <li key={item.id} className="flex flex-wrap justify-between gap-2">
                              <span>
                                {item.articulo_codigo} · {item.articulo_nombre}
                                {item.lote ? ` · lote ${item.lote}` : ""}
                                {item.vencimiento ? ` · vence ${item.vencimiento}` : ""}
                              </span>
                              <span className="text-slate-600">
                                {item.cantidad.toLocaleString("es-CO")} {item.unidad}
                                {movimiento.tipo === "ajuste"
                                  ? ` (diferencia ${item.cantidad_aplicada.toLocaleString("es-CO")})`
                                  : ""}
                                {item.costo_unitario ? ` · $${item.costo_unitario.toLocaleString("es-CO")}` : ""}
                              </span>
                            </li>
                          ))}
                        </ul>
                        <p className="mt-2 text-xs text-slate-500">
                          {movimiento.motivo ? `Motivo: ${movimiento.motivo}. ` : ""}
                          {movimiento.documento ? `Documento: ${movimiento.documento}. ` : ""}
                          {movimiento.observaciones ?? ""}
                          {movimiento.anulado
                            ? ` Anulado por ${movimiento.anulado_por}: ${movimiento.motivo_anulacion}`
                            : ""}
                        </p>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </Tabla>

            <Paginador
              pagina={pagina}
              paginas={paginas}
              total={datos.total}
              porPagina={datos.tamano}
              setPagina={setPagina}
              nombre="movimientos"
            />
          </>
        )}
      </Tarjeta>

      <Modal titulo="Nuevo movimiento" abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <Lista
            etiqueta="Que vas a registrar"
            value={cabecera.tipo}
            onChange={(e) => setCabecera({ ...cabecera, tipo: e.target.value as TipoMovimiento, motivo: "" })}
          >
            {TIPOS.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.texto} — {t.ayuda}
              </option>
            ))}
          </Lista>

          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Fecha"
              type="date"
              required
              value={cabecera.fecha}
              onChange={(e) => setCabecera({ ...cabecera, fecha: e.target.value })}
            />
            <Lista
              etiqueta={cabecera.tipo === "traslado" ? "Bodega de origen" : "Bodega"}
              required
              value={cabecera.bodega_id}
              onChange={(e) => setCabecera({ ...cabecera, bodega_id: e.target.value })}
            >
              <option value="">Elige una bodega</option>
              {(bodegas ?? []).map((bodega) => (
                <option key={bodega.id} value={bodega.id}>
                  {bodega.nombre}
                  {bodega.es_central ? " (central)" : ""}
                </option>
              ))}
            </Lista>

            {cabecera.tipo === "traslado" ? (
              <Lista
                etiqueta="Bodega de destino"
                required
                value={cabecera.bodega_destino_id}
                onChange={(e) => setCabecera({ ...cabecera, bodega_destino_id: e.target.value })}
              >
                <option value="">Elige una bodega</option>
                {(bodegas ?? [])
                  .filter((bodega) => String(bodega.id) !== cabecera.bodega_id)
                  .map((bodega) => (
                    <option key={bodega.id} value={bodega.id}>
                      {bodega.nombre}
                    </option>
                  ))}
              </Lista>
            ) : null}

            {cabecera.tipo === "entrada" ? (
              <>
                <Lista
                  etiqueta="Proveedor"
                  value={cabecera.proveedor_id}
                  onChange={(e) => setCabecera({ ...cabecera, proveedor_id: e.target.value })}
                >
                  <option value="">Sin proveedor</option>
                  {(proveedores ?? []).map((proveedor) => (
                    <option key={proveedor.id} value={proveedor.id}>
                      {proveedor.nombre}
                    </option>
                  ))}
                </Lista>
                <Campo
                  etiqueta="Factura o remision"
                  value={cabecera.documento}
                  onChange={(e) => setCabecera({ ...cabecera, documento: e.target.value })}
                />
              </>
            ) : null}

            {cabecera.tipo === "salida" ? (
              <Lista
                etiqueta="Motivo"
                required
                value={cabecera.motivo}
                onChange={(e) => setCabecera({ ...cabecera, motivo: e.target.value })}
              >
                <option value="">Elige un motivo</option>
                {MOTIVOS_SALIDA.map((motivo) => (
                  <option key={motivo} value={motivo}>
                    {motivo}
                  </option>
                ))}
              </Lista>
            ) : null}

            {cabecera.tipo === "ajuste" ? (
              <Campo
                etiqueta="Motivo del ajuste"
                required
                placeholder="Conteo fisico del mes"
                value={cabecera.motivo}
                onChange={(e) => setCabecera({ ...cabecera, motivo: e.target.value })}
              />
            ) : null}
          </div>

          <div className="space-y-3 rounded-lg border border-slate-200 p-3">
            <p className="text-sm font-medium text-slate-700">
              {cabecera.tipo === "ajuste" ? "Cantidad contada de cada articulo" : "Articulos"}
            </p>

            {lineas.map((linea, indice) => (
              <div key={indice} className="grid gap-2 sm:grid-cols-12">
                <div className="sm:col-span-5">
                  <Lista
                    etiqueta={indice === 0 ? "Articulo" : ""}
                    value={linea.articulo_id}
                    onChange={(e) => cambiarLinea(indice, "articulo_id", e.target.value)}
                  >
                    <option value="">Elige un articulo</option>
                    {(articulos ?? []).map((articulo) => (
                      <option key={articulo.id} value={articulo.id}>
                        {articulo.codigo} · {articulo.nombre}
                      </option>
                    ))}
                  </Lista>
                </div>
                <div className="sm:col-span-3">
                  <Campo
                    etiqueta={indice === 0 ? `Cantidad ${unidadDe(linea.articulo_id)}` : ""}
                    type="number"
                    min={0}
                    step="0.001"
                    value={linea.cantidad}
                    onChange={(e) => cambiarLinea(indice, "cantidad", e.target.value)}
                  />
                </div>
                <div className="sm:col-span-3">
                  <Campo
                    etiqueta={indice === 0 ? "Costo unitario" : ""}
                    type="number"
                    min={0}
                    step="0.01"
                    disabled={cabecera.tipo !== "entrada"}
                    value={linea.costo_unitario}
                    onChange={(e) => cambiarLinea(indice, "costo_unitario", e.target.value)}
                  />
                </div>
                <div className="flex items-end sm:col-span-1">
                  <button
                    type="button"
                    onClick={() => setLineas((actuales) => actuales.filter((_, i) => i !== indice))}
                    disabled={lineas.length === 1}
                    className="mb-1 rounded p-2 text-slate-400 hover:bg-slate-100 disabled:opacity-40"
                    aria-label="Quitar"
                  >
                    ✕
                  </button>
                </div>

                {cabecera.tipo === "entrada" ? (
                  <>
                    <div className="sm:col-span-6">
                      <Campo
                        etiqueta="Lote (opcional)"
                        value={linea.lote}
                        onChange={(e) => cambiarLinea(indice, "lote", e.target.value)}
                      />
                    </div>
                    <div className="sm:col-span-6">
                      <Campo
                        etiqueta="Vencimiento (opcional)"
                        type="date"
                        value={linea.vencimiento}
                        onChange={(e) => cambiarLinea(indice, "vencimiento", e.target.value)}
                      />
                    </div>
                  </>
                ) : null}
              </div>
            ))}

            <Boton
              type="button"
              tono="suave"
              onClick={() => setLineas((actuales) => [...actuales, { ...LINEA_VACIA }])}
            >
              Agregar otro articulo
            </Boton>
          </div>

          <Campo
            etiqueta="Observaciones"
            value={cabecera.observaciones}
            onChange={(e) => setCabecera({ ...cabecera, observaciones: e.target.value })}
          />

          {fallo ? <Aviso>{fallo}</Aviso> : null}

          <div className="flex justify-end gap-2">
            <Boton type="button" tono="suave" onClick={() => setAbierto(false)}>
              Cancelar
            </Boton>
            <Boton type="submit" disabled={guardando}>
              {guardando ? "Guardando..." : "Guardar"}
            </Boton>
          </div>
        </form>
      </Modal>
    </>
  );
}
