# Revisión de AVISENA — errores y fallos encontrados

Fecha: 15/09/2026 · Alcance: `BACKEND/` (FastAPI + MySQL) y `FRONTEND/` (HTML + JS vanilla).
Método: lectura del código, análisis estático (pyflakes, `node --check`), carga real de la app FastAPI (172 rutas) y cruce automático de cada llamada del frontend contra las rutas del backend.
No se pudo probar contra la base de datos porque `db.sql` no está en el repositorio.

Severidad: 🔴 Crítico · 🟠 Alto · 🟡 Medio · ⚪ Bajo

## ✅ Estado de las correcciones (15/09/2026)

| Punto | Estado | Qué se hizo |
|---|---|---|
| C1 | ⚠️ **Pendiente (manual)** | No se puede hacer desde el código: **cambia la clave de MySQL, la contraseña de aplicación de Gmail y el `JWT_SECRET`**, saca `BACKEND/.env` del repositorio (`git rm --cached BACKEND/.env`) y limpia el historial. |
| C2 | ✅ | `config.py` ya no trae secreto por defecto: si falta `JWT_SECRET` (o tiene menos de 32 caracteres) la app no arranca. |
| C3, C4 | ✅ | Errores de sintaxis corregidos en `chickens.js` e `incident_chicken.js`. |
| C5 | ✅ | Código con `secrets`, ligado al email (`/reset-password` ahora pide `email`), límite de intentos (5 fallos invalidan el código) y límite de solicitudes (`core/rate_limit.py`). Login con límite de intentos fallidos. Contraseña mínima unificada en 8. |
| C6 | ✅ | `users.py`: solo un superadmin gestiona superadmins; los admins requieren módulo 10; nadie puede desactivarse a sí mismo; cada usuario puede editar su propio perfil. |
| C7 | ✅ | `/rescue/all-pag`, `/rescue/all-pag-by-date` exigen login y permisos; el PUT verifica permisos. |
| A1 | ✅ | Middleware global en `main.py`: todo error no controlado sale como JSON 500 **con cabeceras CORS**. Los 500 ya no exponen el SQL (`detail=str(e)` reemplazado). |
| A2 | ✅ | `apiClient.js` distingue sesión inválida (cierra sesión) de falta de permisos, y siempre lanza un error (no devuelve `undefined`). Errores 422 legibles y error de red claro. |
| A3 | ✅ | CORS limitado a `CORS_ORIGINS` (nueva variable en `.env.example`). |
| A4, A6 | ✅ | Descuento de stock/salvamento atómico (`UPDATE ... WHERE cantidad >= :cantidad`), filas bloqueadas con `FOR UPDATE`, 404 si el detalle no existe. |
| A5 | ✅ | Validaciones `Field` en gallinas, salvamento, consumo, detalles de venta, ventas y tareas. |
| A7 | ✅ | La venta toma `id_usuario` del token. |
| A8 | ✅ | El stock queda de solo lectura en el frontend (los modales/llamadas que no existían se quitaron); `/stock/stock/all` devuelve `id_producto`, ordena y pagina. |
| A9, A10 | ✅ | `main.js` carga cada módulo con un mapa único, guarda `window.currentPage` y descarta cargas obsoletas; los módulos ya no se auto-inicializan; las exportaciones solo responden en su página; la navegación entre alimentos/consumo e incidentes/aislamientos usa `loadContent`. |
| A11, A12 | ✅ | `index.html` sin `main.js`, login con Enter y spinner; `dashboard.html` con guardia de sesión; "Cerrar sesión" ahora sí borra el token. |
| M1 | ✅ (2ª ronda) | `tipo_huevos` usa ahora el módulo 25, definido en `database/02_seed.sql`. |
| M2 | ✅ | Se quitó el mapa de permisos duplicado de `dashboard.html`; `permisos.js` tiene alias para `categorias_inventario`, `metodos_pago`, etc. |
| M3, M4, M5 | ✅ | URLs corregidas; ruta `/incident/cambiar-estado/{chiken_id}`; servicio duplicado eliminado. |
| M6 | ✅ | Eliminado `PUT /tareas/usuario/{id}` (modificaba todas las tareas); un operario solo cambia estado/fecha fin de sus tareas; `get_tarea_by_id` corregido (consultaba por el campo equivocado); `TareaUpdate` acepta `id_usuario`. |
| M7 | ✅ | Los listados devuelven `[]` en vez de 404. |
| M8 | ✅ | Todas las respuestas pasan por `sanitizeData` (escapa `< > " '`) antes de llegar a `innerHTML`. |
| M9, M10, M12 | ✅ | Sin `console.log` del token; mensajes con `textContent`; exportación de alimentos con todos los registros. |
| M11 | ✅ (2ª ronda) | Esquema y datos iniciales en `BACKEND/database/`. |
| Bajos | ✅ | Eliminados: `sheds copy.py` (x2), `check_tables.py`, `check_columns.py`, `test_produccion.py`, `Ignore`, `js/user.service.js`, `js/sensors.js`, `js/sensor_types.js`, `js/api/dashboard.service.js`, `js/index-charts.js`. URL de la API centralizada en `assets/js/config.js`. `orm_mode` migrado. Dependencias sin uso quitadas de `requirements.txt`. Funciones duplicadas renombradas. |

**Verificación realizada:** pyflakes sin errores, la app FastAPI carga (171 rutas), `node --check` sin errores en todos los JS, las 173 llamadas del frontend coinciden con rutas del backend, y pruebas con TestClient/mocks de CORS, permisos de usuarios, tareas, ventas, reset de contraseña y descuento de stock. No se pudo probar contra la base de datos real (no es accesible desde aquí).

**Notas de despliegue:**
- Agrega `CORS_ORIGINS` al `.env` del servidor si el frontend usa otro dominio.
- Si la API está detrás de nginx, arranca gunicorn/uvicorn con `--forwarded-allow-ips` para que el límite de intentos use la IP real.
- Por el escape anti-XSS, un texto con comillas o `<` guardado en la BD se mostrará escapado dentro de los campos de edición.

---

## 🔴 Críticos

| # | Dónde | Problema | Cómo arreglarlo |
|---|---|---|---|
| C1 | `BACKEND/.env` | El `.env` **con credenciales reales** (IP pública de MySQL, usuario/clave de BD, `JWT_SECRET`, contraseña de aplicación de Gmail) está dentro del proyecto descargado de GitHub. El `.gitignore` lo lista, pero el archivo ya se había subido. | **Rotar ya** la clave de MySQL, la contraseña de aplicación de Gmail y el `JWT_SECRET`. Borrarlo del repo (`git rm --cached BACKEND/.env`) y limpiar el historial (git filter-repo / BFG). Restringir el puerto 3306 por firewall. |
| C2 | `core/config.py` | `JWT_SECRET` tiene un valor por defecto escrito en el código. Si falta la variable, cualquiera que lea el repo puede firmar tokens válidos. | Quitar el valor por defecto y hacer que la app falle al arrancar si no existe. |
| C3 | `pages/chickens.js:174` | **Error de sintaxis** (`console.error("...",` sin cerrar). El módulo no carga: la página **Gallinas** no funciona. | Cerrar el paréntesis: `console.error("Error cargando los tipos de gallinas:", error);` |
| C4 | `pages/incident_chicken.js:619` | **Error de sintaxis** (una `}` de más dentro del `setTimeout`). La página **Incidentes de gallina** no carga. | Eliminar la llave sobrante de la línea 619 (verificado: sin ella el archivo compila). |
| C5 | `router/auth.py` + `crud/users.py` | Recuperación de contraseña débil: código de 6 dígitos con `random` (no criptográfico), **sin límite de intentos** y **no ligado al email** (`/reset-password` solo recibe el código). Con fuerza bruta (1.000.000 combinaciones) se puede cambiar la clave de cualquier usuario con un código pendiente. | Usar `secrets`, pedir email + código, limitar intentos (p. ej. slowapi), guardar el código hasheado e invalidarlo tras N fallos. |
| C6 | `router/users.py` | Escalada de privilegios: quien tenga permiso de "actualizar" en usuarios (módulo 4) puede editar el **email de un superadmin** (`PUT /users/by-id/{id}`) o desactivarlo (`/cambiar-estado`), y luego pedir recuperación de contraseña para ese correo. Solo `crear` distingue roles 1/2. | Validar el rol del usuario destino igual que en `crear` (módulo 10 para admins) y no permitir modificar cuentas de rango superior. |
| C7 | `router/rescue.py` | `GET /rescue/all-pag` y `/rescue/all-pag-by-date` **no requieren login** (la dependencia está comentada). `PUT /rescue/by-id/{id}` exige token pero **no verifica permisos**. | Descomentar `get_current_user` + `verify_permissions`; añadir `verify_permissions(..., 'actualizar')` al PUT. |

## 🟠 Altos

| # | Dónde | Problema | Cómo arreglarlo |
|---|---|---|---|
| A1 | Todos los `crud/*.py` y `router/*.py` | Los CRUD convierten `SQLAlchemyError` en `Exception` genérica, pero los routers solo capturan `SQLAlchemyError`. Resultado: cualquier fallo de BD sale como 500 **sin cabeceras CORS** (comprobado con TestClient), y el navegador muestra "Failed to fetch"/error CORS en vez del mensaje real. | Relanzar `SQLAlchemyError` (o una excepción propia) desde el CRUD y registrar un `@app.exception_handler` global que devuelva JSON. |
| A2 | `assets/js/api/apiClient.js` | Todo 401 se trata como "no tiene permisos", pero el backend devuelve 401 también para **token inválido/expirado** ("Token Invalido", "Not authenticated"). La sesión vencida **nunca cierra sesión**, el usuario solo ve "Acceso denegado". Además en 403 la función devuelve `undefined` y las páginas fallan después con `Cannot read properties of undefined`. | Diferenciar por `detail` (o usar 403 para permisos en el backend) y lanzar un error en vez de `return;`. |
| A3 | `main.py` | CORS con `allow_origins=["*"]` + `allow_credentials=True`: Starlette **refleja cualquier origen** (probado con `https://evil.com`). | Poner la lista real: `["https://avisena.store"]`. |
| A4 | `crud/detalle_huevos.py`, `detalle_salvamento.py` | Condición de carrera en ventas: se consulta el stock y luego se descuenta sin bloqueo → dos ventas simultáneas pueden dejar stock negativo. | `SELECT ... FOR UPDATE` o `UPDATE stock SET ... WHERE id_producto=:id AND cantidad_disponible >= :cantidad` y comprobar `rowcount`. |
| A5 | `schemas/detalle_huevos.py` (`DetalleHuevosUpdate`), `chickens.py`, `rescue.py`, `consumo_gallinas.py`, `ventas.py` | Sin validaciones (`Field`). Ej.: editar un detalle con `cantidad` negativa **aumenta el stock**; en el alta se permite `cantidad = 0`. | Añadir `Field(gt=0)` en cantidades e ids, `ge=0` en precios. |
| A6 | `crud/detalle_huevos.py` update/delete | Si el `id_detalle` no existe, `datos_anteriores` / `data` es `None` → `TypeError` → 500. | Comprobar `None` y devolver 404. |
| A7 | `schemas/ventas.py` | `id_usuario` de la venta lo envía el cliente (sale de `localStorage`). Se puede registrar una venta a nombre de otro usuario. | Tomar `id_usuario` de `user_token` en el router. |
| A8 | Frontend `stock.service.js` | `CreateStock` → `POST /stock/crear` **no existe**; `UpdateStock` → `PUT /stock/by-id/{id}` está **comentado** en el backend. Crear/editar stock siempre falla (404/405). | Exponer esos endpoints (el CRUD `create_or_increment_stock` ya existe) o quitar los botones. |
| A9 | Módulos de `assets/pages/*.js` | 10 módulos registran un listener global `document.addEventListener("click", …".export-format")`. Tras visitar varias páginas, **un clic en "Exportar" dispara la exportación de todos** los módulos visitados (descarga datos de otras páginas). | Registrar el listener sobre el contenedor de la página (que se reemplaza) o comprobar un `data-module`. |
| A10 | `alimentos.js`, `isolations.js`, `chickens.js`, `consumo_alimento.js` | `init()` se ejecuta al importar el módulo **y** otra vez desde `main.js` → peticiones duplicadas y listeners duplicados. `roles.js` añade `document.addEventListener("change", …)` en cada `init()` → cambiar estado de un rol hace N peticiones. | Quitar las llamadas a `init()` de nivel superior; usar listeners sobre elementos de la vista o una bandera "ya registrado". |
| A11 | `index.html` | Carga `assets/js/main.js`, que hace `navLinks.addEventListener` con `navLinks = null` → `TypeError` en la pantalla de login y un `fetch` inútil a `pages/panel.html`. | No incluir `main.js` en `index.html`. |
| A12 | `dashboard.html` | No hay **guardia de sesión**: se puede abrir sin token (solo fallan las peticiones). | Al inicio: si no hay `access_token`, redirigir a `index.html`. |

## 🟡 Medios

| # | Dónde | Problema |
|---|---|---|
| M1 | `router/tipo_huevos.py` | Usa `modulo = 6`, el mismo ID que **tareas** → los permisos de un módulo afectan al otro. |
| M2 | Permisos del frontend | Hay **3 mapas de permisos distintos** (en `main.js`, en el `<script>` de `dashboard.html` y en `permisos.js`) y no coinciden con la tabla `permisos` de la BD. Ej.: `lands` y `categorias_inventario` no están en la lista de `dashboard.html` → quedan **ocultos para todos los roles**, incluido superadmin. Lo ideal es un endpoint que devuelva los permisos del rol. |
| M3 | Frontend `incident_chicken.service.js:91` | Llama a `/incident/chicken_incidents_pag` (no existe; la real es `/incident/all_incidentes-gallinas-pag`). |
| M4 | Frontend `assets/js/user.service.js:41` | Llama a `/users/by_id/…` (la real es `/users/by-id/…`). Es un archivo duplicado de `js/api/user.service.js`; conviene borrarlo. |
| M5 | `router/chicken_incident.py:236` | Ruta `/cambiar-estado/{user_id}` pero la función recibe `chiken_id` → FastAPI lo trata como query obligatorio (el frontend lo "parchea" enviando `?chiken_id=`). Renombrar a `{chiken_id}`. |
| M6 | `router/tareas.py` | `PUT /tareas/usuario/{id}` actualiza **todas** las tareas de un usuario con los mismos datos; y cualquier rol con "actualizar" edita tareas ajenas (no se valida propietario). |
| M7 | Varios routers (`ventas/all-ventas`, `tareas/usuario`, incidentes…) | Devuelven **404 cuando la lista está vacía**; el frontend lo muestra como error. Para listas, devolver `[]` con 200. |
| M8 | ~270 usos de `innerHTML` con datos del backend sin escapar (`nombre`, `descripcion`, …) | **XSS almacenado**: un nombre con `<img onerror=…>` se ejecuta al listar y puede robar el token de `localStorage`. Usar `textContent` o una función `escapeHtml`. |
| M9 | `index.html` | `console.log("Login exitoso:", data)` imprime el token; si falla la red, se muestra `undefined` (`error.detail`). |
| M10 | Contraseñas | Mínimo 8 caracteres al crear usuario, 9 al restablecer. Unificar. |
| M11 | Repositorio | Falta `db.sql` (está en `.gitignore`) → nadie puede levantar el proyecto; y la lógica de `cant_actual` de galpones parece depender de triggers que no están versionados. |
| M12 | `crud/alimento.py` export (`alimentos.js`) | Sin rango de fechas, la exportación solo trae la **página 1 (10 registros)**. |

## ⚪ Bajos / limpieza

- `dependencies.py`: `print(user)` en cada petición autenticada.
- `crud/users.py → update_user()` apunta a la tabla `usuario` (no existe); es código muerto.
- `crud/lands.py`: `get_land_by_id` definida dos veces; `router/users.py`, `detalle_huevos.py`, `detalle_salvamento.py`: funciones con el mismo nombre (ids de OpenAPI duplicados).
- Archivos basura: `router/sheds copy.py`, `schemas/sheds copy.py`, `check_tables.py`, `check_columns.py`, `test_produccion.py`, `Ignore`, `assets/js/sensors.js` y `sensor_types.js` (importan rutas inexistentes `../api/...` y no se usan), `charts-demo.js`, `index-charts.js` (datos aleatorios de la plantilla, cargado en el dashboard).
- `schemas/produccion_huevos.py`: `orm_mode` (Pydantic v1) → usar `model_config = ConfigDict(from_attributes=True)`.
- `datetime.now()` sin zona horaria en tokens de recuperación (depende de la TZ del servidor).
- SweetAlert2 se carga dos veces en `dashboard.html`; `xlsx-latest` de cdn.sheetjs sin versión fija; dos versiones distintas de ApexCharts.
- URL de la API (`https://api.avisena.store`) repetida en 6 archivos: centralizar en un `config.js`.
- Enlaces rotos de la plantilla: `settings.html`, `docs.html`, `favicon.ico`, `charts-custom.js`; `pages/perfil.html` referencia scripts con ruta incorrecta.
- `requirements.txt` incluye paquetes que no se usan (`sendgrid`, `sentry-sdk`, `Werkzeug`, `fastapi-cloud-cli`…).
- Los permisos denegados responden 401; lo correcto es 403 (y facilita arreglar A2).
- Los f-strings en SQL (`UPDATE ... SET {campos}`) son seguros aquí porque las claves vienen del esquema Pydantic, no del usuario — no es un problema, solo mantenerlo así.

---

## Orden sugerido

1. C1 y C2 (rotar credenciales) — hoy.
2. C3, C4 (dos arreglos de una línea que devuelven dos páginas completas).
3. C5–C7, A2, A3.
4. A1 (manejador global de errores) — elimina la mayoría de "errores CORS" misteriosos.
5. Resto de Altos y Medios.


---

## 🔁 Segunda ronda: base de datos, reorganización y despliegue local (15/09/2026)

### Base de datos (`avisena.sql` → `BACKEND/database/`)
El `avisena.sql` que apareció era una versión **antigua e incompleta**: al compararlo con las 239 consultas del backend le faltaban 2 tablas (`alimento`, `consumo_gallinas`) y 10 columnas (`roles.estado`, `modulos.estado`, `galpones.estado`, `sensores.estado`, `tipo_sensores.estado`, `ventas.estado`, `stock.nombre_producto`, `stock.tipo`, `usuarios.reset_token`, `usuarios.reset_token_expiry`), no tenía llave foránea de `detalle_salvamento` → `salvamento`, guardaba dinero como `DECIMAL` sin decimales y usaba `TINYINT` (máx. 255) para galpones y sensores.

Se reemplazó por `01_schema.sql` + `02_seed.sql`:
- Tipos corregidos, `utf8mb4`, llaves foráneas completas, índices por fecha/galpón/estado y `CHECK` contra cantidades negativas.
- Triggers para ocupación de galpones, stock de huevos y existencias de alimento.
- Datos iniciales: roles, 28 módulos (con los IDs que usa el código), matriz de permisos, métodos de pago, tipos de huevo, etc.
- **Verificado:** las 239 sentencias SQL del backend se ejecutan con `EXPLAIN` sobre MySQL 8 sin errores.

### Errores nuevos encontrados y corregidos
| Dónde | Problema |
|---|---|
| `crud/ventas.py` | `/ventas/by-id-usuario-pag` fallaba siempre (columna `id_usuario` ambigua). |
| `crud/dashboard.py` | "Actividad reciente" usaba `stock.id_produccion` (no existe); el total de ventas aplicaba el descuento distinto al resto del sistema. |
| `router/alimento.py` | `/alimento/all-alimentos` llamaba a una función inexistente (error 500). |
| `crud/consumo_gallinas.py` | "Consumos por galpón" no filtraba por galpón. |
| `router/consumo_gallinas.py` | Se podía consumir más alimento del disponible. |
| `router/chickens.py` | Al editar un ingreso, la capacidad del galpón se calculaba mal (sumaba dos veces). |
| Varios routers | Listados por fecha devolvían 404 cuando no había datos; `page_size` máximo de 100 hacía fallar las exportaciones (subido a 1000). |
| `pages/panel.js` | Recursión infinita en las peticiones del panel y temporizadores que seguían corriendo en otras páginas. |
| `pages/ventas.js` | Exportar sin filtros lanzaba `ReferenceError`. |
| `api/tipoHuevo.service.js` | Editar un tipo de huevo lanzaba `ReferenceError`. |
| `pages/lands.js` | El botón Exportar de fincas nunca funcionó. |
| `api/incidente-gallina.service.js`, `api/roles.service.js` | Parámetros de consulta incorrectos. |

### Reorganización
- **Backend:** `main.py` con routers agrupados, `core/config.py` y `core/database.py` reescritos (contraseñas con caracteres especiales, `/health`), `scripts/crear_superadmin.py`, pruebas en `tests/`, dependencias mínimas, imports sin uso eliminados.
- **Frontend:** todos los servicios en `assets/js/api/`, todas las vistas en `assets/js/pages/`, utilidades en `assets/js/utils/`. La exportación CSV/Excel/PDF que estaba copiada en 12 archivos quedó en `utils/exportar.js`. Librerías de CDN (SweetAlert2, ApexCharts, jsPDF, SheetJS) incluidas en `assets/plugins/`. Se eliminaron las páginas de la plantilla (account, charts, help, notifications, orders, signup), el SCSS de Bootstrap, 23 imágenes y ~34 MB de plugins sin uso, y scripts de jQuery/Select2 que nunca se ejecutaban.
- **Despliegue local:** `docker-compose.yml` (MySQL 8.4 + API + nginx). El frontend llama a `/api` y nginx lo reenvía al backend.

### Verificación de esta ronda
- 71 pruebas de API contra MySQL real (`BACKEND/tests/test_api.py`): todas pasan.
- Prueba en navegador (Chromium) a través de nginx: login, las 24 vistas, exportaciones CSV/Excel/PDF, alta de una finca, protección XSS, redirección sin sesión y cierre de sesión.
- No se pudo ejecutar `docker compose up` aquí (Docker Hub bloqueado en este entorno); se validó la sintaxis del compose y se probó la misma configuración (gunicorn + nginx + scripts SQL) fuera de Docker.

### Sigue pendiente
- **Cambiar las credenciales filtradas** (MySQL, Gmail, JWT) y sacar `BACKEND/.env` del historial de git.
- ~~Al anular una venta se borraban sus detalles~~ → resuelto en la tercera ronda.


---

## 🔁 Tercera ronda: ventas anuladas y ocupación de galpones (16/09/2026)

- **Anular una venta** ahora devuelve el stock de huevos y las gallinas de salvamento **sin borrar los detalles**, así queda el historial (con su total). Una venta anulada no admite nuevos detalles, ni edición, ni borrado de detalles, ni cambio de método de pago, y no se puede reactivar. Al eliminarla ya no se vuelve a sumar el stock (antes se habría sumado dos veces).
- **Salvamento** e **incidentes de tipo Muerte o Fuga** descuentan gallinas de `galpones.cant_actual`, con validación de que el galpón tenga suficientes. Editar o eliminar esos registros corrige la ocupación. Un salvamento con ventas ya no se puede eliminar.
- Errores corregidos de paso: `GET /rescue/by-id` y `POST /detalle_salvamento/crear` convertían los errores 404/400 en 500.
- Pruebas: 72 pasan (se agregaron casos de anulación y de ocupación).
- No requiere cambios en la base de datos: basta con `docker compose up -d --build api`.
