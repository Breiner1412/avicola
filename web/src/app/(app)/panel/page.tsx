"use client";

import Link from "next/link";
import { useSesion } from "@/lib/sesion";
import { useDatos } from "@/lib/hooks";
import type { ResumenPanel } from "@/lib/tipos";
import { Barras } from "@/componentes/grafica";
import { Icono } from "@/componentes/iconos";
import { Panal, enPanales } from "@/componentes/panal";
import { Aviso, Cargando, CifraFranja, Encabezado, Franja, Insignia, Tabla, Tarjeta } from "@/componentes/ui";

const moneda = (valor: number) => `$${Math.round(valor).toLocaleString("es-CO")}`;
const numero = (valor: number) => valor.toLocaleString("es-CO");

const ACCESOS = [
  { modulo: "produccion", texto: "Recoger huevos", ruta: "/produccion", icono: "huevo" },
  { modulo: "ventas", texto: "Abrir la caja", ruta: "/caja", icono: "caja" },
  { modulo: "movimientos_aves", texto: "Registrar aves", ruta: "/lotes", icono: "lote" },
  { modulo: "novedades", texto: "Reportar novedad", ruta: "/novedades", icono: "novedad" },
  { modulo: "movimientos_inventario", texto: "Entrada de bodega", ruta: "/movimientos", icono: "movimiento" },
  { modulo: "sensores", texto: "Ver sensores", ruta: "/sensores", icono: "sensor" },
];

type Pendiente = { tono: "rojo" | "ambar" | "azul"; etiqueta: string; texto: string; ruta: string; enlace: string };

const BORDE_PENDIENTE: Record<Pendiente["tono"], string> = {
  rojo: "border-l-alerta",
  ambar: "border-l-yema-honda",
  azul: "border-l-info",
};

function saludo() {
  const hora = new Date().getHours();
  if (hora < 12) return "Buenos dias";
  if (hora < 19) return "Buenas tardes";
  return "Buenas noches";
}

/** Lo que pide atencion hoy, de lo mas urgente a lo menos. Vacio si todo esta en orden. */
function pendientes(datos: ResumenPanel): Pendiente[] {
  const lista: Pendiente[] = [];
  if (datos.tareas_atrasadas)
    lista.push({
      tono: "rojo",
      etiqueta: "Atrasadas",
      texto: `${datos.tareas_atrasadas} tarea(s) pasaron su fecha`,
      ruta: "/tareas",
      enlace: "Ver tareas",
    });
  if (datos.sensores_alerta)
    lista.push({
      tono: "ambar",
      etiqueta: "Por revisar",
      texto: `${datos.sensores_alerta} sensor(es) fuera del rango normal`,
      ruta: "/sensores",
      enlace: "Ver sensores",
    });
  if (datos.novedades_abiertas)
    lista.push({
      tono: "ambar",
      etiqueta: "Sin cerrar",
      texto: `${datos.novedades_abiertas} novedad(es) esperan respuesta`,
      ruta: "/novedades",
      enlace: "Ver novedades",
    });
  if (datos.alertas)
    lista.push({
      tono: "azul",
      etiqueta: "Avisos",
      texto: `${datos.alertas} aviso(s) del sistema`,
      ruta: "/alertas",
      enlace: "Ver avisos",
    });
  return lista;
}

export default function Panel() {
  const { sesion, puede } = useSesion();
  const { datos, cargando, error } = useDatos<ResumenPanel>("/panel/resumen", sesion?.finca_activa?.id ?? 0);

  const fechaLarga = new Date().toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long" });
  const hoy = fechaLarga.charAt(0).toUpperCase() + fechaLarga.slice(1);
  const accesos = ACCESOS.filter((acceso) => puede(acceso.modulo, "ver"));
  const puedeVender = puede("ventas", "ver");

  return (
    <div className="flex flex-col gap-6">
      <Encabezado
        titulo={`${saludo()}, ${sesion?.usuario.nombres ?? ""}`}
        descripcion={hoy}
        acciones={
          <>
            {sesion?.finca_activa?.solo_lectura ? <Insignia tono="azul">Estas viendo esta finca en solo consulta</Insignia> : null}
            {puedeVender ? (
              <Link
                href="/caja"
                className="hidden min-h-14 items-center gap-2 rounded-lg bg-yema px-6 text-lg font-semibold text-tinta shadow-[inset_0_-2px_0_var(--color-yema-honda)] transition hover:bg-yema-clara sm:inline-flex"
              >
                <Icono nombre="caja" className="h-5 w-5" />
                Abrir la caja
              </Link>
            ) : null}
          </>
        }
      />

      {error ? <Aviso>{error}</Aviso> : null}
      {cargando ? <Cargando /> : null}

      {datos ? <Resumen datos={datos} accesos={accesos} /> : null}
    </div>
  );
}

function Resumen({ datos, accesos }: { datos: ResumenPanel; accesos: typeof ACCESOS }) {
  const { panales, sueltos } = enPanales(datos.huevos_disponibles);
  const lista = pendientes(datos);

  return (
    <>
      <Franja className="grid max-md:order-1 lg:grid-cols-[1.5fr_1fr_1fr] [&>*+*]:border-t [&>*+*]:border-white/10 lg:[&>*+*]:border-t-0 lg:[&>*+*]:border-l">
        <CifraFranja
          titulo="Huevos disponibles"
          valor={numero(datos.huevos_disponibles)}
          detalle={`${numero(panales)} panales y ${sueltos} sueltos`}
        >
          <Panal llenos={sueltos} />
        </CifraFranja>
        <CifraFranja
          titulo="Aves en la finca"
          valor={numero(datos.aves_en_finca)}
          detalle={`${Math.round(datos.ocupacion)} % de la capacidad, ${datos.lotes_activos} lote(s)`}
        />
        <CifraFranja
          titulo={`Vendido en ${datos.dias} dias`}
          valor={moneda(datos.ventas_periodo)}
          detalle={`Promedio de ${numero(Math.round(datos.huevos_promedio))} huevos por dia`}
        />
      </Franja>

      {lista.length ? (
        <section aria-label="Pide atencion" className="grid gap-2 max-md:order-1">
          {lista.map((item) => (
            <div
              key={item.ruta}
              className={`flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-l-[5px] border-linea bg-superficie px-4 py-3 ${BORDE_PENDIENTE[item.tono]}`}
            >
              <Insignia tono={item.tono} punto>
                {item.etiqueta}
              </Insignia>
              <p className="min-w-[12rem] flex-1 text-base text-tinta">{item.texto}</p>
              <Link href={item.ruta} className="inline-flex min-h-11 items-center gap-1 font-semibold text-galpon hover:underline">
                {item.enlace}
                <Icono nombre="derecha" className="h-4 w-4" />
              </Link>
            </div>
          ))}
        </section>
      ) : null}

      {/* En el celular los accesos suben al principio: es lo que busca el operario */}
      {accesos.length ? (
        <nav aria-label="Accesos rapidos" className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-6">
          {accesos.map((acceso) => (
            <Link
              key={acceso.ruta + acceso.texto}
              href={acceso.ruta}
              className="flex min-h-[4.5rem] items-center gap-3 rounded-xl border-[1.5px] border-linea bg-superficie px-3.5 py-3 text-base font-semibold text-tinta transition hover:border-galpon active:bg-cal"
            >
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-cal text-galpon">
                <Icono nombre={acceso.icono} className="h-5 w-5" />
              </span>
              <span className="min-w-0 leading-snug">{acceso.texto}</span>
            </Link>
          ))}
        </nav>
      ) : null}

      <div className="grid gap-5 max-md:order-1 lg:grid-cols-3 [&>*]:min-w-0">
        <Tarjeta
          titulo="Huevos recolectados por dia"
          descripcion={`Ultimos ${datos.dias} dias, ${numero(datos.huevos_periodo)} en total`}
          className="lg:col-span-2"
        >
          <Barras datos={datos.produccion} etiqueta="huevos" />
        </Tarjeta>

        <Tarjeta titulo="Para hoy">
          <ul className="divide-y divide-linea-suave">
            <FilaHoy texto="Tareas de hoy" valor={datos.tareas_hoy} tono={datos.tareas_hoy ? "azul" : "verde"} />
            <FilaHoy texto="Tareas atrasadas" valor={datos.tareas_atrasadas} tono={datos.tareas_atrasadas ? "rojo" : "verde"} />
            <FilaHoy texto="Novedades sin cerrar" valor={datos.novedades_abiertas} tono={datos.novedades_abiertas ? "ambar" : "verde"} />
            <FilaHoy texto="Gallinas de descarte" valor={datos.aves_descarte} />
          </ul>
          <Link href="/tareas" className="mt-3 inline-flex min-h-11 items-center gap-1 font-semibold text-galpon hover:underline">
            Ver las tareas
            <Icono nombre="derecha" className="h-4 w-4" />
          </Link>
        </Tarjeta>

        <Tarjeta
          titulo="Ventas por dia"
          descripcion={`Ultimos ${datos.dias} dias, ${moneda(datos.ventas_periodo)} en total`}
          className="lg:col-span-2"
        >
          <Barras datos={datos.ventas} formato={(valor) => moneda(valor)} />
        </Tarjeta>

        <Tarjeta titulo="Sensores">
          {datos.sensores === 0 ? (
            <div className="text-base text-tinta-2">
              Todavia no hay sensores registrados en esta finca.
              <Link href="/sensores" className="mt-2 flex min-h-11 items-center font-semibold text-galpon hover:underline">
                Registrar el primero
              </Link>
            </div>
          ) : (
            <>
              <div className="flex items-baseline gap-2">
                <span className="cifra text-[2.5rem] leading-none font-bold text-tinta">{datos.sensores}</span>
                <span className="text-base text-tinta-2">midiendo la finca</span>
              </div>
              <p className="mt-3">
                {datos.sensores_alerta ? (
                  <Insignia tono="rojo" punto>
                    {datos.sensores_alerta} fuera del rango normal
                  </Insignia>
                ) : (
                  <Insignia tono="verde" punto>
                    Todos dentro del rango normal
                  </Insignia>
                )}
              </p>
              <Link href="/sensores" className="mt-3 inline-flex min-h-11 items-center gap-1 font-semibold text-galpon hover:underline">
                Ver los sensores
                <Icono nombre="derecha" className="h-4 w-4" />
              </Link>
            </>
          )}
        </Tarjeta>
      </div>

      {datos.otras_fincas?.length ? (
        <Tarjeta
          titulo="Las demas fincas de la empresa"
          descripcion={`Resumen general de los ultimos ${datos.dias} dias`}
          className="max-md:order-1"
        >
          <Tabla columnas={["Finca", "Aves", "Lotes activos", "Huevos del periodo"]} numericas={[1, 2, 3]}>
            {datos.otras_fincas.map((finca) => (
              <tr key={finca.id}>
                <td className="px-3 font-semibold">{finca.nombre}</td>
                <td className="cifra px-3 text-right">{numero(finca.aves)}</td>
                <td className="cifra px-3 text-right">{numero(finca.lotes_activos)}</td>
                <td className="cifra px-3 text-right">{numero(finca.huevos_periodo)}</td>
              </tr>
            ))}
          </Tabla>
        </Tarjeta>
      ) : null}
    </>
  );
}

function FilaHoy({ texto, valor, tono }: { texto: string; valor: number; tono?: "verde" | "rojo" | "ambar" | "azul" }) {
  return (
    <li className="flex min-h-12 items-center justify-between gap-3">
      <span className="text-base text-tinta">{texto}</span>
      {tono ? <Insignia tono={tono}>{numero(valor)}</Insignia> : <span className="cifra text-lg font-bold">{numero(valor)}</span>}
    </li>
  );
}
