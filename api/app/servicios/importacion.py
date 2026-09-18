"""Lectura de archivos de Excel o CSV y carga de sus datos al sistema.

No existe un formato fijo: el archivo se lee tal como viene, se muestran sus
columnas y el usuario dice cual corresponde a cada dato. Ese emparejamiento se
puede guardar como plantilla para la proxima vez.
"""

import csv
import io
import unicodedata
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from openpyxl import load_workbook

MAX_FILAS = 5000


# --------------------------- Campos por tipo ---------------------------
# (clave, etiqueta, obligatorio, sinonimos)
CAMPOS: dict[str, list[tuple[str, str, bool, list[str]]]] = {
    "articulos": [
        ("codigo", "Codigo", True, ["codigo", "cod", "referencia", "ref", "sku"]),
        ("nombre", "Nombre", True, ["nombre", "descripcion", "articulo", "producto", "item", "insumo"]),
        ("categoria", "Categoria", False, ["categoria", "tipo", "clase", "grupo", "linea"]),
        ("unidad", "Unidad", False, ["unidad", "medida", "um", "unidad de medida", "presentacion"]),
        ("kg_por_bulto", "Kilos por bulto", False, ["kg por bulto", "kilos por bulto", "peso bulto", "kg bulto"]),
        ("stock_minimo", "Cantidad minima", False, ["minimo", "stock minimo", "existencia minima", "min"]),
        ("observaciones", "Observaciones", False, ["observaciones", "notas", "nota", "comentario"]),
    ],
    "entrada_inventario": [
        ("articulo", "Articulo", True, ["articulo", "producto", "insumo", "nombre", "descripcion", "item"]),
        ("codigo", "Codigo del articulo", False, ["codigo", "cod", "referencia", "sku"]),
        ("cantidad", "Cantidad", True, ["cantidad", "cant", "kilos", "kg", "unidades", "bultos", "existencia"]),
        ("costo_unitario", "Costo unitario", False, ["costo", "precio", "valor unitario", "costo unitario", "vr unitario"]),
        ("fecha", "Fecha", False, ["fecha", "fecha compra", "fecha factura", "dia"]),
        ("documento", "Factura o remision", False, ["factura", "documento", "remision", "numero factura", "no factura"]),
        ("proveedor", "Proveedor", False, ["proveedor", "vendedor", "distribuidor"]),
        ("lote", "Lote del producto", False, ["lote", "lote producto", "serial"]),
        ("vencimiento", "Vencimiento", False, ["vencimiento", "vence", "fecha vencimiento", "caducidad"]),
        ("unidad", "Unidad", False, ["unidad", "medida", "um"]),
        ("categoria", "Categoria", False, ["categoria", "tipo", "clase", "grupo"]),
    ],
    "proveedores": [
        ("nombre", "Nombre", True, ["nombre", "proveedor", "razon social", "empresa"]),
        ("documento", "Documento", False, ["documento", "nit", "cedula", "identificacion", "cc"]),
        ("telefono", "Telefono", False, ["telefono", "celular", "contacto", "movil"]),
        ("email", "Correo", False, ["email", "correo", "correo electronico", "mail"]),
        ("direccion", "Direccion", False, ["direccion", "ubicacion"]),
    ],
    "sanidad": [
        ("fecha", "Fecha", True, ["fecha", "dia", "fecha aplicacion"]),
        ("producto", "Producto", True, ["producto", "vacuna", "medicamento", "biologico", "nombre", "tratamiento"]),
        ("tipo", "Tipo", False, ["tipo", "clase"]),
        ("lote", "Lote de aves", False, ["lote", "lote aves", "codigo lote"]),
        ("galpon", "Galpon", False, ["galpon", "caseta", "galera"]),
        ("dosis", "Dosis", False, ["dosis", "cantidad por ave"]),
        ("via", "Via", False, ["via", "aplicacion", "metodo", "forma"]),
        ("aves_tratadas", "Aves tratadas", False, ["aves", "aves tratadas", "poblacion", "cantidad aves"]),
        ("responsable", "Responsable", False, ["responsable", "aplicado por", "encargado", "quien aplico"]),
        ("lote_producto", "Lote del producto", False, ["lote producto", "lote del producto", "serial", "batch"]),
        ("proximo_refuerzo", "Proximo refuerzo", False, ["refuerzo", "proximo refuerzo", "proxima dosis", "revacunacion"]),
        ("observaciones", "Observaciones", False, ["observaciones", "notas", "comentario"]),
    ],
    "produccion": [
        ("fecha", "Fecha", True, ["fecha", "dia"]),
        ("lote", "Lote", True, ["lote", "codigo lote", "grupo"]),
        ("tipo_huevo", "Tipo de huevo", True, ["tipo", "tipo huevo", "clasificacion", "calibre", "tamano"]),
        ("cantidad", "Cantidad", True, ["cantidad", "huevos", "unidades", "total", "recolectados"]),
    ],
}

ETIQUETAS_TIPO = {
    "articulos": "Articulos del inventario",
    "entrada_inventario": "Entrada de inventario (alimento, insumos, vacunas)",
    "proveedores": "Proveedores",
    "sanidad": "Vacunas y tratamientos aplicados",
    "produccion": "Produccion de huevos",
}


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalizar(texto: str) -> str:
    """Quita tildes, espacios de mas y mayusculas para poder comparar."""
    if texto is None:
        return ""
    limpio = unicodedata.normalize("NFKD", str(texto))
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    limpio = limpio.lower().strip()
    limpio = " ".join(limpio.replace("_", " ").replace(".", " ").split())
    return limpio


# --------------------------- Lectura del archivo ---------------------------
def _valor_plano(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    if valor is None:
        return None
    if isinstance(valor, str):
        return valor.strip()
    return valor


def leer_archivo(contenido: bytes, nombre: str) -> tuple[str | None, list[str], list[dict]]:
    """Devuelve (hoja, columnas, filas). Acepta .xlsx y .csv."""
    minusculas = nombre.lower()

    if minusculas.endswith((".csv", ".txt")):
        texto = contenido.decode("utf-8-sig", errors="replace")
        muestra = texto[:4000]
        try:
            dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t|")
        except csv.Error:
            dialecto = csv.excel
            dialecto.delimiter = ";" if muestra.count(";") > muestra.count(",") else ","

        lector = csv.reader(io.StringIO(texto), dialecto)
        filas_brutas = [fila for fila in lector if any(str(c).strip() for c in fila)]
        if not filas_brutas:
            raise ValueError("El archivo esta vacio")
        encabezados = [str(c).strip() for c in filas_brutas[0]]
        datos = [
            {encabezados[i]: _valor_plano(fila[i]) if i < len(fila) else None for i in range(len(encabezados))}
            for fila in filas_brutas[1:]
        ]
        return None, encabezados, datos[:MAX_FILAS]

    if not minusculas.endswith((".xlsx", ".xlsm")):
        raise ValueError("Solo se pueden leer archivos .xlsx o .csv. Si tienes un .xls antiguo, guardalo como .xlsx")

    libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    hoja = libro.worksheets[0]

    filas_brutas = []
    for fila in hoja.iter_rows(values_only=True):
        if fila is None:
            continue
        if any(celda is not None and str(celda).strip() != "" for celda in fila):
            filas_brutas.append(list(fila))
        if len(filas_brutas) > MAX_FILAS + 20:
            break

    if not filas_brutas:
        raise ValueError("La hoja esta vacia")

    # El encabezado es la primera fila con al menos dos textos
    indice_encabezado = 0
    for indice, fila in enumerate(filas_brutas[:15]):
        textos = [c for c in fila if isinstance(c, str) and c.strip()]
        if len(textos) >= 2:
            indice_encabezado = indice
            break

    encabezados = []
    for posicion, celda in enumerate(filas_brutas[indice_encabezado], start=1):
        nombre_columna = str(celda).strip() if celda is not None and str(celda).strip() else f"Columna {posicion}"
        while nombre_columna in encabezados:
            nombre_columna = f"{nombre_columna} ({posicion})"
        encabezados.append(nombre_columna)

    datos = []
    for fila in filas_brutas[indice_encabezado + 1 :]:
        registro = {
            encabezados[i]: _valor_plano(fila[i]) if i < len(fila) else None for i in range(len(encabezados))
        }
        if any(valor not in (None, "") for valor in registro.values()):
            datos.append(registro)

    return hoja.title, encabezados, datos[:MAX_FILAS]


def sugerir_mapeo(tipo: str, columnas: list[str]) -> dict[str, str]:
    """Empareja automaticamente las columnas del archivo con los campos del sistema."""
    sugerido: dict[str, str] = {}
    usadas: set[str] = set()
    normalizadas = {columna: normalizar(columna) for columna in columnas}

    for clave, _etiqueta, _obligatorio, sinonimos in CAMPOS.get(tipo, []):
        objetivos = [normalizar(s) for s in [clave, *sinonimos]]

        for columna, plano in normalizadas.items():
            if columna in usadas:
                continue
            if plano in objetivos:
                sugerido[clave] = columna
                usadas.add(columna)
                break

        if clave not in sugerido:
            for columna, plano in normalizadas.items():
                if columna in usadas or not plano:
                    continue
                if any(objetivo and (objetivo in plano or plano in objetivo) for objetivo in objetivos):
                    sugerido[clave] = columna
                    usadas.add(columna)
                    break

    return sugerido


# --------------------------- Conversion de valores ---------------------------
def texto(valor) -> str | None:
    if valor is None:
        return None
    limpio = str(valor).strip()
    return limpio or None


def numero(valor, campo: str) -> Decimal | None:
    if valor is None or str(valor).strip() == "":
        return None
    crudo = str(valor).strip().replace("$", "").replace(" ", "")
    # 1.234,56 (formato de Colombia) o 1234.56
    if "," in crudo and "." in crudo:
        crudo = crudo.replace(".", "").replace(",", ".")
    elif "," in crudo:
        crudo = crudo.replace(",", ".")
    try:
        return Decimal(crudo)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{campo}: '{valor}' no es un numero") from exc


def fecha(valor, campo: str) -> date | None:
    if valor is None or str(valor).strip() == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor

    crudo = str(valor).strip()
    for formato in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(crudo, formato).date()
        except ValueError:
            continue
    raise ValueError(f"{campo}: '{valor}' no es una fecha")


def aplicar_mapeo(tipo: str, mapeo: dict[str, str], datos: dict) -> dict:
    """Pasa de {columna del archivo: valor} a {campo del sistema: valor}."""
    return {clave: datos.get(columna) for clave, columna in mapeo.items() if columna}


def validar_fila(tipo: str, valores: dict) -> dict:
    """Convierte y revisa una fila. Lanza ValueError con el problema encontrado."""
    limpio: dict = {}

    for clave, etiqueta, obligatorio, _sinonimos in CAMPOS[tipo]:
        valor = valores.get(clave)

        if clave in ("cantidad", "costo_unitario", "kg_por_bulto", "stock_minimo", "aves_tratadas"):
            convertido = numero(valor, etiqueta)
        elif clave in ("fecha", "vencimiento", "proximo_refuerzo"):
            convertido = fecha(valor, etiqueta)
        else:
            convertido = texto(valor)

        if obligatorio and convertido in (None, ""):
            raise ValueError(f"Falta {etiqueta}")
        limpio[clave] = convertido

    if tipo in ("entrada_inventario", "produccion"):
        if limpio.get("cantidad") is None or limpio["cantidad"] <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")

    return limpio
