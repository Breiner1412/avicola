"use client";

import { useSesion } from "@/lib/sesion";
import { useDatos } from "@/lib/hooks";
import type { Resumen } from "@/lib/tipos";
import { Aviso, Cargando, Tarjeta } from "@/componentes/ui";

function Dato({ titulo, valor, detalle }: { titulo: string; valor: string | number; detalle?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-500">{titulo}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-800">{valor}</p>
      {detalle ? <p className="mt-1 text-xs text-slate-500">{detalle}</p> : null}
    </div>
  );
}

export default function Panel() {
  const { sesion } = useSesion();
  const { datos, cargando, error } = useDatos<Resumen>("/panel/resumen", sesion?.finca_activa?.id ?? 0);

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-slate-800">
          Hola, {sesion?.usuario.nombres}
        </h1>
        <p className="text-sm text-slate-500">
          Estas trabajando en {sesion?.finca_activa?.nombre} como {sesion?.usuario.rol_nombre.toLowerCase()}.
        </p>
      </div>

      {error ? <Aviso>{error}</Aviso> : null}
      {cargando ? <Cargando /> : null}

      {datos ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Dato titulo="Galpones activos" valor={datos.galpones_activos} />
          <Dato
            titulo="Aves en la finca"
            valor={datos.aves_en_finca.toLocaleString("es-CO")}
            detalle={`Capacidad ${datos.capacidad_finca.toLocaleString("es-CO")}`}
          />
          <Dato titulo="Ocupacion" valor={`${datos.ocupacion}%`} />
          <Dato titulo="Usuarios activos" valor={datos.usuarios_activos} detalle={`${datos.fincas_visibles} finca(s) visibles`} />
        </div>
      ) : null}

      <Tarjeta titulo="Siguientes pasos">
        <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
          <li>Registra los galpones de la finca.</li>
          <li>Crea los usuarios que van a trabajar y asignales su finca.</li>
          <li>Revisa los permisos de cada rol antes de empezar.</li>
        </ul>
      </Tarjeta>
    </>
  );
}
