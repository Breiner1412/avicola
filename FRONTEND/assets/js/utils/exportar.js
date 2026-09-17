// Utilidades compartidas para exportar tablas a CSV, Excel y PDF.
// Cada página solo define sus columnas: [{ header: "Título", key: "campo" | (fila) => valor }]

// Librerías incluidas en el proyecto (se cargan solo cuando se exporta)
const LIBRERIAS = {
  xlsx: "assets/plugins/xlsx/xlsx.full.min.js",
  jspdf: "assets/plugins/jspdf/jspdf.umd.min.js",
  autotable: "assets/plugins/jspdf/jspdf.plugin.autotable.min.js",
};

const scriptsCargados = new Map();

/** Carga un script externo una sola vez. */
export function cargarScript(src) {
  if (!scriptsCargados.has(src)) {
    scriptsCargados.set(
      src,
      new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.onload = resolve;
        script.onerror = () => {
          scriptsCargados.delete(src);
          reject(new Error(`No se pudo cargar ${src}`));
        };
        document.head.appendChild(script);
      })
    );
  }
  return scriptsCargados.get(src);
}

/** Descarga un contenido como archivo. */
export function descargarArchivo(contenido, tipoMime, nombreArchivo) {
  const blob = contenido instanceof Blob ? contenido : new Blob([contenido], { type: tipoMime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombreArchivo;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// Los textos llegan escapados desde apiClient (anti-XSS); en el archivo se restauran.
const ENTIDADES = { "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'" };
function desescapar(valor) {
  return typeof valor === "string" ? valor.replace(/&lt;|&gt;|&quot;|&#39;/g, (e) => ENTIDADES[e]) : valor;
}

function valorCelda(fila, columna) {
  const v = typeof columna.key === "function" ? columna.key(fila) : fila[columna.key];
  return v === null || v === undefined ? "" : desescapar(v);
}

function conExtension(nombre, extension) {
  return nombre.replace(/\.[^.]+$/, "") + extension;
}

/** Convierte filas a texto CSV. */
export function aCSV(filas, columnas) {
  const celda = (v) => `"${String(v).replace(/"/g, '""')}"`;
  const encabezado = columnas.map((c) => celda(c.header)).join(",");
  const cuerpo = filas.map((f) => columnas.map((c) => celda(valorCelda(f, c))).join(","));
  return [encabezado, ...cuerpo].join("\n");
}

export function exportarCSV(filas, columnas, nombreArchivo = "reporte.csv") {
  // El BOM (﻿) hace que Excel reconozca las tildes
  descargarArchivo("﻿" + aCSV(filas, columnas), "text/csv;charset=utf-8;", conExtension(nombreArchivo, ".csv"));
}

export async function exportarExcel(filas, columnas, nombreArchivo = "reporte.xlsx", hoja = "Datos") {
  try {
    await cargarScript(LIBRERIAS.xlsx);
  } catch (error) {
    console.warn("No se pudo cargar SheetJS; se exporta en CSV.", error);
    exportarCSV(filas, columnas, nombreArchivo);
    return;
  }
  const datos = filas.map((f) => Object.fromEntries(columnas.map((c) => [c.header, valorCelda(f, c)])));
  const ws = window.XLSX.utils.json_to_sheet(datos, { header: columnas.map((c) => c.header) });
  ws["!cols"] = columnas.map((c) => ({ wch: Math.max(12, String(c.header).length + 2) }));
  const wb = window.XLSX.utils.book_new();
  window.XLSX.utils.book_append_sheet(wb, ws, String(hoja).slice(0, 31));
  window.XLSX.writeFile(wb, conExtension(nombreArchivo, ".xlsx"));
}

export async function exportarPDF(filas, columnas, nombreArchivo = "reporte.pdf", titulo = "Reporte", subtitulos = []) {
  await cargarScript(LIBRERIAS.jspdf);
  await cargarScript(LIBRERIAS.autotable);

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: columnas.length > 6 ? "landscape" : "portrait" });

  doc.setFontSize(16);
  doc.text(titulo, 14, 15);
  doc.setFontSize(10);
  let y = 22;
  for (const linea of [...subtitulos, `Generado: ${new Date().toLocaleString("es-CO")}`]) {
    doc.text(String(linea), 14, y);
    y += 5;
  }

  doc.autoTable({
    head: [columnas.map((c) => c.header)],
    body: filas.map((f) => columnas.map((c) => String(valorCelda(f, c)))),
    startY: y + 2,
    styles: { fontSize: 9, cellPadding: 2 },
    headStyles: { fillColor: [40, 167, 69], textColor: 255, fontStyle: "bold" },
    alternateRowStyles: { fillColor: [245, 245, 245] },
    theme: "grid",
  });
  doc.save(conExtension(nombreArchivo, ".pdf"));
}

/** Atajo: exportar("csv" | "excel" | "pdf", filas, { columnas, nombre, titulo, hoja, subtitulos }) */
export async function exportar(formato, filas, { columnas, nombre = "reporte", titulo = "Reporte", hoja = "Datos", subtitulos = [] }) {
  if (!filas || filas.length === 0) {
    if (window.Swal) Swal.fire({ icon: "info", title: "No hay datos para exportar." });
    return;
  }
  try {
    if (formato === "csv") exportarCSV(filas, columnas, nombre);
    else if (formato === "excel") await exportarExcel(filas, columnas, nombre, hoja);
    else if (formato === "pdf") await exportarPDF(filas, columnas, nombre, titulo, subtitulos);
  } catch (error) {
    console.error("Error al exportar:", error);
    if (window.Swal) Swal.fire({ icon: "error", title: "No se pudo exportar", text: error.message });
  }
}
