-- =====================================================================
--  AVISENA - Esquema de base de datos (MySQL 8.0+)
--  Coincide con las consultas del backend (app/crud y app/router).
--  Ejecutar sobre una base vacía:  mysql -u root -p < 01_schema.sql
-- =====================================================================

CREATE DATABASE IF NOT EXISTS avisena
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
USE avisena;

SET NAMES utf8mb4;
SET time_zone = '-05:00';

-- ---------------------------------------------------------------------
--  1. SEGURIDAD: roles, módulos, permisos y usuarios
-- ---------------------------------------------------------------------
CREATE TABLE roles (
    id_rol        TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre_rol    VARCHAR(30)  NOT NULL,
    descripcion   VARCHAR(500) NULL,
    estado        BOOLEAN      NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id_rol),
    UNIQUE KEY uq_roles_nombre (nombre_rol)
) ENGINE=InnoDB;

CREATE TABLE modulos (
    id_modulo     TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre_modulo VARCHAR(30) NOT NULL,
    estado        BOOLEAN     NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id_modulo),
    UNIQUE KEY uq_modulos_nombre (nombre_modulo)
) ENGINE=InnoDB;

CREATE TABLE permisos (
    id_modulo   TINYINT UNSIGNED NOT NULL,
    id_rol      TINYINT UNSIGNED NOT NULL,
    insertar    BOOLEAN NOT NULL DEFAULT FALSE,
    actualizar  BOOLEAN NOT NULL DEFAULT FALSE,
    seleccionar BOOLEAN NOT NULL DEFAULT FALSE,
    borrar      BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id_modulo, id_rol),
    KEY idx_permisos_rol (id_rol),
    CONSTRAINT fk_permisos_modulo FOREIGN KEY (id_modulo) REFERENCES modulos (id_modulo) ON DELETE CASCADE,
    CONSTRAINT fk_permisos_rol    FOREIGN KEY (id_rol)    REFERENCES roles (id_rol)       ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE usuarios (
    id_usuario          INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    nombre              VARCHAR(70)      NOT NULL,
    documento           VARCHAR(20)      NOT NULL,
    id_rol              TINYINT UNSIGNED NOT NULL,
    email               VARCHAR(100)     NOT NULL,
    telefono            VARCHAR(15)      NOT NULL,
    pass_hash           VARCHAR(255)     NOT NULL,
    estado              BOOLEAN          NOT NULL DEFAULT TRUE,
    reset_token         CHAR(6)          NULL,
    reset_token_expiry  DATETIME         NULL,
    creado_en           TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_usuario),
    -- Los nombres de las llaves contienen "email" / "documento": el backend los
    -- usa para mostrar el mensaje de duplicado correcto.
    UNIQUE KEY uq_usuarios_email (email),
    UNIQUE KEY uq_usuarios_documento (documento),
    KEY idx_usuarios_rol (id_rol),
    CONSTRAINT fk_usuarios_rol FOREIGN KEY (id_rol) REFERENCES roles (id_rol)
) ENGINE=InnoDB;

CREATE TABLE tareas (
    id_tarea         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_usuario       INT UNSIGNED NOT NULL,
    descripcion      VARCHAR(255) NOT NULL,
    fecha_hora_init  DATETIME     NOT NULL,
    fecha_hora_fin   DATETIME     NOT NULL,
    estado           ENUM('Asignada','Pendiente','En proceso','Completada','Cancelada') NOT NULL DEFAULT 'Asignada',
    PRIMARY KEY (id_tarea),
    KEY idx_tareas_usuario_fecha (id_usuario, fecha_hora_init),
    KEY idx_tareas_fecha (fecha_hora_init),
    CONSTRAINT fk_tareas_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
--  2. INFRAESTRUCTURA: fincas, galpones, inventario
-- ---------------------------------------------------------------------
CREATE TABLE fincas (
    id_finca  INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    nombre    VARCHAR(30)   NOT NULL,
    longitud  DECIMAL(9,6)  NOT NULL,
    latitud   DECIMAL(9,6)  NOT NULL,
    estado    BOOLEAN       NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id_finca),
    CONSTRAINT chk_fincas_coordenadas CHECK (latitud BETWEEN -90 AND 90 AND longitud BETWEEN -180 AND 180)
) ENGINE=InnoDB;

CREATE TABLE galpones (
    id_galpon    INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_finca     INT UNSIGNED NOT NULL,
    nombre       VARCHAR(70)  NOT NULL,
    capacidad    INT          NOT NULL,
    cant_actual  INT          NOT NULL DEFAULT 0,   -- lo mantienen los triggers de ingreso_gallinas
    estado       BOOLEAN      NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id_galpon),
    KEY idx_galpones_finca (id_finca),
    KEY idx_galpones_estado (estado),
    CONSTRAINT fk_galpones_finca FOREIGN KEY (id_finca) REFERENCES fincas (id_finca),
    CONSTRAINT chk_galpones_capacidad CHECK (capacidad > 0),
    CONSTRAINT chk_galpones_cantidad  CHECK (cant_actual >= 0)
) ENGINE=InnoDB;

CREATE TABLE categoria_inventario (
    id_categoria  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(100) NOT NULL,
    descripcion   VARCHAR(255) NULL,
    PRIMARY KEY (id_categoria),
    UNIQUE KEY uq_categoria_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE inventario_finca (
    id_inventario  INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    nombre         VARCHAR(100)   NOT NULL,
    cantidad       DECIMAL(10,2)  NOT NULL,
    unidad_medida  VARCHAR(50)    NOT NULL,
    descripcion    VARCHAR(255)   NULL,
    id_categoria   INT UNSIGNED   NOT NULL,
    id_finca       INT UNSIGNED   NOT NULL,
    PRIMARY KEY (id_inventario),
    KEY idx_inventario_finca (id_finca),
    KEY idx_inventario_categoria (id_categoria),
    CONSTRAINT fk_inventario_categoria FOREIGN KEY (id_categoria) REFERENCES categoria_inventario (id_categoria),
    CONSTRAINT fk_inventario_finca     FOREIGN KEY (id_finca)     REFERENCES fincas (id_finca),
    CONSTRAINT chk_inventario_cantidad CHECK (cantidad >= 0)
) ENGINE=InnoDB;

CREATE TABLE incidentes_generales (
    id_incidente   INT UNSIGNED NOT NULL AUTO_INCREMENT,
    descripcion    VARCHAR(255) NOT NULL,
    fecha_hora     DATETIME     NOT NULL,
    id_finca       INT UNSIGNED NOT NULL,
    esta_resuelta  BOOLEAN      NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id_incidente),
    KEY idx_incgen_estado_fecha (esta_resuelta, fecha_hora),
    KEY idx_incgen_fecha (fecha_hora),
    KEY idx_incgen_finca (id_finca),
    CONSTRAINT fk_incgen_finca FOREIGN KEY (id_finca) REFERENCES fincas (id_finca)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
--  3. SENSORES
-- ---------------------------------------------------------------------
CREATE TABLE tipo_sensores (
    id_tipo      INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre       VARCHAR(70)  NOT NULL,
    descripcion  VARCHAR(255) NOT NULL,
    modelo       VARCHAR(70)  NOT NULL,
    estado       BOOLEAN      NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id_tipo)
) ENGINE=InnoDB;

CREATE TABLE sensores (
    id_sensor       INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre          VARCHAR(255) NOT NULL,
    id_tipo_sensor  INT UNSIGNED NOT NULL,
    id_galpon       INT UNSIGNED NOT NULL,
    descripcion     VARCHAR(140) NOT NULL,
    estado          BOOLEAN      NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id_sensor),
    KEY idx_sensores_tipo (id_tipo_sensor),
    KEY idx_sensores_galpon (id_galpon),
    CONSTRAINT fk_sensores_tipo   FOREIGN KEY (id_tipo_sensor) REFERENCES tipo_sensores (id_tipo),
    CONSTRAINT fk_sensores_galpon FOREIGN KEY (id_galpon)      REFERENCES galpones (id_galpon)
) ENGINE=InnoDB;

CREATE TABLE registro_sensores (
    id_registro  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_sensor    INT UNSIGNED    NOT NULL,
    dato_sensor  DOUBLE          NOT NULL,
    fecha_hora   DATETIME        NOT NULL,
    u_medida     VARCHAR(10)     NOT NULL,
    PRIMARY KEY (id_registro),
    KEY idx_regsens_fecha (fecha_hora),
    KEY idx_regsens_sensor_fecha (id_sensor, fecha_hora),
    CONSTRAINT fk_regsens_sensor FOREIGN KEY (id_sensor) REFERENCES sensores (id_sensor)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
--  4. GALLINAS: tipos, ingresos, incidentes, aislamientos, salvamento
-- ---------------------------------------------------------------------
CREATE TABLE tipo_gallinas (
    id_tipo_gallinas  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    raza              VARCHAR(30)  NOT NULL,
    descripcion       VARCHAR(100) NOT NULL,
    PRIMARY KEY (id_tipo_gallinas),
    UNIQUE KEY uq_tipo_gallinas (raza, descripcion)
) ENGINE=InnoDB;

CREATE TABLE ingreso_gallinas (
    id_ingreso         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_galpon          INT UNSIGNED NOT NULL,
    fecha              DATE         NOT NULL,
    id_tipo_gallina    INT UNSIGNED NOT NULL,
    cantidad_gallinas  INT          NOT NULL,
    PRIMARY KEY (id_ingreso),
    KEY idx_ingreso_galpon (id_galpon),
    KEY idx_ingreso_fecha (fecha),
    KEY idx_ingreso_tipo (id_tipo_gallina),
    CONSTRAINT fk_ingreso_galpon FOREIGN KEY (id_galpon)       REFERENCES galpones (id_galpon),
    CONSTRAINT fk_ingreso_tipo   FOREIGN KEY (id_tipo_gallina) REFERENCES tipo_gallinas (id_tipo_gallinas),
    CONSTRAINT chk_ingreso_cantidad CHECK (cantidad_gallinas > 0)
) ENGINE=InnoDB;

CREATE TABLE incidentes_gallina (
    id_inc_gallina  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    galpon_origen   INT UNSIGNED NOT NULL,
    tipo_incidente  ENUM('Enfermedad','Herida','Muerte','Fuga','Ataque Depredador','Produccion',
                         'Alimentacion','Plaga','Estres termico','Otro') NOT NULL,
    cantidad        INT          NOT NULL,
    descripcion     VARCHAR(255) NOT NULL,
    fecha_hora      DATETIME     NOT NULL,
    esta_resuelto   BOOLEAN      NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id_inc_gallina),
    KEY idx_incgal_galpon (galpon_origen),
    KEY idx_incgal_fecha (fecha_hora),
    KEY idx_incgal_estado (esta_resuelto),
    CONSTRAINT fk_incgal_galpon FOREIGN KEY (galpon_origen) REFERENCES galpones (id_galpon),
    CONSTRAINT chk_incgal_cantidad CHECK (cantidad > 0)
) ENGINE=InnoDB;

CREATE TABLE aislamiento (
    id_aislamiento        INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_incidente_gallina  INT UNSIGNED NOT NULL,
    fecha_hora            DATETIME     NOT NULL,
    id_galpon             INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_aislamiento),
    KEY idx_aislamiento_incidente (id_incidente_gallina),
    KEY idx_aislamiento_galpon (id_galpon),
    KEY idx_aislamiento_fecha (fecha_hora),
    CONSTRAINT fk_aislamiento_incidente FOREIGN KEY (id_incidente_gallina) REFERENCES incidentes_gallina (id_inc_gallina),
    CONSTRAINT fk_aislamiento_galpon    FOREIGN KEY (id_galpon)            REFERENCES galpones (id_galpon)
) ENGINE=InnoDB;

-- Gallinas de descarte disponibles para la venta
CREATE TABLE salvamento (
    id_salvamento      INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_galpon          INT UNSIGNED NOT NULL,
    fecha              DATE         NOT NULL,
    id_tipo_gallina    INT UNSIGNED NOT NULL,
    cantidad_gallinas  INT          NOT NULL,   -- disponibles; baja con cada venta
    PRIMARY KEY (id_salvamento),
    KEY idx_salvamento_fecha (fecha),
    KEY idx_salvamento_galpon (id_galpon),
    KEY idx_salvamento_tipo (id_tipo_gallina),
    CONSTRAINT fk_salvamento_galpon FOREIGN KEY (id_galpon)       REFERENCES galpones (id_galpon),
    CONSTRAINT fk_salvamento_tipo   FOREIGN KEY (id_tipo_gallina) REFERENCES tipo_gallinas (id_tipo_gallinas),
    CONSTRAINT chk_salvamento_cantidad CHECK (cantidad_gallinas >= 0)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
--  5. ALIMENTO
-- ---------------------------------------------------------------------
CREATE TABLE alimento (
    id_alimento    INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre         VARCHAR(100) NOT NULL,
    cantidad       INT          NOT NULL,     -- kg disponibles; baja con cada consumo
    fecha_ingreso  DATE         NOT NULL,
    PRIMARY KEY (id_alimento),
    KEY idx_alimento_fecha (fecha_ingreso),
    CONSTRAINT chk_alimento_cantidad CHECK (cantidad >= 0)
) ENGINE=InnoDB;

CREATE TABLE consumo_gallinas (
    id_consumo         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_alimento        INT UNSIGNED NOT NULL,
    cantidad_alimento  INT          NOT NULL,
    id_galpon          INT UNSIGNED NOT NULL,
    fecha_registro     DATE         NOT NULL,
    PRIMARY KEY (id_consumo),
    KEY idx_consumo_fecha (fecha_registro),
    KEY idx_consumo_galpon (id_galpon),
    KEY idx_consumo_alimento (id_alimento),
    CONSTRAINT fk_consumo_alimento FOREIGN KEY (id_alimento) REFERENCES alimento (id_alimento),
    CONSTRAINT fk_consumo_galpon   FOREIGN KEY (id_galpon)   REFERENCES galpones (id_galpon),
    CONSTRAINT chk_consumo_cantidad CHECK (cantidad_alimento > 0)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
--  6. PRODUCCIÓN Y STOCK
-- ---------------------------------------------------------------------
CREATE TABLE tipo_huevos (
    id_tipo_huevo  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    color          VARCHAR(30) NOT NULL,
    `tamaño`       VARCHAR(30) NOT NULL,
    PRIMARY KEY (id_tipo_huevo),
    UNIQUE KEY uq_tipo_huevos (color, `tamaño`)
) ENGINE=InnoDB;

CREATE TABLE produccion_huevos (
    id_produccion  INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    id_galpon      INT UNSIGNED     NOT NULL,
    cantidad       INT              NOT NULL,
    fecha          DATE             NOT NULL,
    id_tipo_huevo  TINYINT UNSIGNED NOT NULL,
    PRIMARY KEY (id_produccion),
    KEY idx_produccion_fecha (fecha),
    KEY idx_produccion_galpon (id_galpon),
    KEY idx_produccion_tipo (id_tipo_huevo),
    CONSTRAINT fk_produccion_galpon FOREIGN KEY (id_galpon)     REFERENCES galpones (id_galpon),
    CONSTRAINT fk_produccion_tipo   FOREIGN KEY (id_tipo_huevo) REFERENCES tipo_huevos (id_tipo_huevo),
    CONSTRAINT chk_produccion_cantidad CHECK (cantidad >= 0)
) ENGINE=InnoDB;

-- Existencias de huevos por tipo y unidad (lo alimenta produccion_huevos
-- mediante triggers y lo descuentan las ventas).
CREATE TABLE stock (
    id_producto          INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    nombre_producto      VARCHAR(50)      NOT NULL,
    tipo                 TINYINT UNSIGNED NULL,
    unidad_medida        ENUM('unidad','panal','docena','medio_panal') NOT NULL,
    cantidad_disponible  INT              NOT NULL DEFAULT 0,
    actualizado_en       TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_producto),
    UNIQUE KEY uq_stock_producto (nombre_producto, tipo, unidad_medida),
    CONSTRAINT fk_stock_tipo FOREIGN KEY (tipo) REFERENCES tipo_huevos (id_tipo_huevo),
    CONSTRAINT chk_stock_cantidad CHECK (cantidad_disponible >= 0)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
--  7. VENTAS
-- ---------------------------------------------------------------------
CREATE TABLE metodo_pago (
    id_tipo      TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre       VARCHAR(30)  NOT NULL,
    descripcion  VARCHAR(100) NOT NULL,
    estado       BOOLEAN      NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id_tipo),
    UNIQUE KEY uq_metodo_pago_nombre (nombre)
) ENGINE=InnoDB;

-- El total NO se guarda: se calcula a partir de los detalles.
CREATE TABLE ventas (
    id_venta    INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    fecha_hora  DATETIME         NOT NULL,
    id_usuario  INT UNSIGNED     NOT NULL,
    tipo_pago   TINYINT UNSIGNED NOT NULL DEFAULT 1,
    estado      BOOLEAN          NOT NULL DEFAULT TRUE,   -- FALSE = anulada
    PRIMARY KEY (id_venta),
    KEY idx_ventas_fecha (fecha_hora),
    KEY idx_ventas_usuario (id_usuario),
    KEY idx_ventas_tipo_pago (tipo_pago),
    CONSTRAINT fk_ventas_usuario   FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario),
    CONSTRAINT fk_ventas_tipo_pago FOREIGN KEY (tipo_pago)  REFERENCES metodo_pago (id_tipo)
) ENGINE=InnoDB;

CREATE TABLE detalle_huevos (
    id_detalle       INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    id_producto      INT UNSIGNED  NOT NULL,
    cantidad         INT           NOT NULL,
    id_venta         INT UNSIGNED  NOT NULL,
    valor_descuento  DECIMAL(12,2) NOT NULL DEFAULT 0,
    precio_venta     DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (id_detalle),
    KEY idx_dethuevos_venta (id_venta),
    KEY idx_dethuevos_producto (id_producto),
    CONSTRAINT fk_dethuevos_producto FOREIGN KEY (id_producto) REFERENCES stock (id_producto),
    CONSTRAINT fk_dethuevos_venta    FOREIGN KEY (id_venta)    REFERENCES ventas (id_venta),
    CONSTRAINT chk_dethuevos_valores CHECK (cantidad > 0 AND precio_venta >= 0 AND valor_descuento >= 0)
) ENGINE=InnoDB;

CREATE TABLE detalle_salvamento (
    id_detalle       INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    id_producto      INT UNSIGNED  NOT NULL,   -- id_salvamento
    cantidad         INT           NOT NULL,
    id_venta         INT UNSIGNED  NOT NULL,
    valor_descuento  DECIMAL(12,2) NOT NULL DEFAULT 0,
    precio_venta     DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (id_detalle),
    KEY idx_detsalv_venta (id_venta),
    KEY idx_detsalv_producto (id_producto),
    CONSTRAINT fk_detsalv_salvamento FOREIGN KEY (id_producto) REFERENCES salvamento (id_salvamento),
    CONSTRAINT fk_detsalv_venta      FOREIGN KEY (id_venta)    REFERENCES ventas (id_venta),
    CONSTRAINT chk_detsalv_valores CHECK (cantidad > 0 AND precio_venta >= 0 AND valor_descuento >= 0)
) ENGINE=InnoDB;

-- =====================================================================
--  TRIGGERS: mantienen los totales calculados
-- =====================================================================
DELIMITER $$

-- Ocupación del galpón (galpones.cant_actual) según los ingresos de gallinas
CREATE TRIGGER trg_ingreso_ai AFTER INSERT ON ingreso_gallinas FOR EACH ROW
BEGIN
    UPDATE galpones SET cant_actual = cant_actual + NEW.cantidad_gallinas
    WHERE id_galpon = NEW.id_galpon;
END$$

CREATE TRIGGER trg_ingreso_au AFTER UPDATE ON ingreso_gallinas FOR EACH ROW
BEGIN
    UPDATE galpones SET cant_actual = GREATEST(cant_actual - OLD.cantidad_gallinas, 0)
    WHERE id_galpon = OLD.id_galpon;
    UPDATE galpones SET cant_actual = cant_actual + NEW.cantidad_gallinas
    WHERE id_galpon = NEW.id_galpon;
END$$

CREATE TRIGGER trg_ingreso_ad AFTER DELETE ON ingreso_gallinas FOR EACH ROW
BEGIN
    UPDATE galpones SET cant_actual = GREATEST(cant_actual - OLD.cantidad_gallinas, 0)
    WHERE id_galpon = OLD.id_galpon;
END$$

-- Stock de huevos (en unidades) según la producción registrada
CREATE TRIGGER trg_produccion_ai AFTER INSERT ON produccion_huevos FOR EACH ROW
BEGIN
    INSERT INTO stock (nombre_producto, tipo, unidad_medida, cantidad_disponible)
    VALUES ('Huevos', NEW.id_tipo_huevo, 'unidad', NEW.cantidad)
    ON DUPLICATE KEY UPDATE cantidad_disponible = cantidad_disponible + NEW.cantidad;
END$$

CREATE TRIGGER trg_produccion_au AFTER UPDATE ON produccion_huevos FOR EACH ROW
BEGIN
    UPDATE stock SET cantidad_disponible = GREATEST(cantidad_disponible - OLD.cantidad, 0)
    WHERE nombre_producto = 'Huevos' AND tipo = OLD.id_tipo_huevo AND unidad_medida = 'unidad';
    INSERT INTO stock (nombre_producto, tipo, unidad_medida, cantidad_disponible)
    VALUES ('Huevos', NEW.id_tipo_huevo, 'unidad', NEW.cantidad)
    ON DUPLICATE KEY UPDATE cantidad_disponible = cantidad_disponible + NEW.cantidad;
END$$

CREATE TRIGGER trg_produccion_ad AFTER DELETE ON produccion_huevos FOR EACH ROW
BEGIN
    UPDATE stock SET cantidad_disponible = GREATEST(cantidad_disponible - OLD.cantidad, 0)
    WHERE nombre_producto = 'Huevos' AND tipo = OLD.id_tipo_huevo AND unidad_medida = 'unidad';
END$$

-- Existencias de alimento según los consumos (falla si no alcanza)
CREATE TRIGGER trg_consumo_ai AFTER INSERT ON consumo_gallinas FOR EACH ROW
BEGIN
    UPDATE alimento SET cantidad = cantidad - NEW.cantidad_alimento
    WHERE id_alimento = NEW.id_alimento;
END$$

CREATE TRIGGER trg_consumo_au AFTER UPDATE ON consumo_gallinas FOR EACH ROW
BEGIN
    UPDATE alimento SET cantidad = cantidad + OLD.cantidad_alimento
    WHERE id_alimento = OLD.id_alimento;
    UPDATE alimento SET cantidad = cantidad - NEW.cantidad_alimento
    WHERE id_alimento = NEW.id_alimento;
END$$

CREATE TRIGGER trg_consumo_ad AFTER DELETE ON consumo_gallinas FOR EACH ROW
BEGIN
    UPDATE alimento SET cantidad = cantidad + OLD.cantidad_alimento
    WHERE id_alimento = OLD.id_alimento;
END$$

DELIMITER ;
