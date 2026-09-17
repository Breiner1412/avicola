# API Dashboard AVISENA

## Descripción

API para el panel de control de la plataforma AVISENA. Proporciona métricas en tiempo real, gráficos y datos de monitoreo de la granja avícola.

## Endpoints Disponibles

### 1. Métricas Principales

**GET** `/dashboard/metricas`

Obtiene las métricas principales del dashboard.

**Respuesta:**

```json
{
  "total_gallinas": 12450,
  "produccion_hoy": 3280,
  "galpones_activos": 8,
  "alertas_activas": 3,
  "gallinas_trend": "+2.5%",
  "produccion_trend": "+5.8%"
}
```

---

### 2. Producción Semanal

**GET** `/dashboard/produccion-semanal`

Obtiene datos de producción de los últimos 7 días comparados con la semana anterior.

**Respuesta:**

```json
{
  "labels": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
  "data_actual": [3100, 3250, 3180, 3400, 3280, 2950, 3100],
  "data_anterior": [2900, 3050, 2980, 3200, 3080, 2750, 2900]
}
```

---

### 3. Distribución por Tipos

**GET** `/dashboard/distribucion-tipos`

Obtiene la distribución de gallinas por tipo/raza.

**Respuesta:**

```json
[
  {
    "tipo": "Leghorn",
    "cantidad": 5602,
    "porcentaje": 45.0
  },
  {
    "tipo": "Rhode Island",
    "cantidad": 3735,
    "porcentaje": 30.0
  }
]
```

---

### 4. Ocupación de Galpones

**GET** `/dashboard/ocupacion-galpones`

Obtiene el porcentaje de ocupación de cada galpón.

**Respuesta:**

```json
[
  {
    "nombre": "Galpón A",
    "capacidad": 2000,
    "cantidad_actual": 1700,
    "ocupacion_porcentaje": 85
  }
]
```

---

### 5. Incidentes Recientes

**GET** `/dashboard/incidentes-recientes`

Obtiene los últimos incidentes registrados (máximo 5).

**Respuesta:**

```json
[
  {
    "id": 15,
    "tipo": "Temperatura",
    "severidad": "warning",
    "descripcion": "Alta temperatura en Galpón C",
    "fecha": "2025-11-24",
    "tiempo": "Hace 2h"
  }
]
```

---

### 6. Datos de Sensores

**GET** `/dashboard/sensores`

Obtiene los últimos datos registrados de los sensores ambientales.

**Respuesta:**

```json
{
  "temperatura": 25.3,
  "humedad": 62.0,
  "co2": 450,
  "luminosidad": 750
}
```

---

### 7. Actividad Reciente

**GET** `/dashboard/actividad-reciente`

Obtiene las últimas actividades registradas en el sistema.

**Respuesta:**

```json
[
  {
    "tipo": "produccion",
    "descripcion": "Producción registrada: 1250 huevos",
    "tiempo": "Hace 10 min",
    "color": "success"
  }
]
```

---

### 8. Dashboard Completo

**GET** `/dashboard/completo`

Obtiene todos los datos del dashboard en una sola petición (optimizado para carga inicial).

**Respuesta:**

```json
{
  "metricas": { ... },
  "produccion_semanal": { ... },
  "distribucion_tipos": [ ... ],
  "ocupacion_galpones": [ ... ],
  "incidentes_recientes": [ ... ],
  "sensores": { ... },
  "actividad_reciente": [ ... ]
}
```

---

## Autenticación

Todos los endpoints requieren autenticación mediante Bearer Token:

```
Authorization: Bearer <token>
```

El token se obtiene del endpoint `/access/token` al iniciar sesión.

---

## Códigos de Estado

- `200` - Operación exitosa
- `401` - No autorizado (token inválido o expirado)
- `500` - Error del servidor

---

## Uso en Frontend

La clase `DashboardService` definida en `assets/js/pages/panel.js` proporciona métodos para consumir estos endpoints:

```javascript
const metricas = await dashboardService.getMetricas();
const produccion = await dashboardService.getProduccionSemanal();
const sensores = await dashboardService.getSensores();
```

---

## Notas Técnicas

1. **Performance**: El endpoint `/completo` está optimizado para reducir el número de peticiones HTTP.

2. **Actualización**: Los sensores se actualizan cada 10 segundos automáticamente en el frontend.

3. **Cache**: No se implementa cache para garantizar datos en tiempo real.

4. **Errores**: Todos los errores de base de datos se logean en el servidor y devuelven mensajes genéricos al cliente.

---

## Archivos Creados/Modificados

### Backend:

- `app/schemas/dashboard.py` - Modelos Pydantic para respuestas
- `app/crud/dashboard.py` - Lógica de negocio y consultas SQL
- `app/router/dashboard.py` - Endpoints FastAPI
- `main.py` - Registro del router dashboard

### Frontend:

- `assets/js/pages/panel.js` - Lógica del panel y servicio para consumir la API
- `pages/panel.html` - Panel de control con gráficos integrados

---

## Testing

Para probar los endpoints, puedes usar la documentación interactiva de FastAPI:

```
http://localhost:8000/docs
```

O hacer peticiones directas:

```bash
curl -X GET "http://localhost:8000/dashboard/metricas" \
  -H "Authorization: Bearer <tu-token>"
```

---

## Próximas Mejoras

- [ ] Implementar filtros por fecha en producción
- [ ] Agregar exportación de datos en CSV/Excel
- [ ] Implementar notificaciones push para alertas críticas
- [ ] Agregar más tipos de gráficos (área, radar, etc.)
- [ ] Implementar panel de predicción con ML
