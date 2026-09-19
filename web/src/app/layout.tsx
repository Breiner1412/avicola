import type { Metadata, Viewport } from "next";
import "./globals.css";
import { ProveedorSesion } from "@/lib/sesion";
import { ProveedorDialogos } from "@/componentes/dialogos";

export const metadata: Metadata = {
  title: "AVISENA",
  description: "Gestion de granjas avicolas: fincas, galpones, aves, inventario, ventas y tareas.",
  manifest: "/manifest.webmanifest",
  applicationName: "AVISENA",
  appleWebApp: { capable: true, title: "AVISENA", statusBarStyle: "black-translucent" },
  icons: { apple: "/apple-icon.png" },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#065f46",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RaizLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <ProveedorSesion>
          <ProveedorDialogos>{children}</ProveedorDialogos>
        </ProveedorSesion>
      </body>
    </html>
  );
}
