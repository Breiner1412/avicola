"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type {
  Articulo,
  BalanceLote,
  Bodega,
  ConsumoAlimento,
  Galpon,
  MovimientoAves,
  Pesaje,
  Sanidad,
} from "@/lib/tipos";
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
  usePaginas,
} from "@/componentes/ui";
import { fecha, hoy } from "@/lib/formato";
import { avisar, useDialogos } from "@/componentes/dialogos";

const TIPOS_MOVIMIENTO = [
  { valor: "muerte", texto: "Mortalidad" },
  { valor: "descarte", texto: "Descarte (dejaron de producir)" },
  { valor: "venta", texto: "Venta de aves" },
  { valor: "fuga", texto: "Fuga" },
  { valor: "robo", texto: "Robo" },
  { valor: "consumo", texto: "Consumo en la finca" },
  { valor: "regalo", texto: "Regalo" },
  { valor: "ingreso", texto: "Ingreso de mas aves" },
  { valor: "traslado", texto: "Traslado a otro galpon" },
];

const PESTANAS = [
  { clave: "movimientos", texto: "Movimientos" },
  { clave: "alimento", texto: "Alimento" },
  { clave: "pesajes", texto: "Pesajes" },
  { clave: "sanidad", texto: "Vacunas" },
];

function Dato({ titulo, valor, detalle }: { titulo: string; valor: string | number; detalle?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-500">{titulo}</p>
      <p className="mt-1 text-xl font-semibold text-slate-800">{valor}</p>
      {detalle ? <p className="mt-0.5 text-xs text-slate-500">{detalle}</p> : null}
    </div>
  );
}

export default function DetalleLote() {
  const { confirmar, pedirTexto } = useDialogos();
  const parametros = useParams<{ id: string }>();
  const loteId = Number(parametros.id);
  const { puede } = useSesion();
  const [pestana, setPestana] = useState("movimientos");
  const [recargas, setRecargas] = useState(0);

  const { datos: balance, cargando, error, recargar } = useDatos<BalanceLote>(`/lotes/${loteId}/balance`, recargas);
  const { datos: movimientos, recargar: recargarMovimientos } = useDatos<MovimientoAves[]>(
    `/movimientos-aves?lote_id=${loteId}`,
    recargas,
  );
  const { datos: consumos, recargar: recargarConsumos } = useDatos<ConsumoAlimento[]>(
    `/consumo-alimento?lote_id=${loteId}`,
    recargas,
  );
  const { datos: pesajes, recargar: recargarPesajes } = useDatos<Pesaje[]>(`/pesajes?lote_id=${loteId}`, recargas);
  const { datos: sanidad } = useDatos<Sanidad[]>(
    puede("sanidad", "ver") ? `/sanidad?lote_id=${loteId}` : null,
    recargas,
  );
  const { datos: galpones } = useDatos<Galpon[]>("/galpones");
  const { datos: bodegas } = useDatos<Bodega[]>(puede("bodegas", "ver") ? "/bodegas" : null);
  const { datos: articulos } = useDatos<Articulo[]>(puede("articulos", "ver") ? "/articulos?clase=alimento" : null);
  const pagSanidad = usePaginas(sanidad, 15, "");
  const pagPesajes = usePaginas(pesajes, 15, "");
  const pagConsumos = usePaginas(consumos, 15, "");
  const pagMovimientos = usePaginas(movimientos, 15, "");

  const [modal, setModal] = useState<"" | "movimiento" | "alimento" | "pesaje">("");
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  const [movimiento, setMovimiento] = useState({
    tipo: "muerte",
    fecha: hoy(),
    cantidad: "",
    galpon_destino_id: "",
    peso_kg: "",
    motivo: "",
    observaciones: "",
  });
  const [alimento, setAlimento] = useState({
    fecha: hoy(),
    articulo_id: "",
    bodega_id: "",
    cantidad: "",
    observaciones: "",
  });
  const [pesaje, setPesaje] = useState({ fecha: hoy(), aves_muestra: "", peso_total_kg: "", observaciones: "" });

  async function refrescar() {
    setRecargas((n) => n + 1);
    await Promise.all([recargar(), recargarMovimientos(), recargarConsumos(), recargarPesajes()]);
  }

  async function guardarMovimiento(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      await api("/movimientos-aves", {
        metodo: "POST",
        cuerpo: {
          lote_id: loteId,
          fecha: movimiento.fecha,
          tipo: movimiento.tipo,
          cantidad: Number(movimiento.cantidad),
          galpon_destino_id: movimiento.tipo === "traslado" ? Number(movimiento.galpon_destino_id) : null,
          peso_kg: movimiento.peso_kg ? Number(movimiento.peso_kg) : null,
          motivo: movimiento.motivo || null,
          observaciones: movimiento.observaciones || null,
        },
      });
      setModal("");
      setMovimiento({ ...movimiento, cantidad: "", motivo: "", observaciones: "", peso_kg: "" });
      await refrescar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function guardarAlimento(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      await api("/consumo-alimento", {
        metodo: "POST",
        cuerpo: {
          lote_id: loteId,
          fecha: alimento.fecha,
          articulo_id: Number(alimento.articulo_id),
          bodega_id: Number(alimento.bodega_id),
          cantidad: Number(alimento.cantidad),
          observaciones: alimento.observaciones || null,
        },
      });
      setModal("");
      setAlimento({ ...alimento, cantidad: "", observaciones: "" });
      await refrescar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function guardarPesaje(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      await api("/pesajes", {
        metodo: "POST",
        cuerpo: {
          lote_id: loteId,
          fecha: pesaje.fecha,
          aves_muestra: Number(pesaje.aves_muestra),
          peso_total_kg: Number(pesaje.peso_total_kg),
          observaciones: pesaje.observaciones || null,
        },
      });
      setModal("");
      setPesaje({ ...pesaje, aves_muestra: "", peso_total_kg: "", observaciones: "" });
      await refrescar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function anularMovimiento(id: number) {
    const motivo = await pedirTexto({
      titulo: "Anular el movimiento",
      mensaje: "Las aves vuelven a quedar como estaban. El movimiento queda en el historial como anulado.",
      etiqueta: "Por que se anula?",
      aceptar: "Anular",
      peligro: true,
      requerido: true,
    });
    if (!motivo || motivo.length < 3) return;
    try {
      await api(`/movimientos-aves/${id}/anular`, { metodo: "POST", cuerpo: { motivo } });
      await refrescar();
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  async function cerrarLote() {
    const seguro = await confirmar({
      titulo: "Cerrar el lote",
      mensaje: "Solo se puede cerrar si ya no quedan aves. Despues no se le pueden registrar mas movimientos.",
      aceptar: "Cerrar lote",
    });
    if (!seguro) return;
    try {
      await api(`/lotes/${loteId}/cerrar`, { metodo: "POST", cuerpo: { fecha: hoy() } });
      await refrescar();
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  if (cargando) return <Cargando />;
  if (error) return <Aviso>{error}</Aviso>;
  if (!balance) return null;

  const lote = balance.lote;
  const moneda = (valor: number) => `$${Math.round(valor).toLocaleString("es-CO")}`;

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/lotes" className="text-sm text-emerald-700 hover:underline">
            ← Volver a los lotes
          </Link>
          <h1 className="mt-1 text-xl font-semibold text-slate-800">
            Lote {lote.codigo}
            {lote.estado === "cerrado" ? (
              <span className="ml-2">
                <Insignia>Cerrado</Insignia>
              </span>
            ) : null}
          </h1>
          <p className="text-sm text-slate-500">
            {lote.galpon_nombre} · {lote.raza_nombre ?? "sin raza"} · {lote.proposito} · {lote.edad_semanas} semanas
          </p>
        </div>
        <div className="flex gap-2">
          {puede("movimientos_aves", "crear") && lote.estado === "activo" ? (
            <Boton onClick={() => setModal("movimiento")}>Registrar aves</Boton>
          ) : null}
          {puede("alimentacion", "crear") && lote.estado === "activo" ? (
            <Boton tono="suave" onClick={() => setModal("alimento")}>
              Dar alimento
            </Boton>
          ) : null}
          {puede("pesajes", "crear") && lote.estado === "activo" ? (
            <Boton tono="suave" onClick={() => setModal("pesaje")}>
              Pesar
            </Boton>
          ) : null}
          {puede("lotes", "editar") && lote.estado === "activo" ? (
            <Boton tono="peligro" onClick={cerrarLote}>
              Cerrar lote
            </Boton>
          ) : null}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Dato
          titulo="Aves"
          valor={lote.aves_actuales.toLocaleString("es-CO")}
          detalle={`Entraron ${lote.aves_iniciales.toLocaleString("es-CO")} · descarte ${lote.aves_descarte}`}
        />
        <Dato
          titulo="Mortalidad"
          valor={`${lote.mortalidad_porcentaje.toLocaleString("es-CO")}%`}
          detalle={`${lote.mortalidad.toLocaleString("es-CO")} aves`}
        />
        <Dato
          titulo="Alimento"
          valor={`${balance.alimento_kg.toLocaleString("es-CO")} kg`}
          detalle={`${balance.alimento_por_ave_kg} kg por ave · ${moneda(balance.alimento_costo)}`}
        />
        {lote.proposito === "engorde" ? (
          <Dato
            titulo="Peso promedio"
            valor={balance.peso_promedio_kg ? `${balance.peso_promedio_kg} kg` : "sin pesajes"}
            detalle={
              balance.conversion_alimenticia
                ? `Conversion ${balance.conversion_alimenticia} kg de alimento por kg de ave`
                : undefined
            }
          />
        ) : (
          <Dato
            titulo="Huevos"
            valor={balance.huevos_total.toLocaleString("es-CO")}
            detalle={`${Math.round(balance.huevos_por_dia).toLocaleString("es-CO")} por dia · postura ${balance.porcentaje_postura.toLocaleString("es-CO")}%`}
          />
        )}
      </div>

      <Tarjeta titulo="Costos hasta hoy">
        <div className="grid gap-4 sm:grid-cols-4">
          <Dato titulo="Aves" valor={moneda(balance.costo_aves)} />
          <Dato titulo="Alimento" valor={moneda(balance.alimento_costo)} />
          <Dato titulo="Sanidad" valor={moneda(balance.costo_sanidad)} />
          <Dato
            titulo="Costo por ave"
            valor={moneda(balance.costo_por_ave)}
            detalle={`Total ${moneda(balance.costo_total)}`}
          />
        </div>
      </Tarjeta>

      <div className="flex gap-2 border-b border-slate-200">
        {PESTANAS.map((p) => (
          <button
            key={p.clave}
            onClick={() => setPestana(p.clave)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm ${
              pestana === p.clave
                ? "border-emerald-700 font-medium text-emerald-800"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {p.texto}
          </button>
        ))}
      </div>

      {pestana === "movimientos" ? (
        <Tarjeta>
          {!movimientos || movimientos.length === 0 ? (
            <Vacio>Sin movimientos registrados.</Vacio>
          ) : (
            <>
              <Tabla columnas={["Fecha", "Tipo", "Cantidad", "Motivo", "Quien", ""]}>
                {pagMovimientos.visibles.map((m) => (
                  <tr key={m.id} className={m.anulado ? "text-slate-400" : "hover:bg-slate-50"}>
                    <td className="whitespace-nowrap px-3 py-2">{fecha(m.fecha)}</td>
                    <td className="px-3 py-2 capitalize">
                      {m.tipo}
                      {m.anulado ? (
                        <span className="ml-2">
                          <Insignia tono="rojo">Anulado</Insignia>
                        </span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2">{m.cantidad.toLocaleString("es-CO")}</td>
                    <td className="px-3 py-2 text-slate-500">{m.motivo ?? "-"}</td>
                    <td className="px-3 py-2 text-xs text-slate-500">{m.usuario_nombre ?? "-"}</td>
                    <td className="px-3 py-2 text-right">
                      {puede("movimientos_aves", "editar") && !m.anulado && m.tipo !== "ingreso" ? (
                        <Boton tono="peligro" onClick={() => anularMovimiento(m.id)}>
                          Anular
                        </Boton>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </Tabla>
              <Paginador {...pagMovimientos} nombre="movimientos" />
            </>
          )}
        </Tarjeta>
      ) : null}

      {pestana === "alimento" ? (
        <Tarjeta>
          {!consumos || consumos.length === 0 ? (
            <Vacio>Todavia no se ha registrado alimento para este lote.</Vacio>
          ) : (
            <>
              <Tabla columnas={["Fecha", "Alimento", "Cantidad", "Costo", "Quien"]}>
                {pagConsumos.visibles.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="whitespace-nowrap px-3 py-2">{fecha(c.fecha)}</td>
                    <td className="px-3 py-2">{c.articulo_nombre}</td>
                    <td className="px-3 py-2">
                      {c.cantidad.toLocaleString("es-CO")} {c.unidad}
                    </td>
                    <td className="px-3 py-2">{moneda(c.costo)}</td>
                    <td className="px-3 py-2 text-xs text-slate-500">{c.usuario_nombre ?? "-"}</td>
                  </tr>
                ))}
              </Tabla>
              <Paginador {...pagConsumos} nombre="registros" />
            </>
          )}
        </Tarjeta>
      ) : null}

      {pestana === "pesajes" ? (
        <Tarjeta>
          {!pesajes || pesajes.length === 0 ? (
            <Vacio>Sin pesajes registrados.</Vacio>
          ) : (
            <>
              <Tabla columnas={["Fecha", "Edad", "Aves pesadas", "Peso total", "Promedio"]}>
                {pagPesajes.visibles.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="whitespace-nowrap px-3 py-2">{fecha(p.fecha)}</td>
                    <td className="px-3 py-2">{p.edad_dias ? `${p.edad_dias} dias` : "-"}</td>
                    <td className="px-3 py-2">{p.aves_muestra}</td>
                    <td className="px-3 py-2">{p.peso_total_kg} kg</td>
                    <td className="px-3 py-2 font-medium text-slate-700">{p.peso_promedio_kg} kg</td>
                  </tr>
                ))}
              </Tabla>
              <Paginador {...pagPesajes} nombre="pesajes" />
            </>
          )}
        </Tarjeta>
      ) : null}

      {pestana === "sanidad" ? (
        <Tarjeta
          acciones={
            <Link href="/sanidad" className="text-sm text-emerald-700 hover:underline">
              Registrar
            </Link>
          }
        >
          {!sanidad || sanidad.length === 0 ? (
            <Vacio>Sin vacunas ni tratamientos registrados para este lote.</Vacio>
          ) : (
            <>
              <Tabla columnas={["Fecha", "Tipo", "Producto", "Via", "Aves", "Refuerzo"]}>
                {pagSanidad.visibles.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50">
                    <td className="whitespace-nowrap px-3 py-2">{fecha(s.fecha)}</td>
                    <td className="px-3 py-2 capitalize">{s.tipo}</td>
                    <td className="px-3 py-2 font-medium text-slate-700">{s.producto}</td>
                    <td className="px-3 py-2">{s.via}</td>
                    <td className="px-3 py-2">{s.aves_tratadas ?? "-"}</td>
                    <td className="px-3 py-2">{s.proximo_refuerzo ?? "-"}</td>
                  </tr>
                ))}
              </Tabla>
              <Paginador {...pagSanidad} nombre="aplicaciones" />
            </>
          )}
        </Tarjeta>
      ) : null}

      <Modal titulo="Registrar aves" abierto={modal === "movimiento"} onCerrar={() => setModal("")}>
        <form onSubmit={guardarMovimiento} className="space-y-4">
          <Lista
            etiqueta="Que paso"
            value={movimiento.tipo}
            onChange={(e) => setMovimiento({ ...movimiento, tipo: e.target.value })}
          >
            {TIPOS_MOVIMIENTO.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.texto}
              </option>
            ))}
          </Lista>

          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Fecha"
              type="date"
              required
              value={movimiento.fecha}
              onChange={(e) => setMovimiento({ ...movimiento, fecha: e.target.value })}
            />
            <Campo
              etiqueta="Cuantas aves"
              type="number"
              min={1}
              required
              value={movimiento.cantidad}
              onChange={(e) => setMovimiento({ ...movimiento, cantidad: e.target.value })}
            />
            {movimiento.tipo === "traslado" ? (
              <Lista
                etiqueta="Galpon de destino"
                required
                value={movimiento.galpon_destino_id}
                onChange={(e) => setMovimiento({ ...movimiento, galpon_destino_id: e.target.value })}
              >
                <option value="">Elige un galpon</option>
                {(galpones ?? [])
                  .filter((g) => g.id !== lote.galpon_id)
                  .map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.nombre}
                    </option>
                  ))}
              </Lista>
            ) : null}
            {movimiento.tipo === "venta" ? (
              <Campo
                etiqueta="Peso total (kg, opcional)"
                type="number"
                min={0}
                step="0.001"
                value={movimiento.peso_kg}
                onChange={(e) => setMovimiento({ ...movimiento, peso_kg: e.target.value })}
              />
            ) : null}
          </div>

          <Campo
            etiqueta="Motivo"
            placeholder="golpe de calor, dejaron de producir, ..."
            value={movimiento.motivo}
            onChange={(e) => setMovimiento({ ...movimiento, motivo: e.target.value })}
          />

          {movimiento.tipo === "descarte" ? (
            <Aviso tipo="info">
              Las aves de descarte quedan guardadas aparte para venderlas como salvamento; siguen contando en el galpon
              hasta que salgan.
            </Aviso>
          ) : null}

          {fallo ? <Aviso>{fallo}</Aviso> : null}

          <div className="flex justify-end gap-2">
            <Boton type="button" tono="suave" onClick={() => setModal("")}>
              Cancelar
            </Boton>
            <Boton type="submit" disabled={guardando}>
              {guardando ? "Guardando..." : "Guardar"}
            </Boton>
          </div>
        </form>
      </Modal>

      <Modal titulo="Dar alimento al lote" abierto={modal === "alimento"} onCerrar={() => setModal("")}>
        <form onSubmit={guardarAlimento} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Fecha"
              type="date"
              required
              value={alimento.fecha}
              onChange={(e) => setAlimento({ ...alimento, fecha: e.target.value })}
            />
            <Campo
              etiqueta="Cantidad (kg)"
              type="number"
              min={0}
              step="0.001"
              required
              value={alimento.cantidad}
              onChange={(e) => setAlimento({ ...alimento, cantidad: e.target.value })}
            />
            <Lista
              etiqueta="Alimento"
              required
              value={alimento.articulo_id}
              onChange={(e) => setAlimento({ ...alimento, articulo_id: e.target.value })}
            >
              <option value="">Elige el alimento</option>
              {(articulos ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nombre} ({a.existencia_total} {a.unidad})
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="De que bodega sale"
              required
              value={alimento.bodega_id}
              onChange={(e) => setAlimento({ ...alimento, bodega_id: e.target.value })}
            >
              <option value="">Elige la bodega</option>
              {(bodegas ?? []).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.nombre}
                </option>
              ))}
            </Lista>
          </div>

          <Campo
            etiqueta="Observaciones"
            value={alimento.observaciones}
            onChange={(e) => setAlimento({ ...alimento, observaciones: e.target.value })}
          />

          {fallo ? <Aviso>{fallo}</Aviso> : null}

          <div className="flex justify-end gap-2">
            <Boton type="button" tono="suave" onClick={() => setModal("")}>
              Cancelar
            </Boton>
            <Boton type="submit" disabled={guardando}>
              {guardando ? "Guardando..." : "Guardar"}
            </Boton>
          </div>
        </form>
      </Modal>

      <Modal titulo="Registrar un pesaje" abierto={modal === "pesaje"} onCerrar={() => setModal("")}>
        <form onSubmit={guardarPesaje} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <Campo
              etiqueta="Fecha"
              type="date"
              required
              value={pesaje.fecha}
              onChange={(e) => setPesaje({ ...pesaje, fecha: e.target.value })}
            />
            <Campo
              etiqueta="Aves pesadas"
              type="number"
              min={1}
              required
              value={pesaje.aves_muestra}
              onChange={(e) => setPesaje({ ...pesaje, aves_muestra: e.target.value })}
            />
            <Campo
              etiqueta="Peso total (kg)"
              type="number"
              min={0}
              step="0.001"
              required
              value={pesaje.peso_total_kg}
              onChange={(e) => setPesaje({ ...pesaje, peso_total_kg: e.target.value })}
            />
          </div>

          <Campo
            etiqueta="Observaciones"
            value={pesaje.observaciones}
            onChange={(e) => setPesaje({ ...pesaje, observaciones: e.target.value })}
          />

          {fallo ? <Aviso>{fallo}</Aviso> : null}

          <div className="flex justify-end gap-2">
            <Boton type="button" tono="suave" onClick={() => setModal("")}>
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
