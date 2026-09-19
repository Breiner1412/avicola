"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Galpon, Lote, Novedad } from "@/lib/tipos";
import {
  Aviso,
  Boton,
  Campo,
  Cargando,
  Insignia,
  Lista,
  Modal,
  Paginador,
  Tarjeta,
  Vacio,
  usePaginas,
} from "@/componentes/ui";
import { fecha, hoy } from "@/lib/formato";
import { avisar, useDialogos } from "@/componentes/dialogos";

const CATEGORIAS = [
  { valor: "infraestructura", texto: "Infraestructura (danos, techos, cercas)" },
  { valor: "clima", texto: "Clima (lluvia, vendaval, calor)" },
  { valor: "animales", texto: "Animales (plagas, depredadores)" },
  { valor: "servicios", texto: "Servicios (luz, agua, internet)" },
  { valor: "seguridad", texto: "Seguridad (robos, intrusos)" },
  { valor: "salud", texto: "Salud del lote" },
  { valor: "otro", texto: "Otro" },
];

const GRAVEDADES = [
  { valor: "alta", texto: "Alta" },
  { valor: "media", texto: "Media" },
  { valor: "baja", texto: "Baja" },
];

const TONO: Record<string, "rojo" | "azul" | "gris"> = { alta: "rojo", media: "azul", baja: "gris" };
const moneda = (valor: number) => `$${Math.round(valor).toLocaleString("es-CO")}`;

const VACIO = {
  fecha: hoy(),
  categoria: "infraestructura",
  subtipo: "",
  titulo: "",
  descripcion: "",
  gravedad: "media",
  galpon_id: "",
  lote_id: "",
  aves_afectadas: "",
  descontar_aves: false,
  costo_estimado: "",
  acciones: "",
};

export default function Novedades() {
  const { pedirTexto } = useDialogos();
  const { sesion, puede } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;
  const [recargas, setRecargas] = useState(0);
  const [estado, setEstado] = useState("");
  const [categoria, setCategoria] = useState("");

  const parametros = new URLSearchParams();
  if (estado) parametros.set("estado", estado);
  if (categoria) parametros.set("categoria", categoria);
  const ruta = `/novedades${parametros.toString() ? `?${parametros.toString()}` : ""}`;

  const { datos, cargando, error, recargar } = useDatos<Novedad[]>(ruta, `${finca}-${ruta}-${recargas}`);
  const { datos: galpones } = useDatos<Galpon[]>("/galpones", finca);
  const { datos: lotes } = useDatos<Lote[]>("/lotes?solo_activos=true", finca);
  const pagNovedades = usePaginas(datos, 10, ruta);

  const [abierto, setAbierto] = useState(false);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      await api("/novedades", {
        metodo: "POST",
        cuerpo: {
          fecha: formulario.fecha,
          categoria: formulario.categoria,
          subtipo: formulario.subtipo || null,
          titulo: formulario.titulo,
          descripcion: formulario.descripcion || null,
          gravedad: formulario.gravedad,
          galpon_id: formulario.galpon_id ? Number(formulario.galpon_id) : null,
          lote_id: formulario.lote_id ? Number(formulario.lote_id) : null,
          aves_afectadas: Number(formulario.aves_afectadas || 0),
          descontar_aves: formulario.descontar_aves,
          costo_estimado: Number(formulario.costo_estimado || 0),
          acciones: formulario.acciones || null,
        },
      });
      setAbierto(false);
      setFormulario(VACIO);
      setRecargas((n) => n + 1);
      await recargar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function cerrar(novedad: Novedad) {
    const acciones = await pedirTexto({
      titulo: "Cerrar la novedad",
      mensaje: novedad.titulo,
      etiqueta: "Que se hizo para resolverlo?",
      valor: novedad.acciones ?? "",
      placeholder: "Ej: se cambio la teja rota",
      aceptar: "Cerrar novedad",
      largo: true,
    });
    if (acciones === null) return;
    try {
      await api(`/novedades/${novedad.id}/cerrar`, { metodo: "POST", cuerpo: { acciones: acciones || null } });
      setRecargas((n) => n + 1);
      await recargar();
      avisar.bien("Novedad cerrada");
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Novedades</h1>
          <p className="text-sm text-slate-500">Lo que se sale de lo normal: danos, clima, servicios, plagas o robos</p>
        </div>
        {puede("novedades", "crear") ? <Boton onClick={() => setAbierto(true)}>Reportar novedad</Boton> : null}
      </div>

      <Tarjeta>
        <div className="grid gap-3 sm:grid-cols-3">
          <Lista etiqueta="Estado" value={estado} onChange={(e) => setEstado(e.target.value)}>
            <option value="">Todas</option>
            <option value="abierta">Abiertas</option>
            <option value="en_proceso">En proceso</option>
            <option value="cerrada">Cerradas</option>
          </Lista>
          <Lista etiqueta="Categoria" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
            <option value="">Todas</option>
            {CATEGORIAS.map((c) => (
              <option key={c.valor} value={c.valor}>
                {c.texto}
              </option>
            ))}
          </Lista>
        </div>
      </Tarjeta>

      {error ? <Aviso>{error}</Aviso> : null}
      {cargando ? <Cargando /> : null}

      {!cargando && (!datos || datos.length === 0) ? (
        <Tarjeta>
          <Vacio>No hay novedades registradas con esos filtros.</Vacio>
        </Tarjeta>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-2 [&>*]:min-w-0">
        {pagNovedades.visibles.map((novedad) => (
          <div
            key={novedad.id}
            className={`rounded-xl border bg-white p-4 shadow-sm ${
              novedad.estado === "cerrada" ? "border-slate-200 opacity-70" : "border-slate-200"
            }`}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-medium text-slate-800">{novedad.titulo}</p>
                <p className="text-xs text-slate-500">
                  {fecha(novedad.fecha)} · {CATEGORIAS.find((c) => c.valor === novedad.categoria)?.texto.split(" (")[0] ?? novedad.categoria}
                  {novedad.subtipo ? ` · ${novedad.subtipo}` : ""}
                  {novedad.reportado_por ? ` · ${novedad.reportado_por}` : ""}
                </p>
              </div>
              <div className="flex gap-2">
                <Insignia tono={TONO[novedad.gravedad]}>{novedad.gravedad}</Insignia>
                {novedad.estado === "cerrada" ? (
                  <Insignia tono="verde">Cerrada</Insignia>
                ) : (
                  <Insignia tono="azul">{novedad.estado === "abierta" ? "Abierta" : "En proceso"}</Insignia>
                )}
              </div>
            </div>

            {novedad.descripcion ? <p className="mt-2 text-sm text-slate-600">{novedad.descripcion}</p> : null}

            <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
              {novedad.aves_afectadas ? <span>{novedad.aves_afectadas} ave(s) afectadas</span> : null}
              {novedad.costo_estimado ? <span>Costo estimado {moneda(novedad.costo_estimado)}</span> : null}
            </div>

            {novedad.acciones ? <p className="mt-2 text-xs text-slate-600">Se hizo: {novedad.acciones}</p> : null}
            {novedad.cerrada_por ? (
              <p className="mt-1 text-xs text-emerald-700">Cerrada por {novedad.cerrada_por}</p>
            ) : null}

            {puede("novedades", "editar") && novedad.estado !== "cerrada" ? (
              <div className="mt-3">
                <Boton tono="suave" onClick={() => cerrar(novedad)}>
                  Cerrar novedad
                </Boton>
              </div>
            ) : null}
          </div>
        ))}
      </div>
      <Paginador {...pagNovedades} nombre="novedades" />

      <Modal titulo="Reportar una novedad" abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <Campo
            etiqueta="Que paso"
            required
            placeholder="Se volo parte del techo del galpon 1"
            value={formulario.titulo}
            onChange={(e) => setFormulario({ ...formulario, titulo: e.target.value })}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Fecha"
              type="date"
              required
              value={formulario.fecha}
              onChange={(e) => setFormulario({ ...formulario, fecha: e.target.value })}
            />
            <Lista
              etiqueta="Categoria"
              value={formulario.categoria}
              onChange={(e) => setFormulario({ ...formulario, categoria: e.target.value })}
            >
              {CATEGORIAS.map((c) => (
                <option key={c.valor} value={c.valor}>
                  {c.texto}
                </option>
              ))}
            </Lista>
            <Campo
              etiqueta="Tipo (como lo llaman ustedes)"
              placeholder="vendaval, corte de energia, ..."
              value={formulario.subtipo}
              onChange={(e) => setFormulario({ ...formulario, subtipo: e.target.value })}
            />
            <Lista
              etiqueta="Gravedad"
              value={formulario.gravedad}
              onChange={(e) => setFormulario({ ...formulario, gravedad: e.target.value })}
            >
              {GRAVEDADES.map((g) => (
                <option key={g.valor} value={g.valor}>
                  {g.texto}
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="Galpon"
              value={formulario.galpon_id}
              onChange={(e) => setFormulario({ ...formulario, galpon_id: e.target.value })}
            >
              <option value="">Toda la finca</option>
              {(galpones ?? []).map((g) => (
                <option key={g.id} value={g.id}>
                  {g.nombre}
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="Lote"
              value={formulario.lote_id}
              onChange={(e) => setFormulario({ ...formulario, lote_id: e.target.value })}
            >
              <option value="">Ninguno</option>
              {(lotes ?? []).map((l) => (
                <option key={l.id} value={l.id}>
                  {l.codigo} ({l.aves_actuales} aves)
                </option>
              ))}
            </Lista>
          </div>

          <Campo
            etiqueta="Detalle"
            value={formulario.descripcion}
            onChange={(e) => setFormulario({ ...formulario, descripcion: e.target.value })}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Aves afectadas"
              type="number"
              min={0}
              value={formulario.aves_afectadas}
              onChange={(e) => setFormulario({ ...formulario, aves_afectadas: e.target.value })}
            />
            <Campo
              etiqueta="Costo estimado"
              type="number"
              min={0}
              value={formulario.costo_estimado}
              onChange={(e) => setFormulario({ ...formulario, costo_estimado: e.target.value })}
            />
          </div>

          {Number(formulario.aves_afectadas || 0) > 0 && formulario.lote_id ? (
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={formulario.descontar_aves}
                onChange={(e) => setFormulario({ ...formulario, descontar_aves: e.target.checked })}
              />
              Esas aves murieron: descontarlas del lote
            </label>
          ) : null}

          <Campo
            etiqueta="Que se hizo o se va a hacer"
            value={formulario.acciones}
            onChange={(e) => setFormulario({ ...formulario, acciones: e.target.value })}
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
