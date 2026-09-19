-- ============================================================================
-- BELLEZA INTEGRAL - SUSCRIPCIONES MENSUALES
-- MySQL 8.0+
-- Requiere: usuarios, auditoria_cambios y auditoria_eventos.
-- Los pagos son demostrativos: no existe un cargo bancario real.
-- ============================================================================

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS planes_suscripcion (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255) NULL,
    precio_mensual DECIMAL(10,2) NOT NULL,
    duracion_meses TINYINT UNSIGNED NOT NULL DEFAULT 1,
    descuento_servicios TINYINT UNSIGNED NOT NULL DEFAULT 0,
    descuento_productos TINYINT UNSIGNED NOT NULL DEFAULT 0,
    acumulable_promociones TINYINT(1) NOT NULL DEFAULT 0,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_planes_suscripcion_nombre (nombre),
    KEY idx_planes_suscripcion_activo (activo),
    CONSTRAINT chk_plan_suscripcion_precio CHECK (precio_mensual >= 0),
    CONSTRAINT chk_plan_suscripcion_duracion CHECK (duracion_meses BETWEEN 1 AND 24),
    CONSTRAINT chk_plan_suscripcion_desc_serv CHECK (descuento_servicios BETWEEN 0 AND 100),
    CONSTRAINT chk_plan_suscripcion_desc_prod CHECK (descuento_productos BETWEEN 0 AND 100),
    CONSTRAINT chk_plan_suscripcion_acum CHECK (acumulable_promociones IN (0,1)),
    CONSTRAINT chk_plan_suscripcion_activo CHECK (activo IN (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS suscripciones (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id INT UNSIGNED NOT NULL,
    plan_id INT UNSIGNED NOT NULL,
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    estado ENUM('activa','vencida','cancelada','suspendida') NOT NULL DEFAULT 'activa',
    precio_mensual_contratado DECIMAL(10,2) NOT NULL,
    duracion_meses_contratada TINYINT UNSIGNED NOT NULL,
    descuento_servicios_contratado TINYINT UNSIGNED NOT NULL DEFAULT 0,
    descuento_productos_contratado TINYINT UNSIGNED NOT NULL DEFAULT 0,
    acumulable_promociones_contratado TINYINT(1) NOT NULL DEFAULT 0,
    fecha_cancelacion DATETIME NULL,
    motivo_cancelacion VARCHAR(255) NULL,
    clave_operacion VARCHAR(64) NOT NULL,
    solicitud_hash CHAR(64) NOT NULL,
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_suscripciones_usuario_clave (usuario_id, clave_operacion),
    KEY idx_suscripciones_usuario_estado (usuario_id, estado),
    KEY idx_suscripciones_fecha_fin (fecha_fin),
    KEY idx_suscripciones_plan (plan_id),
    CONSTRAINT fk_suscripciones_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_suscripciones_plan FOREIGN KEY (plan_id) REFERENCES planes_suscripcion(id),
    CONSTRAINT chk_suscripciones_fechas CHECK (fecha_fin > fecha_inicio),
    CONSTRAINT chk_suscripciones_precio CHECK (precio_mensual_contratado >= 0),
    CONSTRAINT chk_suscripciones_duracion CHECK (duracion_meses_contratada BETWEEN 1 AND 24),
    CONSTRAINT chk_suscripciones_desc_serv CHECK (descuento_servicios_contratado BETWEEN 0 AND 100),
    CONSTRAINT chk_suscripciones_desc_prod CHECK (descuento_productos_contratado BETWEEN 0 AND 100),
    CONSTRAINT chk_suscripciones_acum CHECK (acumulable_promociones_contratado IN (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pagos_suscripcion (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    suscripcion_id INT UNSIGNED NOT NULL,
    usuario_id INT UNSIGNED NOT NULL,
    periodo_inicio DATETIME NOT NULL,
    periodo_fin DATETIME NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    metodo_pago ENUM('efectivo','tarjeta_simulada') NOT NULL,
    estado ENUM('aprobado','rechazado','reembolsado') NOT NULL DEFAULT 'aprobado',
    tarjeta_ultimos4 VARCHAR(4) NULL,
    referencia_pago VARCHAR(100) NULL,
    clave_operacion VARCHAR(64) NOT NULL,
    solicitud_hash CHAR(64) NOT NULL,
    fecha_pago DATETIME NULL,
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_pago_suscripcion_usuario_clave (usuario_id, clave_operacion),
    KEY idx_pago_suscripcion_suscripcion (suscripcion_id),
    KEY idx_pago_suscripcion_usuario_fecha (usuario_id, fecha_creacion),
    CONSTRAINT fk_pago_suscripcion FOREIGN KEY (suscripcion_id) REFERENCES suscripciones(id),
    CONSTRAINT fk_pago_suscripcion_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT chk_pago_suscripcion_periodo CHECK (periodo_fin > periodo_inicio),
    CONSTRAINT chk_pago_suscripcion_monto CHECK (monto >= 0),
    CONSTRAINT chk_pago_suscripcion_tarjeta CHECK (
        (metodo_pago='tarjeta_simulada' AND tarjeta_ultimos4 IS NOT NULL)
        OR (metodo_pago='efectivo' AND tarjeta_ultimos4 IS NULL)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE OR REPLACE VIEW vw_suscripciones_detalle AS
SELECT
    s.id AS suscripcion_id,
    s.usuario_id,
    u.nombre AS cliente,
    u.email,
    s.plan_id,
    p.nombre AS plan,
    p.descripcion AS plan_descripcion,
    s.fecha_inicio,
    s.fecha_fin,
    s.estado AS estado_registrado,
    CASE
        WHEN s.estado='activa' AND s.fecha_fin<=NOW() THEN 'vencida'
        ELSE s.estado
    END AS estado_efectivo,
    s.precio_mensual_contratado,
    s.duracion_meses_contratada,
    s.descuento_servicios_contratado,
    s.descuento_productos_contratado,
    s.acumulable_promociones_contratado,
    s.fecha_cancelacion,
    s.motivo_cancelacion,
    s.fecha_creacion,
    s.fecha_actualizacion
FROM suscripciones s
JOIN usuarios u ON u.id=s.usuario_id
JOIN planes_suscripcion p ON p.id=s.plan_id;

CREATE OR REPLACE VIEW vw_suscripciones_activas AS
SELECT *
FROM vw_suscripciones_detalle
WHERE estado_registrado='activa'
  AND fecha_inicio<=NOW()
  AND fecha_fin>NOW();

DROP TRIGGER IF EXISTS trg_suscripciones_bi_validar;
DROP TRIGGER IF EXISTS trg_suscripciones_bu_validar;
DROP TRIGGER IF EXISTS trg_pagos_suscripcion_bu_bloquear;
DROP TRIGGER IF EXISTS trg_pagos_suscripcion_bd_bloquear;
DROP TRIGGER IF EXISTS trg_aud_planes_suscripcion_ai;
DROP TRIGGER IF EXISTS trg_aud_planes_suscripcion_au;
DROP TRIGGER IF EXISTS trg_aud_suscripciones_ai;
DROP TRIGGER IF EXISTS trg_aud_suscripciones_au;
DROP TRIGGER IF EXISTS trg_aud_pagos_suscripcion_ai;

DELIMITER $$

CREATE TRIGGER trg_suscripciones_bi_validar
BEFORE INSERT ON suscripciones
FOR EACH ROW
BEGIN
    DECLARE v_cliente INT DEFAULT 0;
    DECLARE v_plan INT DEFAULT 0;
    DECLARE v_activas INT DEFAULT 0;

    SELECT COUNT(*) INTO v_cliente
    FROM usuarios
    WHERE id=NEW.usuario_id AND rol='cliente' AND activo=1;

    IF v_cliente=0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='La suscripcion requiere un cliente activo';
    END IF;

    SELECT COUNT(*) INTO v_plan
    FROM planes_suscripcion
    WHERE id=NEW.plan_id AND activo=1;

    IF v_plan=0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='El plan de suscripcion no esta disponible';
    END IF;

    SELECT COUNT(*) INTO v_activas
    FROM suscripciones
    WHERE usuario_id=NEW.usuario_id
      AND estado='activa'
      AND fecha_fin>NOW();

    IF NEW.estado='activa' AND v_activas>0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='El cliente ya posee una suscripcion activa';
    END IF;
END$$

CREATE TRIGGER trg_suscripciones_bu_validar
BEFORE UPDATE ON suscripciones
FOR EACH ROW
BEGIN
    IF NEW.usuario_id<>OLD.usuario_id
       OR NEW.plan_id<>OLD.plan_id
       OR NEW.precio_mensual_contratado<>OLD.precio_mensual_contratado
       OR NEW.duracion_meses_contratada<>OLD.duracion_meses_contratada
       OR NEW.descuento_servicios_contratado<>OLD.descuento_servicios_contratado
       OR NEW.descuento_productos_contratado<>OLD.descuento_productos_contratado
       OR NEW.acumulable_promociones_contratado<>OLD.acumulable_promociones_contratado
       OR NEW.clave_operacion<>OLD.clave_operacion
       OR NEW.solicitud_hash<>OLD.solicitud_hash THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Las condiciones historicas de la suscripcion son inmutables';
    END IF;
END$$

CREATE TRIGGER trg_pagos_suscripcion_bu_bloquear
BEFORE UPDATE ON pagos_suscripcion
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='pagos_suscripcion es inmutable';
END$$

CREATE TRIGGER trg_pagos_suscripcion_bd_bloquear
BEFORE DELETE ON pagos_suscripcion
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='No se permite eliminar pagos de suscripcion';
END$$

CREATE TRIGGER trg_aud_planes_suscripcion_ai
AFTER INSERT ON planes_suscripcion
FOR EACH ROW
BEGIN
    INSERT INTO auditoria_cambios(
        usuario_bd,usuario_app_id,ip_app,correlacion_id,
        tabla,registro_id,operacion,datos_anteriores,datos_nuevos
    ) VALUES(
        CURRENT_USER(),@app_usuario_id,@app_ip,@app_correlacion_id,
        'planes_suscripcion',NEW.id,'INSERT',NULL,
        JSON_OBJECT(
            'nombre',NEW.nombre,
            'precio_mensual',NEW.precio_mensual,
            'duracion_meses',NEW.duracion_meses,
            'descuento_servicios',NEW.descuento_servicios,
            'descuento_productos',NEW.descuento_productos,
            'acumulable_promociones',NEW.acumulable_promociones,
            'activo',NEW.activo
        )
    );
END$$

CREATE TRIGGER trg_aud_planes_suscripcion_au
AFTER UPDATE ON planes_suscripcion
FOR EACH ROW
BEGIN
    INSERT INTO auditoria_cambios(
        usuario_bd,usuario_app_id,ip_app,correlacion_id,
        tabla,registro_id,operacion,datos_anteriores,datos_nuevos
    ) VALUES(
        CURRENT_USER(),@app_usuario_id,@app_ip,@app_correlacion_id,
        'planes_suscripcion',NEW.id,'UPDATE',
        JSON_OBJECT('nombre',OLD.nombre,'precio_mensual',OLD.precio_mensual,'activo',OLD.activo),
        JSON_OBJECT('nombre',NEW.nombre,'precio_mensual',NEW.precio_mensual,'activo',NEW.activo)
    );
END$$

CREATE TRIGGER trg_aud_suscripciones_ai
AFTER INSERT ON suscripciones
FOR EACH ROW
BEGIN
    INSERT INTO auditoria_cambios(
        usuario_bd,usuario_app_id,ip_app,correlacion_id,
        tabla,registro_id,operacion,datos_anteriores,datos_nuevos
    ) VALUES(
        CURRENT_USER(),@app_usuario_id,@app_ip,@app_correlacion_id,
        'suscripciones',NEW.id,'INSERT',NULL,
        JSON_OBJECT(
            'usuario_id',NEW.usuario_id,
            'plan_id',NEW.plan_id,
            'fecha_inicio',NEW.fecha_inicio,
            'fecha_fin',NEW.fecha_fin,
            'estado',NEW.estado,
            'precio_mensual_contratado',NEW.precio_mensual_contratado
        )
    );
END$$

CREATE TRIGGER trg_aud_suscripciones_au
AFTER UPDATE ON suscripciones
FOR EACH ROW
BEGIN
    INSERT INTO auditoria_cambios(
        usuario_bd,usuario_app_id,ip_app,correlacion_id,
        tabla,registro_id,operacion,datos_anteriores,datos_nuevos
    ) VALUES(
        CURRENT_USER(),@app_usuario_id,@app_ip,@app_correlacion_id,
        'suscripciones',NEW.id,'UPDATE',
        JSON_OBJECT(
            'fecha_fin',OLD.fecha_fin,
            'estado',OLD.estado,
            'fecha_cancelacion',OLD.fecha_cancelacion,
            'motivo_cancelacion',OLD.motivo_cancelacion
        ),
        JSON_OBJECT(
            'fecha_fin',NEW.fecha_fin,
            'estado',NEW.estado,
            'fecha_cancelacion',NEW.fecha_cancelacion,
            'motivo_cancelacion',NEW.motivo_cancelacion
        )
    );
END$$

CREATE TRIGGER trg_aud_pagos_suscripcion_ai
AFTER INSERT ON pagos_suscripcion
FOR EACH ROW
BEGIN
    INSERT INTO auditoria_cambios(
        usuario_bd,usuario_app_id,ip_app,correlacion_id,
        tabla,registro_id,operacion,datos_anteriores,datos_nuevos
    ) VALUES(
        CURRENT_USER(),@app_usuario_id,@app_ip,@app_correlacion_id,
        'pagos_suscripcion',NEW.id,'INSERT',NULL,
        JSON_OBJECT(
            'suscripcion_id',NEW.suscripcion_id,
            'usuario_id',NEW.usuario_id,
            'periodo_inicio',NEW.periodo_inicio,
            'periodo_fin',NEW.periodo_fin,
            'monto',NEW.monto,
            'metodo_pago',NEW.metodo_pago,
            'estado',NEW.estado,
            'tarjeta_ultimos4',NEW.tarjeta_ultimos4,
            'referencia_pago',NEW.referencia_pago
        )
    );
END$$

DELIMITER ;

INSERT INTO planes_suscripcion(
    nombre,descripcion,precio_mensual,duracion_meses,
    descuento_servicios,descuento_productos,acumulable_promociones,activo
)
SELECT
    'Membresía Mensual',
    'Plan mensual de Belleza Integral.',
    100.00,1,10,5,0,1
WHERE NOT EXISTS (
    SELECT 1 FROM planes_suscripcion WHERE nombre='Membresía Mensual'
);
