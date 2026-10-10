"""Datos de ejemplo: una granja que lleva seis meses usando Avícola.

Crea la cuenta "Granja Avicola La Esperanza" con dos fincas, sus usuarios, galpones,
bodegas, articulos, lotes, puntos de venta y sensores, y despues simula dia por dia
el trabajo de los ultimos meses: recoleccion de huevos, alimento, mortalidad, pesajes,
vacunas, compras, traslados, ventas con su caja, descarte, pollo de engorde, tareas,
rutinas, novedades y mediciones de los sensores.

Todo se registra con las mismas reglas del sistema (las funciones de la API), asi que
el inventario, las aves y la caja cuadran como si lo hubiera hecho la gente.

Uso:
    python -m app.demo                 # 180 dias hasta hoy
    python -m app.demo --dias 90       # otro periodo

Con Docker:
    docker compose exec api python -m app.demo

Solo se puede cargar una vez por base de datos. Para empezar de cero hay que borrar la
base (docker compose down -v) y volver a levantar todo.

El paquete se divide por areas: datos (constantes y curvas), base (sesion, reloj y
llamadas), estructura, granja, tienda, trabajo y sensores; simulacion las junta.
"""
