import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { ProveedorSesion } from "@/lib/sesion";
import { ProveedorDialogos } from "@/componentes/dialogos";

// Las fuentes van dentro del repositorio: la imagen se construye sin internet
const fuenteTexto = localFont({
  src: [
    { path: "../fuentes/atkinson-next-latin-wght.woff2", weight: "200 800", style: "normal" },
    { path: "../fuentes/atkinson-next-latin-wght-italic.woff2", weight: "200 800", style: "italic" },
  ],
  variable: "--fuente-texto",
  display: "swap",
});

const fuenteCifra = localFont({
  src: "../fuentes/archivo-latin-wdth.woff2",
  weight: "100 900",
  variable: "--fuente-cifra",
  display: "swap",
  declarations: [{ prop: "font-stretch", value: "62% 125%" }],
});

export const metadata: Metadata = {
  title: "Avícola",
  description: "Gestion de granjas avicolas: fincas, galpones, aves, inventario, ventas y tareas.",
  manifest: "/manifest.webmanifest",
  applicationName: "Avícola",
  appleWebApp: { capable: true, title: "Avícola", statusBarStyle: "black-translucent" },
  icons: { apple: "/apple-icon.png" },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#1e4d3a",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RaizLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${fuenteTexto.variable} ${fuenteCifra.variable}`}>
      <body>
        <ProveedorSesion>
          <ProveedorDialogos>{children}</ProveedorDialogos>
        </ProveedorSesion>
      </body>
    </html>
  );
}
