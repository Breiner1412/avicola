"use client";

import { useState } from "react";
import { useDatos } from "@/lib/hooks";
import type { LineaAuditoria, Pagina } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Lista, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

const ENTIDADES = ["", "usuarios", "fincas", "galpones", "cuentas", "permisos", "sesiones"];

export default function Auditoria() {
  const [entidad, setEntidad] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [pagina, setPagina] = useState(1);

  const parametros = new URLSearchParams({ pagina: String(pagina), tamano: "50" });
  if (entidad) parametros.set("entidad", entidad);
  if (desde) parametros.set("desde", desde);
  if (hasta) parametros.set("hasta", hasta);

  const ruta = `/auditoria?${parametros.toString()}`;
  const { datos, cargando, error } = useDatos<Pagina<LineaAuditoria>>(ruta, ruta);
  const paginas = datos ? Math.max(1, Math.ceil(datos.total / datos.tamano)) : 1;

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Registro de cambios</h1>
        <p className="text-sm text-slate-500">Quien hizo que y cuando. No se puede editar ni borrar.</p>
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        <div className="mb-4 grid gap-3 sm:grid-cols-4">
          <Lista
            etiqueta="Tipo de registro"
            value={entidad}
            onChange={(e) => {
              setEntidad(e.target.value);
              setPagina(1);
            }}
          >
            {ENTIDADES.map((valor) => (
              <option key={valor} value={valor}>
                {valor === "" ? "Todos" : valor}
              </option>
            ))}
          </Lista>
          <Campo etiqueta="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
          <Campo etiqueta="Hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </div>

        {cargando ? (
          <Cargando />
        ) : !datos || datos.datos.length === 0 ? (
          <Vacio>No hay movimientos registrados con esos filtros.</Vacio>
        ) : (
          <>
            <Tabla columnas={["Fecha", "Usuario", "Accion", "Tipo", "Detalle"]}>
              {datos.datos.map((linea) => (
                <tr key={linea.id} className="hover:bg-slate-50">
                  <td className="whitespace-nowrap px-3 py-2 text-slate-500">
                    {new Date(linea.creado_en).toLocaleString("es-CO")}
                  </td>
                  <td className="px-3 py-2">{linea.usuario_nombre ?? "-"}</td>
                  <td className="px-3 py-2 capitalize">{linea.accion.replace("_", " ")}</td>
                  <td className="px-3 py-2">{linea.entidad}</td>
                  <td className="px-3 py-2 text-slate-600">{linea.descripcion ?? "-"}</td>
                </tr>
              ))}
            </Tabla>

            <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
              <span>
                {datos.total} movimiento(s) · pagina {datos.pagina} de {paginas}
              </span>
              <div className="flex gap-2">
                <Boton tono="suave" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>
                  Anterior
                </Boton>
                <Boton tono="suave" disabled={pagina >= paginas} onClick={() => setPagina((p) => p + 1)}>
                  Siguiente
                </Boton>
              </div>
            </div>
          </>
        )}
      </Tarjeta>
    </>
  );
}
