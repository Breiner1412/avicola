"use client";

import { useState } from "react";
import { api, FalloApi } from "@/lib/api";
import { useSesion } from "@/lib/sesion";
import { Aviso, Boton, Campo } from "@/componentes/ui";

export function CambiarClave({ obligatorio = false, onListo }: { obligatorio?: boolean; onListo?: () => void }) {
  const { recargar, salir } = useSesion();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [repetida, setRepetida] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setError("");
    if (nueva !== repetida) {
      setError("Las contrasenas nuevas no coinciden");
      return;
    }
    setEnviando(true);
    try {
      await api("/auth/cambiar-clave", { metodo: "POST", cuerpo: { clave_actual: actual, clave_nueva: nueva } });
      await recargar();
      onListo?.();
    } catch (fallo) {
      setError(fallo instanceof FalloApi ? fallo.message : "No se pudo cambiar la contrasena");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-4">
      {obligatorio ? <Aviso tipo="info">Por seguridad, cambia la contrasena que te entregaron.</Aviso> : null}
      <Campo etiqueta="Contrasena actual" type="password" required value={actual} onChange={(e) => setActual(e.target.value)} />
      <Campo
        etiqueta="Contrasena nueva"
        type="password"
        required
        minLength={8}
        value={nueva}
        onChange={(e) => setNueva(e.target.value)}
      />
      <Campo
        etiqueta="Repite la contrasena nueva"
        type="password"
        required
        minLength={8}
        value={repetida}
        onChange={(e) => setRepetida(e.target.value)}
      />
      {error ? <Aviso>{error}</Aviso> : null}
      <div className="flex gap-2">
        <Boton type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : "Guardar"}
        </Boton>
        {obligatorio ? (
          <Boton type="button" tono="suave" onClick={() => salir()}>
            Salir
          </Boton>
        ) : null}
      </div>
    </form>
  );
}
