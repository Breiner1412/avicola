# AVISENA

Sistema de gestion para granjas avicolas: varias fincas, varias cuentas (empresas o
personas), aves, inventario, sanidad y ventas.

- **API:** FastAPI (Python 3.11) + SQLAlchemy + Alembic + MySQL 8.4 + Redis
- **Web:** Next.js 15 + TypeScript + Tailwind CSS
- **Local:** Docker Compose levanta base de datos, cache, API y web

> La version 2 esta en las carpetas `api/` y `web/`.
> Las carpetas `BACKEND/` y `FRONTEND/` son la version 1 y se eliminaran cuando la
> version 2 la reemplace por completo.

---

## Puesta en marcha

```bash
# 1. Variables de entorno (cambia las contrasenas y el JWT_SECRET)
cp .env.example .env

# 2. Levantar todo
docker compose -f docker-compose.v2.yml up -d --build

# 3. Abrir
#    Aplicacion:  http://localhost:3000
#    API y documentacion: http://localhost:8000/docs
```

Entra con el `ADMIN_EMAIL` y `ADMIN_PASSWORD` del `.env`. La primera vez el sistema
crea los modulos, los roles, los permisos, el usuario de plataforma y una cuenta con
una finca de ejemplo para poder empezar.

| Accion | Comando |
|---|---|
| Ver los registros de la API | `docker compose -f docker-compose.v2.yml logs -f api` |
| Detener | `docker compose -f docker-compose.v2.yml down` |
| Empezar de cero | `docker compose -f docker-compose.v2.yml down -v` y volver a levantar |
| Reiniciar la clave del admin | `docker compose -f docker-compose.v2.yml exec api python -m app.semilla --reiniciar-admin` |
| Restaurar los permisos de fabrica | `... exec api python -m app.semilla --forzar-permisos` |

### Sin Docker

```bash
# API
cd api
cp .env.example .env          # ajusta la conexion a tu MySQL
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.semilla
uvicorn app.main:app --reload         # http://localhost:8000

# Web (en otra terminal)
cd web
npm install
npm run dev                            # http://localhost:3000
```

La web llama a la API por `/api` del mismo dominio: Next.js reenvia esas rutas al
backend (`API_INTERNA`), asi las cookies de sesion funcionan sin configurar CORS.

---

## Estructura

```
AVISENA/
├── docker-compose.v2.yml     # base de datos + cache + API + web
├── .env.example              # variables de entorno (copiar a .env)
├── docs/DISENO_V2.md         # diseno completo del sistema
├── api/
│   ├── app/
│   │   ├── main.py           # aplicacion FastAPI
│   │   ├── core/             # configuracion, base de datos, seguridad, permisos, auditoria
│   │   ├── modelos/          # tablas (SQLAlchemy)
│   │   ├── esquemas/         # validacion de datos que entran y salen
│   │   ├── servicios/        # reglas de negocio (sesiones, alcance por finca)
│   │   ├── rutas/            # endpoints por modulo
│   │   └── semilla.py        # datos iniciales
│   ├── migraciones/          # Alembic
│   └── tests/                # pruebas de extremo a extremo
└── web/
    └── src/
        ├── app/              # pantallas (App Router)
        ├── componentes/      # piezas de interfaz reutilizables
        └── lib/              # cliente de la API, sesion, menu, tipos
```

---

## Como funcionan los accesos

- **Cuenta:** una empresa o una persona. Todo lo que se registra pertenece a una cuenta.
- **Finca:** cada cuenta puede tener varias. La informacion se guarda separada por finca.
- **Finca activa:** al entrar, el empleado elige en cual esta trabajando; los
  administradores y supervisores pueden cambiarla desde la barra superior. La web envia
  esa finca en cada peticion y la API valida que el usuario tenga acceso.
- **Supervisor:** trabaja en las fincas a su cargo y puede tener otras marcadas como
  *solo consulta*, para ver lo que necesite de otra finca de la misma cuenta.

| Rol | Que puede hacer |
|---|---|
| plataforma | Administra el sistema y todas las cuentas |
| propietario | Todo dentro de su cuenta |
| administrador | Toda la operacion de las fincas de la cuenta |
| supervisor | Su finca completa; otras fincas de la cuenta solo de consulta |
| operario | Registra el trabajo diario de su finca |
| cajero | Atiende el punto de venta |

Los permisos se guardan en la base de datos (`permisos`) y se cambian desde la pantalla
**Roles y permisos**. El backend los valida en cada peticion; la web solo esconde lo que
el rol no puede usar.

---

## Pruebas

```bash
cd api
pip install -r requirements-dev.txt
python -m pytest -q
```

Las pruebas cubren el inicio de sesion, el cambio de contrasena, los permisos por rol,
la eleccion de finca, los galpones, el registro de cambios y —lo mas importante— que
**una cuenta no pueda ver ni tocar los datos de otra**.

---

## Seguridad

- Token de acceso corto (JWT) y token de refresco en una cookie `HttpOnly`.
- Contrasenas con bcrypt; limite de intentos en el inicio de sesion y en la recuperacion.
- Cada operacion importante queda en el registro de cambios con usuario, finca y fecha.
- Los errores internos salen como un mensaje generico, sin detalles de la base de datos.
- **Nunca subas el archivo `.env` al repositorio.**

---

## Version 1 (carpetas BACKEND/ y FRONTEND/)

La version anterior sigue funcionando con `docker compose up -d --build`; sus variables
estan en `BACKEND/.env.example`. Se mantiene solo como referencia mientras se termina la
version 2.

## Pruebas automaticas en GitHub

El archivo `docs/github-actions-pruebas.yml` trae el flujo de trabajo listo. Para
activarlo, copialo a `.github/workflows/pruebas.yml` en tu computador y sube el cambio.
