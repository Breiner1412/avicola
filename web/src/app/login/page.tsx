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
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-galpon px-4 py-10">
      <div className="flex items-center gap-3">
        <span aria-hidden="true" className="block h-12 w-10 rounded-[50%_50%_46%_46%/58%_58%_42%_42%] bg-yema" />
        <div>
          <h1 className="font-cifra text-[2.25rem] leading-none font-bold text-white [font-stretch:118%]">Avícola</h1>
          <p className="mt-1 text-base text-galpon-claro">Gestion de granjas avicolas</p>
        </div>
      </div>

      <div className="w-full max-w-sm rounded-xl bg-superficie p-6 shadow-[0_24px_60px_-20px_rgb(0_0_0/0.45)] sm:p-8">
        <h2 className="mb-5 font-cifra text-xl font-bold text-tinta [font-stretch:108%]">Entrar</h2>
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

          <Boton type="submit" tamano="grande" disabled={enviando} className="w-full">
            {enviando ? "Entrando..." : "Entrar"}
          </Boton>
        </form>

        <p className="mt-6 text-center text-sm text-tinta-2">
          Si olvidaste tu contrasena, pidele al administrador que te asigne una nueva.
        </p>
      </div>
    </main>
  );
}
