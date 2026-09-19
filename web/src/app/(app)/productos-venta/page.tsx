"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { PrecioHistorial, ProductoVenta, TipoHuevo } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";
import { avisar } from "@/componentes/dialogos";

const CLASES = [
  { valor: "huevo", texto: "Huevos" },
  { valor: "ave_descarte", texto: "Gallinas de descarte" },
  { valor: "ave_engorde", texto: "Aves de engorde" },
  { valor: "otro", texto: "Otro" },
];

const PRESENTACIONES = [
  { valor: "unidad", texto: "Por unidad" },
  { valor: "docena", texto: "Docena (12)" },
  { valor: "medio_panal", texto: "Medio panal (15)" },
  { valor: "panal", texto: "Panal (30)" },
  { valor: "kg", texto: "Por kilo" },
];

const moneda = (valor: number) => `$${Math.round(valor).toLocaleString("es-CO")}`;

const VACIO = { nombre: "", clase: "huevo", presentacion: "panal", tipo_huevo_id: "", precio: "" };

export default function ProductosVenta() {
  const { puede } = useSesion();
  const [recargas, setRecargas] = useState(0);
  const { datos, cargando, error, recargar } = useDatos<ProductoVenta[]>(
    "/productos-venta?incluir_inactivos=true",
    recargas,
  );
  const { datos: tipos } = useDatos<TipoHuevo[]>("/tipos-huevo");

  const [abierto, setAbierto] = useState(false);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  const [precioDe, setPrecioDe] = useState<ProductoVenta | null>(null);
  const [nuevoPrecio, setNuevoPrecio] = useState("");
  const { datos: historial } = useDatos<PrecioHistorial[]>(
    precioDe ? `/precios?producto_id=${precioDe.id}` : null,
    `${precioDe?.id ?? 0}-${recargas}`,
  );

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      await api("/productos-venta", {
        metodo: "POST",
        cuerpo: {
          nombre: formulario.nombre,
          clase: formulario.clase,
          presentacion: formulario.clase === "ave_engorde" ? "kg" : formulario.presentacion,
          tipo_huevo_id: formulario.tipo_huevo_id ? Number(formulario.tipo_huevo_id) : null,
          precio: formulario.precio ? Number(formulario.precio) : null,
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

  async function cambiarPrecio(evento: React.FormEvent) {
    evento.preventDefault();
    if (!precioDe) return;
    try {
      await api("/precios", {
        metodo: "POST",
        cuerpo: { producto_id: precioDe.id, precio: Number(nuevoPrecio) },
      });
      setNuevoPrecio("");
      setRecargas((n) => n + 1);
      await recargar();
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  async function cambiarEstado(producto: ProductoVenta) {
    try {
      await api(`/productos-venta/${producto.id}`, { metodo: "PATCH", cuerpo: { activo: !producto.activo } });
      setRecargas((n) => n + 1);
      await recargar();
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Productos y precios</h1>
          <p className="text-sm text-slate-500">
            Como se vende cada cosa: huevos por unidad, docena, medio panal o panal; gallinas de descarte por unidad y
            engorde por kilo.
          </p>
        </div>
        {puede("productos_venta", "crear") ? <Boton onClick={() => setAbierto(true)}>Nuevo producto</Boton> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>Todavia no hay productos.</Vacio>
        ) : (
          <Tabla columnas={["Producto", "Tipo", "Presentacion", "Se cobra", "Precio", "Estado", ""]}>
            {datos.map((producto) => (
              <tr key={producto.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">{producto.nombre}</td>
                <td className="px-3 py-2">
                  {CLASES.find((c) => c.valor === producto.clase)?.texto ?? producto.clase}
                  {producto.tipo_huevo ? <span className="block text-xs text-slate-500">{producto.tipo_huevo}</span> : null}
                </td>
                <td className="px-3 py-2">
                  {PRESENTACIONES.find((p) => p.valor === producto.presentacion)?.texto}
                  {producto.factor > 1 ? (
                    <span className="block text-xs text-slate-500">{producto.factor} huevos</span>
                  ) : null}
                </td>
                <td className="px-3 py-2">{producto.cobro_por === "kg" ? "por kilo" : "por unidad"}</td>
                <td className="px-3 py-2 font-medium">
                  {producto.precio !== null ? moneda(producto.precio) : <Insignia tono="rojo">sin precio</Insignia>}
                </td>
                <td className="px-3 py-2">
                  {producto.activo ? <Insignia tono="verde">Activo</Insignia> : <Insignia>Inactivo</Insignia>}
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    {puede("precios", "editar") ? (
                      <Boton tono="suave" onClick={() => setPrecioDe(producto)}>
                        Precio
                      </Boton>
                    ) : null}
                    {puede("productos_venta", "editar") ? (
                      <Boton tono={producto.activo ? "peligro" : "suave"} onClick={() => cambiarEstado(producto)}>
                        {producto.activo ? "Desactivar" : "Activar"}
                      </Boton>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      <Modal titulo="Nuevo producto" abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <Campo
            etiqueta="Nombre"
            required
            placeholder="Panal de huevo AAA"
            value={formulario.nombre}
            onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Lista
              etiqueta="Que se vende"
              value={formulario.clase}
              onChange={(e) => setFormulario({ ...formulario, clase: e.target.value })}
            >
              {CLASES.map((c) => (
                <option key={c.valor} value={c.valor}>
                  {c.texto}
                </option>
              ))}
            </Lista>

            {formulario.clase === "huevo" ? (
              <Lista
                etiqueta="Tipo de huevo"
                required
                value={formulario.tipo_huevo_id}
                onChange={(e) => setFormulario({ ...formulario, tipo_huevo_id: e.target.value })}
              >
                <option value="">Elige el tipo</option>
                {(tipos ?? [])
                  .filter((t) => t.comercial)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.nombre}
                    </option>
                  ))}
              </Lista>
            ) : null}

            {formulario.clase !== "ave_engorde" ? (
              <Lista
                etiqueta="Presentacion"
                value={formulario.presentacion}
                onChange={(e) => setFormulario({ ...formulario, presentacion: e.target.value })}
              >
                {PRESENTACIONES.filter((p) => formulario.clase === "huevo" || p.valor !== "panal").map((p) => (
                  <option key={p.valor} value={p.valor}>
                    {p.texto}
                  </option>
                ))}
              </Lista>
            ) : (
              <Aviso tipo="info">Las aves de engorde se cobran por kilo.</Aviso>
            )}

            <Campo
              etiqueta="Precio"
              type="number"
              min={0}
              value={formulario.precio}
              onChange={(e) => setFormulario({ ...formulario, precio: e.target.value })}
            />
          </div>

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

      <Modal titulo={`Precio de ${precioDe?.nombre ?? ""}`} abierto={Boolean(precioDe)} onCerrar={() => setPrecioDe(null)}>
        <form onSubmit={cambiarPrecio} className="space-y-4">
          <Campo
            etiqueta="Precio nuevo"
            type="number"
            min={0}
            required
            value={nuevoPrecio}
            onChange={(e) => setNuevoPrecio(e.target.value)}
          />
          <Boton type="submit">Guardar precio</Boton>

          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">Historial</p>
            {!historial || historial.length === 0 ? (
              <Vacio>Sin precios anteriores.</Vacio>
            ) : (
              <ul className="space-y-1 text-sm">
                {historial.map((precio) => (
                  <li key={precio.id} className="flex justify-between border-b border-slate-100 py-1">
                    <span>
                      {moneda(precio.precio)}
                      {precio.hasta ? null : (
                        <span className="ml-2">
                          <Insignia tono="verde">vigente</Insignia>
                        </span>
                      )}
                    </span>
                    <span className="text-xs text-slate-500">
                      desde {precio.desde}
                      {precio.hasta ? ` hasta ${precio.hasta}` : ""} · {precio.usuario_nombre ?? ""}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </form>
      </Modal>
    </>
  );
}
