"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FalloApi } from "@/lib/api";
import { useSesion } from "@/lib/sesion";
import { Aviso, Boton, Campo, Cargando } from "@/componentes/ui";

export default function Login() {
  const { sesion, cargando, entrar } = useSesion();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (!cargando && sesion) router.replace("/panel");
  }, [cargando, sesion, router]);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setError("");
    setEnviando(true);
    try {
      await entrar(email.trim().toLowerCase(), clave);
      router.replace("/panel");
    } catch (fallo) {
      setError(fallo instanceof FalloApi ? fallo.message : "No se pudo iniciar sesion");
    } finally {
      setEnviando(false);
    }
  }

  if (cargando) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Cargando />
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-b from-emerald-800 to-emerald-950 px-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-xl">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold tracking-tight text-emerald-800">AVISENA</h1>
          <p className="mt-1 text-sm text-slate-500">Gestion de granjas avicolas</p>
        </div>

        <form onSubmit={enviar} className="space-y-4">
          <Campo
            etiqueta="Correo"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="tucorreo@ejemplo.com"
          />
          <Campo
            etiqueta="Contrasena"
            type="password"
            autoComplete="current-password"
            required
            value={clave}
            onChange={(e) => setClave(e.target.value)}
            placeholder="••••••••"
          />

          {error ? <Aviso>{error}</Aviso> : null}

          <Boton type="submit" disabled={enviando} className="w-full">
            {enviando ? "Entrando..." : "Entrar"}
          </Boton>
        </form>

        <p className="mt-6 text-center text-xs text-slate-400">
          Si olvidaste tu contrasena, pidele al administrador que te asigne una nueva.
        </p>
      </div>
    </main>
  );
}
