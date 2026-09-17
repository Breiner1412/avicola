-- =====================================================================
--  AVISENA - Datos iniciales (ejecutar después de 01_schema.sql)
--  Los IDs de módulos y roles están fijos porque el backend los usa.
--  El usuario superadmin se crea con: python -m scripts.crear_superadmin
-- =====================================================================
USE avisena;
SET NAMES utf8mb4;

INSERT INTO roles (id_rol, nombre_rol, descripcion, estado) VALUES
  (1, 'superadmin', 'Acceso total al sistema', TRUE),
  (2, 'administrador', 'Gestiona la operación de la granja', TRUE),
  (3, 'supervisor', 'Supervisa producción, sanidad y alimentación', TRUE),
  (4, 'operario', 'Registra las actividades diarias', TRUE);

INSERT INTO modulos (id_modulo, nombre_modulo, estado) VALUES
  (1, 'modulos', TRUE),
  (2, 'permisos', TRUE),
  (3, 'roles', TRUE),
  (4, 'usuarios', TRUE),
  (5, 'ventas', TRUE),
  (6, 'tareas', TRUE),
  (7, 'detalle_huevos', TRUE),
  (8, 'metodo_pago', TRUE),
  (9, 'detalle_salvamento', TRUE),
  (10, 'administradores', TRUE),
  (11, 'fincas', TRUE),
  (12, 'galpones', TRUE),
  (13, 'incidentes_generales', TRUE),
  (14, 'inventario', TRUE),
  (15, 'categoria_inventario', TRUE),
  (16, 'sensores', TRUE),
  (17, 'tipo_sensores', TRUE),
  (18, 'registro_sensores', TRUE),
  (19, 'tipo_gallinas', TRUE),
  (20, 'ingreso_gallinas', TRUE),
  (21, 'salvamento', TRUE),
  (22, 'incidentes_gallina', TRUE),
  (23, 'aislamiento', TRUE),
  (24, 'produccion_huevos', TRUE),
  (25, 'tipo_huevos', TRUE),
  (26, 'stock', TRUE),
  (27, 'consumo_gallinas', TRUE),
  (28, 'alimento', TRUE);

-- Permisos: (modulo, rol, insertar, actualizar, seleccionar, borrar)
INSERT INTO permisos (id_modulo, id_rol, insertar, actualizar, seleccionar, borrar) VALUES
  ( 1, 1, 1, 1, 1, 1),  -- modulos
  ( 2, 1, 1, 1, 1, 1),  -- permisos
  ( 3, 1, 1, 1, 1, 1),  -- roles
  ( 4, 1, 1, 1, 1, 1),  -- usuarios
  ( 5, 1, 1, 1, 1, 1),  -- ventas
  ( 6, 1, 1, 1, 1, 1),  -- tareas
  ( 7, 1, 1, 1, 1, 1),  -- detalle_huevos
  ( 8, 1, 1, 1, 1, 1),  -- metodo_pago
  ( 9, 1, 1, 1, 1, 1),  -- detalle_salvamento
  (10, 1, 1, 1, 1, 1),  -- administradores
  (11, 1, 1, 1, 1, 1),  -- fincas
  (12, 1, 1, 1, 1, 1),  -- galpones
  (13, 1, 1, 1, 1, 1),  -- incidentes_generales
  (14, 1, 1, 1, 1, 1),  -- inventario
  (15, 1, 1, 1, 1, 1),  -- categoria_inventario
  (16, 1, 1, 1, 1, 1),  -- sensores
  (17, 1, 1, 1, 1, 1),  -- tipo_sensores
  (18, 1, 1, 1, 1, 1),  -- registro_sensores
  (19, 1, 1, 1, 1, 1),  -- tipo_gallinas
  (20, 1, 1, 1, 1, 1),  -- ingreso_gallinas
  (21, 1, 1, 1, 1, 1),  -- salvamento
  (22, 1, 1, 1, 1, 1),  -- incidentes_gallina
  (23, 1, 1, 1, 1, 1),  -- aislamiento
  (24, 1, 1, 1, 1, 1),  -- produccion_huevos
  (25, 1, 1, 1, 1, 1),  -- tipo_huevos
  (26, 1, 1, 1, 1, 1),  -- stock
  (27, 1, 1, 1, 1, 1),  -- consumo_gallinas
  (28, 1, 1, 1, 1, 1),  -- alimento
  ( 1, 2, 1, 1, 1, 0),  -- modulos
  ( 2, 2, 1, 1, 1, 0),  -- permisos
  ( 3, 2, 1, 1, 1, 1),  -- roles
  ( 4, 2, 1, 1, 1, 1),  -- usuarios
  ( 5, 2, 1, 1, 1, 1),  -- ventas
  ( 6, 2, 1, 1, 1, 1),  -- tareas
  ( 7, 2, 1, 1, 1, 1),  -- detalle_huevos
  ( 8, 2, 1, 1, 1, 1),  -- metodo_pago
  ( 9, 2, 1, 1, 1, 1),  -- detalle_salvamento
  (10, 2, 0, 0, 0, 0),  -- administradores
  (11, 2, 1, 1, 1, 1),  -- fincas
  (12, 2, 1, 1, 1, 1),  -- galpones
  (13, 2, 1, 1, 1, 1),  -- incidentes_generales
  (14, 2, 1, 1, 1, 1),  -- inventario
  (15, 2, 1, 1, 1, 1),  -- categoria_inventario
  (16, 2, 1, 1, 1, 0),  -- sensores
  (17, 2, 1, 1, 1, 0),  -- tipo_sensores
  (18, 2, 0, 0, 1, 0),  -- registro_sensores
  (19, 2, 1, 1, 1, 1),  -- tipo_gallinas
  (20, 2, 1, 1, 1, 1),  -- ingreso_gallinas
  (21, 2, 1, 1, 1, 1),  -- salvamento
  (22, 2, 1, 1, 1, 1),  -- incidentes_gallina
  (23, 2, 1, 1, 1, 1),  -- aislamiento
  (24, 2, 1, 1, 1, 1),  -- produccion_huevos
  (25, 2, 1, 1, 1, 1),  -- tipo_huevos
  (26, 2, 1, 1, 1, 1),  -- stock
  (27, 2, 1, 1, 1, 0),  -- consumo_gallinas
  (28, 2, 1, 1, 1, 0),  -- alimento
  ( 1, 3, 0, 0, 0, 0),  -- modulos
  ( 2, 3, 0, 0, 0, 0),  -- permisos
  ( 3, 3, 0, 0, 0, 0),  -- roles
  ( 4, 3, 0, 0, 0, 0),  -- usuarios
  ( 5, 3, 0, 0, 0, 0),  -- ventas
  ( 6, 3, 1, 1, 1, 1),  -- tareas
  ( 7, 3, 0, 0, 0, 0),  -- detalle_huevos
  ( 8, 3, 0, 0, 0, 0),  -- metodo_pago
  ( 9, 3, 0, 0, 0, 0),  -- detalle_salvamento
  (10, 3, 0, 0, 0, 0),  -- administradores
  (11, 3, 0, 0, 1, 0),  -- fincas
  (12, 3, 0, 0, 1, 0),  -- galpones
  (13, 3, 1, 1, 1, 1),  -- incidentes_generales
  (14, 3, 0, 0, 0, 0),  -- inventario
  (15, 3, 0, 0, 0, 0),  -- categoria_inventario
  (16, 3, 1, 1, 1, 0),  -- sensores
  (17, 3, 1, 1, 1, 0),  -- tipo_sensores
  (18, 3, 0, 0, 1, 0),  -- registro_sensores
  (19, 3, 1, 1, 1, 0),  -- tipo_gallinas
  (20, 3, 1, 1, 1, 0),  -- ingreso_gallinas
  (21, 3, 1, 1, 1, 0),  -- salvamento
  (22, 3, 1, 1, 1, 0),  -- incidentes_gallina
  (23, 3, 1, 0, 1, 0),  -- aislamiento
  (24, 3, 1, 1, 1, 0),  -- produccion_huevos
  (25, 3, 0, 0, 1, 0),  -- tipo_huevos
  (26, 3, 0, 0, 1, 0),  -- stock
  (27, 3, 1, 1, 1, 0),  -- consumo_gallinas
  (28, 3, 1, 1, 1, 0),  -- alimento
  ( 1, 4, 0, 0, 0, 0),  -- modulos
  ( 2, 4, 0, 0, 0, 0),  -- permisos
  ( 3, 4, 0, 0, 0, 0),  -- roles
  ( 4, 4, 0, 0, 0, 0),  -- usuarios
  ( 5, 4, 0, 0, 0, 0),  -- ventas
  ( 6, 4, 0, 1, 1, 0),  -- tareas
  ( 7, 4, 0, 0, 0, 0),  -- detalle_huevos
  ( 8, 4, 0, 0, 0, 0),  -- metodo_pago
  ( 9, 4, 0, 0, 0, 0),  -- detalle_salvamento
  (10, 4, 0, 0, 0, 0),  -- administradores
  (11, 4, 0, 0, 1, 0),  -- fincas
  (12, 4, 0, 0, 1, 0),  -- galpones
  (13, 4, 0, 1, 1, 0),  -- incidentes_generales
  (14, 4, 0, 0, 0, 0),  -- inventario
  (15, 4, 0, 0, 0, 0),  -- categoria_inventario
  (16, 4, 0, 0, 1, 0),  -- sensores
  (17, 4, 0, 0, 1, 0),  -- tipo_sensores
  (18, 4, 0, 0, 1, 0),  -- registro_sensores
  (19, 4, 0, 0, 1, 0),  -- tipo_gallinas
  (20, 4, 1, 1, 1, 0),  -- ingreso_gallinas
  (21, 4, 1, 1, 1, 0),  -- salvamento
  (22, 4, 1, 1, 1, 0),  -- incidentes_gallina
  (23, 4, 1, 0, 1, 0),  -- aislamiento
  (24, 4, 1, 1, 1, 0),  -- produccion_huevos
  (25, 4, 0, 0, 1, 0),  -- tipo_huevos
  (26, 4, 0, 0, 1, 0),  -- stock
  (27, 4, 1, 1, 1, 0),  -- consumo_gallinas
  (28, 4, 0, 0, 1, 0);  -- alimento

INSERT INTO metodo_pago (id_tipo, nombre, descripcion, estado) VALUES
  (1, 'Efectivo', 'Pago en efectivo (método por defecto de las ventas)', TRUE),
  (2, 'Transferencia', 'Transferencia bancaria o billetera digital', TRUE),
  (3, 'Tarjeta', 'Tarjeta débito o crédito', TRUE);

-- Los IDs 1-3 corresponden a las etiquetas AA / AAA / Super del frontend
INSERT INTO tipo_huevos (id_tipo_huevo, color, `tamaño`) VALUES
  (1, 'Rojo', 'AA'),
  (2, 'Rojo', 'AAA'),
  (3, 'Rojo', 'Super');

INSERT INTO tipo_gallinas (raza, descripcion) VALUES
  ('Hy-Line Brown', 'Ponedora de huevo rojo'),
  ('Lohmann Brown', 'Ponedora de huevo rojo de alta producción');

INSERT INTO categoria_inventario (nombre, descripcion) VALUES
  ('Herramientas', 'Herramientas y equipos de trabajo'),
  ('Medicamentos', 'Vacunas y medicamentos veterinarios'),
  ('Insumos', 'Material de cama, desinfectantes y otros insumos');

INSERT INTO tipo_sensores (nombre, descripcion, modelo, estado) VALUES
  ('Temperatura', 'Mide la temperatura ambiente del galpón', 'DHT22', TRUE),
  ('Humedad', 'Mide la humedad relativa del galpón', 'DHT22', TRUE),
  ('Luminosidad', 'Mide la intensidad de luz del galpón', 'BH1750', TRUE);
