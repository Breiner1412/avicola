import type { Metadata } from "next";
import "./globals.css";
import { ProveedorSesion } from "@/lib/sesion";

export const metadata: Metadata = {
  title: "AVISENA",
  description: "Gestion de granjas avicolas: fincas, galpones, aves, inventario y ventas.",
};

export default function RaizLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <ProveedorSesion>{children}</ProveedorSesion>
      </body>
    </html>
  );
}
