"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSesion } from "@/lib/sesion";
import { Cargando } from "@/componentes/ui";

export default function Inicio() {
  const { sesion, cargando } = useSesion();
  const router = useRouter();

  useEffect(() => {
    if (cargando) return;
    router.replace(sesion ? "/panel" : "/login");
  }, [cargando, sesion, router]);

  return (
    <main className="flex min-h-screen items-center justify-center">
      <Cargando />
    </main>
  );
}
