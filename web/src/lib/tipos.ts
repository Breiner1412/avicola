export type Acciones = { ver: boolean; crear: boolean; editar: boolean; borrar: boolean };
export type Permisos = Record<string, Acciones>;

export type Finca = {
  id: number;
  codigo: string;
  nombre: string;
  municipio: string | null;
  solo_lectura: boolean;
};

export type FincaCompleta = Finca & {
  cuenta_id: number;
  departamento: string | null;
  direccion: string | null;
  telefono: string | null;
  activo: boolean;
};

export type UsuarioSesion = {
  id: number;
  nombres: string;
  apellidos: string;
  email: string;
  rol: string;
  rol_nombre: string;
  cuenta_id: number | null;
  cuenta_nombre: string | null;
  debe_cambiar_clave: boolean;
};

export type Sesion = {
  token: string;
  expira_en_minutos: number;
  usuario: UsuarioSesion;
  finca_activa: Finca | null;
  fincas: Finca[];
  permisos: Permisos;
};

export type Galpon = {
  id: number;
  finca_id: number;
  codigo: string;
  nombre: string;
  tipo: "postura" | "levante" | "engorde" | "cria";
  capacidad: number;
  aves_actuales: number;
  observaciones: string | null;
  activo: boolean;
};

export type FincaAsignada = { finca_id: number; solo_lectura: boolean };

export type Usuario = {
  id: number;
  cuenta_id: number | null;
  nombres: string;
  apellidos: string;
  email: string;
  documento: string | null;
  telefono: string | null;
  rol: string;
  rol_nombre: string;
  activo: boolean;
  debe_cambiar_clave: boolean;
  ultimo_ingreso: string | null;
  fincas: FincaAsignada[];
};

export type Rol = {
  id: number;
  clave: string;
  nombre: string;
  descripcion: string | null;
  nivel: number;
  de_plataforma: boolean;
};

export type Cuenta = {
  id: number;
  tipo: "empresa" | "persona";
  nombre: string;
  documento: string | null;
  email_contacto: string | null;
  telefono: string | null;
  activo: boolean;
};

export type LineaAuditoria = {
  id: number;
  cuenta_id: number | null;
  finca_id: number | null;
  usuario_id: number | null;
  usuario_nombre: string | null;
  accion: string;
  entidad: string;
  entidad_id: number | null;
  descripcion: string | null;
  datos: Record<string, unknown> | null;
  ip: string | null;
  creado_en: string;
};

export type Pagina<T> = { total: number; pagina: number; tamano: number; datos: T[] };

export type Resumen = {
  finca_activa: { id: number; nombre: string } | null;
  fincas_visibles: number;
  usuarios_activos: number;
  galpones_activos: number;
  aves_en_finca: number;
  capacidad_finca: number;
  ocupacion: number;
  solo_lectura: boolean;
};

// --- Inventario ---
export type Bodega = {
  id: number;
  cuenta_id: number;
  finca_id: number | null;
  codigo: string;
  nombre: string;
  ubicacion: string | null;
  activo: boolean;
  es_central: boolean;
};

export type CategoriaArticulo = {
  id: number;
  cuenta_id: number | null;
  nombre: string;
  clase: string;
};

export type Articulo = {
  id: number;
  cuenta_id: number;
  categoria_id: number;
  categoria_nombre: string;
  clase: string;
  codigo: string;
  nombre: string;
  unidad: string;
  kg_por_bulto: number | null;
  stock_minimo: number;
  observaciones: string | null;
  activo: boolean;
  existencia_total: number;
  bajo_minimo: boolean;
};

export type Proveedor = {
  id: number;
  cuenta_id: number;
  nombre: string;
  documento: string | null;
  telefono: string | null;
  email: string | null;
  direccion: string | null;
  activo: boolean;
};

export type Existencia = {
  bodega_id: number;
  bodega_nombre: string;
  articulo_id: number;
  articulo_codigo: string;
  articulo_nombre: string;
  unidad: string;
  cantidad: number;
  costo_promedio: number;
  stock_minimo: number;
  bajo_minimo: boolean;
};

export type TipoMovimiento = "entrada" | "salida" | "traslado" | "ajuste";

export type ItemMovimiento = {
  id: number;
  articulo_id: number;
  articulo_codigo: string;
  articulo_nombre: string;
  unidad: string;
  cantidad: number;
  cantidad_aplicada: number;
  costo_unitario: number;
  lote: string | null;
  vencimiento: string | null;
};

export type Movimiento = {
  id: number;
  tipo: TipoMovimiento;
  fecha: string;
  bodega_id: number;
  bodega_nombre: string;
  bodega_destino_id: number | null;
  bodega_destino_nombre: string | null;
  proveedor_id: number | null;
  proveedor_nombre: string | null;
  motivo: string | null;
  documento: string | null;
  observaciones: string | null;
  total: number;
  usuario_nombre: string | null;
  anulado: boolean;
  anulado_en: string | null;
  anulado_por: string | null;
  motivo_anulacion: string | null;
  creado_en: string;
  items: ItemMovimiento[];
};

// --- Aves ---
export type Raza = { id: number; cuenta_id: number | null; nombre: string; proposito: string };

export type Lote = {
  id: number;
  cuenta_id: number;
  finca_id: number;
  galpon_id: number;
  galpon_nombre: string;
  raza_id: number | null;
  raza_nombre: string | null;
  codigo: string;
  proposito: "postura" | "engorde" | "levante";
  fecha_ingreso: string;
  edad_dias: number;
  edad_semanas: number;
  aves_iniciales: number;
  aves_actuales: number;
  aves_descarte: number;
  mortalidad: number;
  mortalidad_porcentaje: number;
  costo_ave: number;
  estado: "activo" | "cerrado";
  fecha_cierre: string | null;
  observaciones: string | null;
};

export type MovimientoAves = {
  id: number;
  lote_id: number;
  lote_codigo: string;
  fecha: string;
  tipo: string;
  cantidad: number;
  galpon_destino_id: number | null;
  peso_kg: number | null;
  motivo: string | null;
  observaciones: string | null;
  usuario_nombre: string | null;
  anulado: boolean;
  anulado_por: string | null;
  motivo_anulacion: string | null;
  creado_en: string;
};

export type TipoHuevo = { id: number; cuenta_id: number | null; nombre: string; orden: number; comercial: boolean };

export type ProduccionDia = {
  fecha: string;
  lote_id: number;
  lote_codigo: string;
  aves: number;
  total: number;
  comercial: number;
  porcentaje_postura: number;
  detalles: Record<string, number>;
};

export type StockHuevos = {
  tipo_huevo_id: number;
  tipo: string;
  comercial: boolean;
  cantidad: number;
  panales: number;
};

export type Pesaje = {
  id: number;
  lote_id: number;
  fecha: string;
  aves_muestra: number;
  peso_total_kg: number;
  peso_promedio_kg: number;
  edad_dias: number | null;
  observaciones: string | null;
  usuario_nombre: string | null;
};

export type ConsumoAlimento = {
  id: number;
  lote_id: number;
  fecha: string;
  articulo_id: number;
  articulo_nombre: string;
  unidad: string;
  bodega_id: number;
  cantidad: number;
  costo: number;
  observaciones: string | null;
  usuario_nombre: string | null;
};

export type Sanidad = {
  id: number;
  fecha: string;
  tipo: string;
  producto: string;
  lote_id: number | null;
  lote_codigo: string | null;
  galpon_id: number | null;
  galpon_nombre: string | null;
  articulo_id: number | null;
  cantidad_usada: number | null;
  lote_producto: string | null;
  dosis: string | null;
  via: string;
  aves_tratadas: number | null;
  responsable: string | null;
  proximo_refuerzo: string | null;
  observaciones: string | null;
  usuario_nombre: string | null;
  creado_en: string;
};

export type BalanceLote = {
  lote: Lote;
  dias_en_granja: number;
  alimento_kg: number;
  alimento_costo: number;
  alimento_por_ave_kg: number;
  huevos_total: number;
  huevos_comerciales: number;
  huevos_por_dia: number;
  porcentaje_postura: number;
  peso_promedio_kg: number | null;
  peso_fecha: string | null;
  costo_aves: number;
  costo_sanidad: number;
  costo_total: number;
  costo_por_ave: number;
  conversion_alimenticia: number | null;
};

// --- Ventas ---
export type PuntoVenta = {
  id: number;
  cuenta_id: number;
  finca_id: number | null;
  codigo: string;
  nombre: string;
  direccion: string | null;
  prefijo: string;
  consecutivo: number;
  activo: boolean;
  es_central: boolean;
};

export type ProductoVenta = {
  id: number;
  cuenta_id: number;
  nombre: string;
  clase: "huevo" | "ave_descarte" | "ave_engorde" | "otro";
  tipo_huevo_id: number | null;
  tipo_huevo: string | null;
  presentacion: "unidad" | "docena" | "medio_panal" | "panal" | "kg";
  factor: number;
  cobro_por: "unidad" | "kg";
  orden: number;
  activo: boolean;
  precio: number | null;
  disponible: number | null;
};

export type PrecioHistorial = {
  id: number;
  producto_id: number;
  punto_venta_id: number | null;
  precio: number;
  desde: string;
  hasta: string | null;
  usuario_nombre: string | null;
};

export type MetodoPago = { id: number; nombre: string; es_efectivo: boolean };

export type Turno = {
  id: number;
  punto_venta_id: number;
  punto_venta_nombre: string;
  usuario_id: number;
  usuario_nombre: string | null;
  estado: "abierto" | "cerrado";
  base_inicial: number;
  abierto_en: string;
  cerrado_en: string | null;
  ventas: number;
  total_vendido: number;
  total_efectivo: number;
  esperado_en_caja: number;
  efectivo_contado: number | null;
  diferencia: number | null;
  observaciones: string | null;
};

export type DetalleVenta = {
  id: number;
  producto_id: number;
  descripcion: string;
  clase: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
  unidades: number;
  peso_kg: number | null;
  lote_id: number | null;
};

export type Venta = {
  id: number;
  numero: string;
  punto_venta_id: number;
  punto_venta_nombre: string;
  turno_id: number | null;
  fecha: string;
  subtotal: number;
  descuento: number;
  total: number;
  estado: "activa" | "anulada";
  observaciones: string | null;
  usuario_nombre: string | null;
  anulada_en: string | null;
  anulada_por: string | null;
  motivo_anulacion: string | null;
  creado_en: string;
  detalles: DetalleVenta[];
  pagos: { metodo_pago_id: number; metodo_nombre: string; es_efectivo: boolean; monto: number; referencia: string | null }[];
};

export type ResumenVentas = {
  ventas: number;
  total: number;
  efectivo: number;
  otros_medios: number;
  anuladas: number;
  huevos_vendidos: number;
  aves_vendidas: number;
};
