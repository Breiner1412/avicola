"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Galpon, Rutina, Tarea, Usuario } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tarjeta, Vacio } from "@/componentes/ui";

const DIAS = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"];
const PRIORIDADES = [
  { valor: "alta", texto: "Alta" },
  { valor: "media", texto: "Media" },
  { valor: "baja", texto: "Baja" },
];
const ESTADOS = [
  { valor: "pendiente", texto: "Pendiente" },
  { valor: "en_proceso", texto: "En proceso" },
  { valor: "hecha", texto: "Hecha" },
  { valor: "cancelada", texto: "Cancelada" },
];

function hoy() {
  return new Date().toISOString().slice(0, 10);
}

const TONO_PRIORIDAD: Record<string, "rojo" | "azul" | "gris"> = { alta: "rojo", media: "azul", baja: "gris" };

export default function Tareas() {
  const { sesion, puede } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;
  const [recargas, setRecargas] = useState(0);
  const [dia, setDia] = useState(hoy());
  const [verTodas, setVerTodas] = useState(false);

  const ruta = verTodas ? `/tareas?estado=pendiente` : `/tareas?desde=${dia}&hasta=${dia}`;
  const { datos, cargando, error, recargar } = useDatos<Tarea[]>(ruta, `${finca}-${ruta}-${recargas}`);
  const { datos: rutinas, recargar: recargarRutinas } = useDatos<Rutina[]>(
    puede("tareas", "crear") ? "/rutinas" : null,
    `${finca}-${recargas}`,
  );
  const { datos: usuarios } = useDatos<Usuario[]>(puede("usuarios", "ver") ? "/usuarios?incluir_inactivos=false" : null);
  const { datos: galpones } = useDatos<Galpon[]>("/galpones", finca);

  const [abierto, setAbierto] = useState(false);
  const [rutinaAbierta, setRutinaAbierta] = useState(false);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [tarea, setTarea] = useState({
    titulo: "",
    descripcion: "",
    fecha: hoy(),
    hora: "",
    prioridad: "media",
    asignado_a: "",
    galpon_id: "",
  });
  const [rutina, setRutina] = useState({
    titulo: "",
    descripcion: "",
    frecuencia: "diaria",
    dias_semana: [] as number[],
    dia_mes: "",
    hora: "",
    prioridad: "media",
    asignado_a: "",
  });

  async function guardarTarea(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      await api("/tareas", {
        metodo: "POST",
        cuerpo: {
          titulo: tarea.titulo,
          descripcion: tarea.descripcion || null,
          fecha: tarea.fecha,
          hora: tarea.hora || null,
          prioridad: tarea.prioridad,
          asignado_a: tarea.asignado_a ? Number(tarea.asignado_a) : null,
          galpon_id: tarea.galpon_id ? Number(tarea.galpon_id) : null,
        },
      });
      setAbierto(false);
      setTarea({ ...tarea, titulo: "", descripcion: "", hora: "" });
      setRecargas((n) => n + 1);
      await recargar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function guardarRutina(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      await api("/rutinas", {
        metodo: "POST",
        cuerpo: {
          titulo: rutina.titulo,
          descripcion: rutina.descripcion || null,
          frecuencia: rutina.frecuencia,
          dias_semana: rutina.dias_semana,
          dia_mes: rutina.dia_mes ? Number(rutina.dia_mes) : null,
          hora: rutina.hora || null,
          prioridad: rutina.prioridad,
          asignado_a: rutina.asignado_a ? Number(rutina.asignado_a) : null,
        },
      });
      setRutinaAbierta(false);
      setRutina({ ...rutina, titulo: "", descripcion: "", dias_semana: [], dia_mes: "" });
      setRecargas((n) => n + 1);
      await recargarRutinas();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function generar() {
    try {
      const salida = await api<{ creadas: number }>("/rutinas/generar", { metodo: "POST", cuerpo: { fecha: dia } });
      setRecargas((n) => n + 1);
      await recargar();
      alert(salida.creadas ? `Se crearon ${salida.creadas} tarea(s) de rutina.` : "Las tareas de hoy ya estaban creadas.");
    } catch (error) {
      alert(mensajeDeError(error));
    }
  }

  async function cambiarEstado(fila: Tarea, estado: string) {
    try {
      await api(`/tareas/${fila.id}`, { metodo: "PATCH", cuerpo: { estado } });
      setRecargas((n) => n + 1);
      await recargar();
    } catch (error) {
      alert(mensajeDeError(error));
    }
  }

  const pendientes = (datos ?? []).filter((t) => t.estado !== "hecha" && t.estado !== "cancelada");
  const listas = (datos ?? []).filter((t) => t.estado === "hecha" || t.estado === "cancelada");

  function Tarjetita({ fila }: { fila: Tarea }) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="font-medium text-slate-800">{fila.titulo}</p>
            <p className="text-xs text-slate-500">
              {fila.fecha}
              {fila.hora ? ` · ${fila.hora}` : ""}
              {fila.asignado_nombre ? ` · ${fila.asignado_nombre}` : " · sin asignar"}
              {fila.rutina_id ? " · rutina" : ""}
            </p>
          </div>
          <Insignia tono={TONO_PRIORIDAD[fila.prioridad]}>{fila.prioridad}</Insignia>
        </div>

        {fila.descripcion ? <p className="mt-2 text-sm text-slate-600">{fila.descripcion}</p> : null}
        {fila.notas ? <p className="mt-1 text-xs text-slate-500">Nota: {fila.notas}</p> : null}
        {fila.terminada_por ? (
          <p className="mt-1 text-xs text-emerald-700">Hecha por {fila.terminada_por}</p>
        ) : null}

        {puede("tareas", "editar") ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {fila.estado !== "hecha" ? (
              <>
                {fila.estado === "pendiente" ? (
                  <Boton tono="suave" onClick={() => cambiarEstado(fila, "en_proceso")}>
                    Empezar
                  </Boton>
                ) : null}
                <Boton onClick={() => cambiarEstado(fila, "hecha")}>Marcar hecha</Boton>
              </>
            ) : (
              <Boton tono="suave" onClick={() => cambiarEstado(fila, "pendiente")}>
                Reabrir
              </Boton>
            )}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Tareas</h1>
          <p className="text-sm text-slate-500">Lo que hay que hacer hoy en {sesion?.finca_activa?.nombre}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {puede("tareas", "crear") ? (
            <>
              <Boton tono="suave" onClick={generar}>
                Generar rutinas del dia
              </Boton>
              <Boton tono="suave" onClick={() => setRutinaAbierta(true)}>
                Nueva rutina
              </Boton>
              <Boton onClick={() => setAbierto(true)}>Nueva tarea</Boton>
            </>
          ) : null}
        </div>
      </div>

      <Tarjeta>
        <div className="flex flex-wrap items-end gap-3">
          <Campo etiqueta="Dia" type="date" value={dia} onChange={(e) => setDia(e.target.value)} disabled={verTodas} />
          <label className="flex items-center gap-2 pb-2 text-sm text-slate-600">
            <input type="checkbox" checked={verTodas} onChange={(e) => setVerTodas(e.target.checked)} />
            Ver todas las pendientes
          </label>
        </div>
      </Tarjeta>

      {error ? <Aviso>{error}</Aviso> : null}
      {cargando ? <Cargando /> : null}

      {!cargando && pendientes.length === 0 && listas.length === 0 ? (
        <Tarjeta>
          <Vacio>No hay tareas para este dia.</Vacio>
        </Tarjeta>
      ) : null}

      {pendientes.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {pendientes.map((fila) => (
            <Tarjetita key={fila.id} fila={fila} />
          ))}
        </div>
      ) : null}

      {listas.length > 0 ? (
        <Tarjeta titulo="Ya hechas">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {listas.map((fila) => (
              <Tarjetita key={fila.id} fila={fila} />
            ))}
          </div>
        </Tarjeta>
      ) : null}

      {rutinas && rutinas.length > 0 ? (
        <Tarjeta titulo="Rutinas">
          <ul className="space-y-2 text-sm">
            {rutinas.map((fila) => (
              <li key={fila.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                <span>
                  <span className="font-medium text-slate-700">{fila.titulo}</span>
                  <span className="block text-xs text-slate-500">
                    {fila.frecuencia === "diaria"
                      ? "Todos los dias"
                      : fila.frecuencia === "semanal"
                        ? (fila.dias_semana ?? []).map((d) => DIAS[d]).join(", ")
                        : `Cada mes el dia ${fila.dia_mes}`}
                    {fila.hora ? ` · ${fila.hora}` : ""}
                  </span>
                </span>
                {fila.activo ? <Insignia tono="verde">Activa</Insignia> : <Insignia>Inactiva</Insignia>}
              </li>
            ))}
          </ul>
        </Tarjeta>
      ) : null}

      <Modal titulo="Nueva tarea" abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardarTarea} className="space-y-4">
          <Campo
            etiqueta="Que hay que hacer"
            required
            value={tarea.titulo}
            onChange={(e) => setTarea({ ...tarea, titulo: e.target.value })}
          />
          <Campo
            etiqueta="Detalle"
            value={tarea.descripcion}
            onChange={(e) => setTarea({ ...tarea, descripcion: e.target.value })}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Fecha"
              type="date"
              required
              value={tarea.fecha}
              onChange={(e) => setTarea({ ...tarea, fecha: e.target.value })}
            />
            <Campo etiqueta="Hora" type="time" value={tarea.hora} onChange={(e) => setTarea({ ...tarea, hora: e.target.value })} />
            <Lista
              etiqueta="Prioridad"
              value={tarea.prioridad}
              onChange={(e) => setTarea({ ...tarea, prioridad: e.target.value })}
            >
              {PRIORIDADES.map((p) => (
                <option key={p.valor} value={p.valor}>
                  {p.texto}
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="Quien la hace"
              value={tarea.asignado_a}
              onChange={(e) => setTarea({ ...tarea, asignado_a: e.target.value })}
            >
              <option value="">Sin asignar</option>
              {(usuarios ?? []).map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nombres} {u.apellidos}
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="Galpon"
              value={tarea.galpon_id}
              onChange={(e) => setTarea({ ...tarea, galpon_id: e.target.value })}
            >
              <option value="">Toda la finca</option>
              {(galpones ?? []).map((g) => (
                <option key={g.id} value={g.id}>
                  {g.nombre}
                </option>
              ))}
            </Lista>
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

      <Modal titulo="Nueva rutina" abierto={rutinaAbierta} onCerrar={() => setRutinaAbierta(false)}>
        <form onSubmit={guardarRutina} className="space-y-4">
          <Aviso tipo="info">
            Una rutina es una tarea que se repite. Con el boton &quot;Generar rutinas del dia&quot; se crean las tareas
            que toquen ese dia.
          </Aviso>
          <Campo
            etiqueta="Que hay que hacer"
            required
            value={rutina.titulo}
            onChange={(e) => setRutina({ ...rutina, titulo: e.target.value })}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Lista
              etiqueta="Cada cuanto"
              value={rutina.frecuencia}
              onChange={(e) => setRutina({ ...rutina, frecuencia: e.target.value })}
            >
              <option value="diaria">Todos los dias</option>
              <option value="semanal">Algunos dias de la semana</option>
              <option value="mensual">Una vez al mes</option>
            </Lista>
            <Campo etiqueta="Hora" type="time" value={rutina.hora} onChange={(e) => setRutina({ ...rutina, hora: e.target.value })} />
          </div>

          {rutina.frecuencia === "semanal" ? (
            <div className="flex flex-wrap gap-2">
              {DIAS.map((nombre, indice) => (
                <label key={nombre} className="flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-sm">
                  <input
                    type="checkbox"
                    checked={rutina.dias_semana.includes(indice)}
                    onChange={(e) =>
                      setRutina({
                        ...rutina,
                        dias_semana: e.target.checked
                          ? [...rutina.dias_semana, indice]
                          : rutina.dias_semana.filter((d) => d !== indice),
                      })
                    }
                  />
                  {nombre}
                </label>
              ))}
            </div>
          ) : null}

          {rutina.frecuencia === "mensual" ? (
            <Campo
              etiqueta="Dia del mes"
              type="number"
              min={1}
              max={31}
              value={rutina.dia_mes}
              onChange={(e) => setRutina({ ...rutina, dia_mes: e.target.value })}
            />
          ) : null}

          <Lista
            etiqueta="Quien la hace"
            value={rutina.asignado_a}
            onChange={(e) => setRutina({ ...rutina, asignado_a: e.target.value })}
          >
            <option value="">Sin asignar</option>
            {(usuarios ?? []).map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombres} {u.apellidos}
              </option>
            ))}
          </Lista>

          {fallo ? <Aviso>{fallo}</Aviso> : null}
          <div className="flex justify-end gap-2">
            <Boton type="button" tono="suave" onClick={() => setRutinaAbierta(false)}>
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
