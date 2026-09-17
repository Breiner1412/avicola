"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Articulo, CategoriaArticulo } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

const UNIDADES = ["unidad", "kg", "litro", "bulto", "dosis", "metro"];
const CLASES = ["", "alimento", "vacuna", "medicamento", "herramienta", "repuesto", "insumo", "otro"];

const VACIO = {
  codigo: "",
  nombre: "",
  categoria_id: "",
  unidad: "unidad",
  kg_por_bulto: "",
  stock_minimo: "0",
  observaciones: "",
};

export default function Articulos() {
  const { puede } = useSesion();
  const [buscar, setBuscar] = useState("");
  const [clase, setClase] = useState("");
  const [soloBajos, setSoloBajos] = useState(false);

  const parametros = new URLSearchParams();
  if (buscar) parametros.set("buscar", buscar);
  if (clase) parametros.set("clase", clase);
  if (soloBajos) parametros.set("solo_bajo_minimo", "true");
  const ruta = `/articulos${parametros.toString() ? `?${parametros.toString()}` : ""}`;

  const { datos, cargando, error, recargar } = useDatos<Articulo[]>(ruta, ruta);
  const { datos: categorias, recargar: recargarCategorias } = useDatos<CategoriaArticulo[]>("/categorias-articulo");

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<Articulo | null>(null);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [nuevaCategoria, setNuevaCategoria] = useState("");

  function abrir(articulo?: Articulo) {
    setFallo("");
    setEditando(articulo ?? null);
    setFormulario(
      articulo
        ? {
            codigo: articulo.codigo,
            nombre: articulo.nombre,
            categoria_id: String(articulo.categoria_id),
            unidad: articulo.unidad,
            kg_por_bulto: articulo.kg_por_bulto ? String(articulo.kg_por_bulto) : "",
            stock_minimo: String(articulo.stock_minimo),
            observaciones: articulo.observaciones ?? "",
          }
        : { ...VACIO, categoria_id: categorias?.[0] ? String(categorias[0].id) : "" },
    );
    setAbierto(true);
  }

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    const cuerpo = {
      codigo: formulario.codigo,
      nombre: formulario.nombre,
      categoria_id: Number(formulario.categoria_id),
      unidad: formulario.unidad,
      kg_por_bulto: formulario.kg_por_bulto ? Number(formulario.kg_por_bulto) : null,
      stock_minimo: Number(formulario.stock_minimo || 0),
      observaciones: formulario.observaciones || null,
    };
    try {
      if (editando) await api(`/articulos/${editando.id}`, { metodo: "PATCH", cuerpo });
      else await api("/articulos", { metodo: "POST", cuerpo });
      setAbierto(false);
      await recargar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function crearCategoria() {
    if (nuevaCategoria.trim().length < 2) return;
    try {
      const creada = await api<CategoriaArticulo>("/categorias-articulo", {
        metodo: "POST",
        cuerpo: { nombre: nuevaCategoria.trim(), clase: "insumo" },
      });
      setNuevaCategoria("");
      await recargarCategorias();
      setFormulario((actual) => ({ ...actual, categoria_id: String(creada.id) }));
    } catch (error) {
      setFallo(mensajeDeError(error));
    }
  }

  async function desactivar(articulo: Articulo) {
    if (!confirm(`Desactivar ${articulo.nombre}?`)) return;
    try {
      await api(`/articulos/${articulo.id}`, { metodo: "DELETE" });
      await recargar();
    } catch (error) {
      alert(mensajeDeError(error));
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Articulos</h1>
          <p className="text-sm text-slate-500">Alimento, vacunas, medicamentos, herramientas, repuestos e insumos</p>
        </div>
        {puede("articulos", "crear") ? <Boton onClick={() => abrir()}>Nuevo articulo</Boton> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        <div className="mb-4 grid gap-3 sm:grid-cols-4">
          <Campo
            etiqueta="Buscar"
            placeholder="Nombre o codigo"
            value={buscar}
            onChange={(e) => setBuscar(e.target.value)}
          />
          <Lista etiqueta="Tipo" value={clase} onChange={(e) => setClase(e.target.value)}>
            {CLASES.map((valor) => (
              <option key={valor} value={valor}>
                {valor === "" ? "Todos" : valor}
              </option>
            ))}
          </Lista>
          <label className="flex items-end gap-2 pb-2 text-sm text-slate-600">
            <input type="checkbox" checked={soloBajos} onChange={(e) => setSoloBajos(e.target.checked)} />
            Solo los que estan bajo el minimo
          </label>
        </div>

        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>No hay articulos con esos filtros.</Vacio>
        ) : (
          <Tabla columnas={["Codigo", "Articulo", "Categoria", "Unidad", "Existencia", "Minimo", ""]}>
            {datos.map((articulo) => (
              <tr key={articulo.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 text-slate-500">{articulo.codigo}</td>
                <td className="px-3 py-2 font-medium text-slate-700">
                  {articulo.nombre}
                  {articulo.bajo_minimo ? (
                    <span className="ml-2">
                      <Insignia tono="rojo">Bajo minimo</Insignia>
                    </span>
                  ) : null}
                </td>
                <td className="px-3 py-2">{articulo.categoria_nombre}</td>
                <td className="px-3 py-2">
                  {articulo.unidad}
                  {articulo.kg_por_bulto ? ` · bulto de ${articulo.kg_por_bulto} kg` : ""}
                </td>
                <td className="px-3 py-2">{articulo.existencia_total.toLocaleString("es-CO")}</td>
                <td className="px-3 py-2 text-slate-500">{articulo.stock_minimo.toLocaleString("es-CO")}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    {puede("articulos", "editar") ? (
                      <Boton tono="suave" onClick={() => abrir(articulo)}>
                        Editar
                      </Boton>
                    ) : null}
                    {puede("articulos", "borrar") && articulo.activo ? (
                      <Boton tono="peligro" onClick={() => desactivar(articulo)}>
                        Desactivar
                      </Boton>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      <Modal titulo={editando ? "Editar articulo" : "Nuevo articulo"} abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Codigo"
              required
              maxLength={30}
              value={formulario.codigo}
              onChange={(e) => setFormulario({ ...formulario, codigo: e.target.value })}
            />
            <Campo
              etiqueta="Nombre"
              required
              value={formulario.nombre}
              onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
            />
            <Lista
              etiqueta="Categoria"
              value={formulario.categoria_id}
              onChange={(e) => setFormulario({ ...formulario, categoria_id: e.target.value })}
            >
              {(categorias ?? []).map((categoria) => (
                <option key={categoria.id} value={categoria.id}>
                  {categoria.nombre}
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="Unidad"
              value={formulario.unidad}
              onChange={(e) => setFormulario({ ...formulario, unidad: e.target.value })}
            >
              {UNIDADES.map((unidad) => (
                <option key={unidad} value={unidad}>
                  {unidad}
                </option>
              ))}
            </Lista>
            <Campo
              etiqueta="Kilos por bulto (solo alimento)"
              type="number"
              min={0}
              step="0.001"
              value={formulario.kg_por_bulto}
              onChange={(e) => setFormulario({ ...formulario, kg_por_bulto: e.target.value })}
            />
            <Campo
              etiqueta="Cantidad minima que debe haber"
              type="number"
              min={0}
              step="0.001"
              value={formulario.stock_minimo}
              onChange={(e) => setFormulario({ ...formulario, stock_minimo: e.target.value })}
            />
          </div>

          <Campo
            etiqueta="Observaciones"
            value={formulario.observaciones}
            onChange={(e) => setFormulario({ ...formulario, observaciones: e.target.value })}
          />

          {puede("articulos", "crear") ? (
            <div className="flex items-end gap-2 rounded-lg border border-dashed border-slate-300 p-3">
              <Campo
                etiqueta="Agregar una categoria nueva"
                value={nuevaCategoria}
                onChange={(e) => setNuevaCategoria(e.target.value)}
                className="flex-1"
              />
              <Boton type="button" tono="suave" onClick={crearCategoria}>
                Agregar
              </Boton>
            </div>
          ) : null}

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
