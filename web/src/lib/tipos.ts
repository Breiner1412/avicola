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
