-- Capa de integridad para el esquema aislado de CI.
-- Replica los objetos que la API espera: auditoría, vistas, rutinas y triggers.

CREATE TABLE IF NOT EXISTS auditoria_cambios (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    fecha_evento DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    usuario_bd VARCHAR(255) NOT NULL,
    usuario_app_id BIGINT UNSIGNED NULL,
    ip_app VARCHAR(45) NULL,
    correlacion_id CHAR(36) NULL,
    tabla VARCHAR(64) NOT NULL,
    registro_id BIGINT UNSIGNED NULL,
    operacion ENUM('INSERT','UPDATE','DELETE') NOT NULL,
    datos_anteriores JSON NULL,
    datos_nuevos JSON NULL,
    PRIMARY KEY (id),
    INDEX idx_auditoria_fecha (fecha_evento),
    INDEX idx_auditoria_tabla_registro (tabla,registro_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS auditoria_eventos (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    fecha_evento DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    usuario_app_id BIGINT UNSIGNED NULL,
    ip_app VARCHAR(45) NULL,
    correlacion_id CHAR(36) NULL,
    tipo_evento VARCHAR(80) NOT NULL,
    entidad VARCHAR(64) NULL,
    entidad_id BIGINT UNSIGNED NULL,
    detalle JSON NULL,
    PRIMARY KEY (id),
    INDEX idx_eventos_fecha (fecha_evento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP VIEW IF EXISTS vw_citas_detalle;
DROP VIEW IF EXISTS vw_inventario_actual;
DROP VIEW IF EXISTS vw_resumen_pedidos;
DROP VIEW IF EXISTS vw_clientes_fidelizacion;
DROP VIEW IF EXISTS vw_promociones_vigentes;

CREATE VIEW vw_citas_detalle AS
SELECT c.id AS cita_id,c.cliente_id,cli.nombre AS cliente,c.personal_id,
       per.nombre AS personal,c.servicio_id,s.nombre AS servicio,c.fecha,c.hora,
       c.duracion_min,c.estado,c.notas,c.fecha_creacion
FROM citas c
JOIN usuarios cli ON cli.id=c.cliente_id
LEFT JOIN usuarios per ON per.id=c.personal_id
JOIN servicios s ON s.id=c.servicio_id;

CREATE VIEW vw_inventario_actual AS
SELECT p.id,p.nombre,p.descripcion,p.categoria,p.tipo,p.precio,p.stock,p.imagen,p.activo
FROM productos p;

CREATE VIEW vw_resumen_pedidos AS
SELECT p.id,p.usuario_id,p.fecha,p.total,p.estado,p.metodo_pago,
       COUNT(d.id) AS lineas,COALESCE(SUM(d.cantidad),0) AS unidades
FROM pedidos p
LEFT JOIN pedido_detalle d ON d.pedido_id=p.id
GROUP BY p.id,p.usuario_id,p.fecha,p.total,p.estado,p.metodo_pago;

CREATE VIEW vw_clientes_fidelizacion AS
SELECT u.id,u.nombre,u.email,u.telefono,u.puntos,u.activo,
       COUNT(h.id) AS movimientos
FROM usuarios u
LEFT JOIN puntos_historial h ON h.usuario_id=u.id
WHERE u.rol='cliente'
GROUP BY u.id,u.nombre,u.email,u.telefono,u.puntos,u.activo;

CREATE VIEW vw_promociones_vigentes AS
SELECT id,titulo,descripcion,descuento_porcentaje,fecha_inicio,fecha_fin,activa,puntos_costo
FROM promociones
WHERE activa=1 AND CURRENT_DATE BETWEEN fecha_inicio AND fecha_fin;

DROP FUNCTION IF EXISTS fn_total_pedido;
DROP FUNCTION IF EXISTS fn_stock_suficiente;
DROP FUNCTION IF EXISTS fn_saldo_puntos;
DELIMITER $$
CREATE FUNCTION fn_total_pedido(p_pedido_id INT UNSIGNED)
RETURNS DECIMAL(12,2)
NOT DETERMINISTIC READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(12,2);
    SELECT COALESCE(SUM(cantidad*precio_unitario),0) INTO v_total
      FROM pedido_detalle WHERE pedido_id=p_pedido_id;
    RETURN v_total;
END$$

CREATE FUNCTION fn_stock_suficiente(p_producto_id INT UNSIGNED,p_cantidad INT UNSIGNED)
RETURNS TINYINT
NOT DETERMINISTIC READS SQL DATA
BEGIN
    DECLARE v_stock BIGINT;
    SELECT stock INTO v_stock FROM productos WHERE id=p_producto_id AND activo=1;
    RETURN IF(COALESCE(v_stock,0)>=p_cantidad,1,0);
END$$

CREATE FUNCTION fn_saldo_puntos(p_usuario_id INT UNSIGNED)
RETURNS BIGINT UNSIGNED
NOT DETERMINISTIC READS SQL DATA
BEGIN
    DECLARE v_saldo BIGINT UNSIGNED;
    SELECT COALESCE(puntos,0) INTO v_saldo FROM usuarios WHERE id=p_usuario_id;
    RETURN COALESCE(v_saldo,0);
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_registrar_movimiento_inventario;
DROP PROCEDURE IF EXISTS sp_ajustar_puntos;
DROP PROCEDURE IF EXISTS sp_crear_cita;
DROP PROCEDURE IF EXISTS sp_asignar_personal_cita;
DROP PROCEDURE IF EXISTS sp_actualizar_estado_cita;
DROP PROCEDURE IF EXISTS sp_confirmar_pedido;
DROP PROCEDURE IF EXISTS sp_cancelar_pedido;
DELIMITER $$
CREATE PROCEDURE sp_registrar_movimiento_inventario(
    IN p_producto_id INT UNSIGNED, IN p_usuario_id INT UNSIGNED,
    IN p_tipo VARCHAR(10), IN p_cantidad INT UNSIGNED, IN p_motivo VARCHAR(150))
BEGIN
    DECLARE v_stock BIGINT;
    SELECT stock INTO v_stock FROM productos WHERE id=p_producto_id FOR UPDATE;
    IF v_stock IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Producto no encontrado'; END IF;
    IF p_tipo NOT IN ('entrada','salida') OR p_cantidad=0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Movimiento inválido';
    END IF;
    IF p_tipo='salida' AND v_stock<p_cantidad THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Stock insuficiente';
    END IF;
    SET @permitir_cambio_stock=1;
    UPDATE productos SET stock=stock+IF(p_tipo='entrada',p_cantidad,-p_cantidad) WHERE id=p_producto_id;
    SET @permitir_cambio_stock=NULL;
    INSERT INTO movimientos_inventario(producto_id,usuario_id,tipo,cantidad,motivo)
    VALUES(p_producto_id,p_usuario_id,p_tipo,p_cantidad,p_motivo);
END$$

CREATE PROCEDURE sp_ajustar_puntos(
    IN p_usuario_id INT UNSIGNED, IN p_puntos INT, IN p_motivo VARCHAR(150))
BEGIN
    DECLARE v_saldo BIGINT;
    SELECT puntos INTO v_saldo FROM usuarios WHERE id=p_usuario_id FOR UPDATE;
    IF v_saldo IS NULL OR v_saldo+p_puntos<0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Saldo de puntos inválido';
    END IF;
    SET @permitir_cambio_puntos=1;
    UPDATE usuarios SET puntos=puntos+p_puntos WHERE id=p_usuario_id;
    SET @permitir_cambio_puntos=NULL;
    INSERT INTO puntos_historial(usuario_id,puntos,motivo) VALUES(p_usuario_id,p_puntos,p_motivo);
END$$

CREATE PROCEDURE sp_crear_cita(
    IN p_cliente_id INT UNSIGNED,IN p_personal_id INT UNSIGNED,
    IN p_servicio_id INT UNSIGNED,IN p_fecha DATE,IN p_hora TIME,
    IN p_duracion SMALLINT UNSIGNED,IN p_notas VARCHAR(255))
BEGIN
    INSERT INTO citas(cliente_id,personal_id,servicio_id,fecha,hora,duracion_min,notas)
    VALUES(p_cliente_id,p_personal_id,p_servicio_id,p_fecha,p_hora,p_duracion,p_notas);
END$$

CREATE PROCEDURE sp_asignar_personal_cita(IN p_cita_id INT UNSIGNED,IN p_personal_id INT UNSIGNED)
BEGIN
    UPDATE citas SET personal_id=p_personal_id WHERE id=p_cita_id;
END$$

CREATE PROCEDURE sp_actualizar_estado_cita(IN p_cita_id INT UNSIGNED,IN p_estado VARCHAR(20))
BEGIN
    IF p_estado NOT IN ('pendiente','confirmada','completada','cancelada') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Estado inválido';
    END IF;
    UPDATE citas SET estado=p_estado WHERE id=p_cita_id;
END$$

CREATE PROCEDURE sp_confirmar_pedido(IN p_pedido_id INT UNSIGNED)
BEGIN
    UPDATE pedidos SET estado='completado' WHERE id=p_pedido_id;
END$$

CREATE PROCEDURE sp_cancelar_pedido(IN p_pedido_id INT UNSIGNED)
BEGIN
    UPDATE pedidos SET estado='cancelado' WHERE id=p_pedido_id;
END$$
DELIMITER ;

-- Triggers de control e inmutabilidad (14).
DROP TRIGGER IF EXISTS trg_usuarios_bu_control_puntos;
DROP TRIGGER IF EXISTS trg_productos_bu_control_stock;
DROP TRIGGER IF EXISTS trg_disponibilidades_bi_validar;
DROP TRIGGER IF EXISTS trg_disponibilidades_bu_validar;
DROP TRIGGER IF EXISTS trg_citas_bi_validar;
DROP TRIGGER IF EXISTS trg_citas_bu_validar;
DROP TRIGGER IF EXISTS trg_auditoria_cambios_bu_bloquear;
DROP TRIGGER IF EXISTS trg_auditoria_cambios_bd_bloquear;
DROP TRIGGER IF EXISTS trg_auditoria_eventos_bu_bloquear;
DROP TRIGGER IF EXISTS trg_auditoria_eventos_bd_bloquear;
DROP TRIGGER IF EXISTS trg_puntos_historial_bu_bloquear;
DROP TRIGGER IF EXISTS trg_puntos_historial_bd_bloquear;
DROP TRIGGER IF EXISTS trg_movimientos_inventario_bu_bloquear;
DROP TRIGGER IF EXISTS trg_movimientos_inventario_bd_bloquear;
DELIMITER $$
CREATE TRIGGER trg_usuarios_bu_control_puntos BEFORE UPDATE ON usuarios FOR EACH ROW
BEGIN
    IF NEW.puntos<>OLD.puntos AND COALESCE(@permitir_cambio_puntos,0)<>1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Cambio directo de puntos no permitido';
    END IF;
END$$
CREATE TRIGGER trg_productos_bu_control_stock BEFORE UPDATE ON productos FOR EACH ROW
BEGIN
    IF NEW.stock<>OLD.stock AND COALESCE(@permitir_cambio_stock,0)<>1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Cambio directo de stock no permitido';
    END IF;
END$$
CREATE TRIGGER trg_disponibilidades_bi_validar BEFORE INSERT ON disponibilidades FOR EACH ROW
BEGIN
    IF NEW.hora_fin<=NEW.hora_inicio THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Bloque horario inválido'; END IF;
    IF (SELECT COUNT(*) FROM usuarios WHERE id=NEW.personal_id AND rol='personal' AND activo=1)=0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Personal no disponible';
    END IF;
END$$
CREATE TRIGGER trg_disponibilidades_bu_validar BEFORE UPDATE ON disponibilidades FOR EACH ROW
BEGIN
    IF NEW.hora_fin<=NEW.hora_inicio THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Bloque horario inválido'; END IF;
    IF (SELECT COUNT(*) FROM usuarios WHERE id=NEW.personal_id AND rol='personal')=0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Usuario sin rol personal';
    END IF;
END$$
CREATE TRIGGER trg_citas_bi_validar BEFORE INSERT ON citas FOR EACH ROW
BEGIN
    IF NEW.duracion_min=0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Duración inválida'; END IF;
    IF (SELECT COUNT(*) FROM usuarios WHERE id=NEW.cliente_id AND rol='cliente' AND activo=1)=0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Cliente no disponible';
    END IF;
    IF NEW.personal_id IS NOT NULL AND
       (SELECT COUNT(*) FROM usuarios WHERE id=NEW.personal_id AND rol='personal' AND activo=1)=0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Personal no disponible';
    END IF;
END$$
CREATE TRIGGER trg_citas_bu_validar BEFORE UPDATE ON citas FOR EACH ROW
BEGIN
    IF NEW.duracion_min=0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Duración inválida'; END IF;
END$$
CREATE TRIGGER trg_auditoria_cambios_bu_bloquear BEFORE UPDATE ON auditoria_cambios FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Auditoría inmutable'; END$$
CREATE TRIGGER trg_auditoria_cambios_bd_bloquear BEFORE DELETE ON auditoria_cambios FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Auditoría inmutable'; END$$
CREATE TRIGGER trg_auditoria_eventos_bu_bloquear BEFORE UPDATE ON auditoria_eventos FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Auditoría inmutable'; END$$
CREATE TRIGGER trg_auditoria_eventos_bd_bloquear BEFORE DELETE ON auditoria_eventos FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Auditoría inmutable'; END$$
CREATE TRIGGER trg_puntos_historial_bu_bloquear BEFORE UPDATE ON puntos_historial FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Historial de puntos inmutable'; END$$
CREATE TRIGGER trg_puntos_historial_bd_bloquear BEFORE DELETE ON puntos_historial FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Historial de puntos inmutable'; END$$
CREATE TRIGGER trg_movimientos_inventario_bu_bloquear BEFORE UPDATE ON movimientos_inventario FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Historial de inventario inmutable'; END$$
CREATE TRIGGER trg_movimientos_inventario_bd_bloquear BEFORE DELETE ON movimientos_inventario FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Historial de inventario inmutable'; END$$
DELIMITER ;

-- Triggers de auditoría (26). Total esperado: 40 triggers.
DROP TRIGGER IF EXISTS trg_aud_usuarios_ai;
DROP TRIGGER IF EXISTS trg_aud_usuarios_au;
DROP TRIGGER IF EXISTS trg_aud_usuarios_ad;
DROP TRIGGER IF EXISTS trg_aud_servicios_ai;
DROP TRIGGER IF EXISTS trg_aud_servicios_au;
DROP TRIGGER IF EXISTS trg_aud_servicios_ad;
DROP TRIGGER IF EXISTS trg_aud_disponibilidades_ai;
DROP TRIGGER IF EXISTS trg_aud_disponibilidades_au;
DROP TRIGGER IF EXISTS trg_aud_disponibilidades_ad;
DROP TRIGGER IF EXISTS trg_aud_citas_ai;
DROP TRIGGER IF EXISTS trg_aud_citas_au;
DROP TRIGGER IF EXISTS trg_aud_citas_ad;
DROP TRIGGER IF EXISTS trg_aud_productos_ai;
DROP TRIGGER IF EXISTS trg_aud_productos_au;
DROP TRIGGER IF EXISTS trg_aud_productos_ad;
DROP TRIGGER IF EXISTS trg_aud_pedidos_ai;
DROP TRIGGER IF EXISTS trg_aud_pedidos_au;
DROP TRIGGER IF EXISTS trg_aud_pedidos_ad;
DROP TRIGGER IF EXISTS trg_aud_pedido_detalle_ai;
DROP TRIGGER IF EXISTS trg_aud_pedido_detalle_au;
DROP TRIGGER IF EXISTS trg_aud_pedido_detalle_ad;
DROP TRIGGER IF EXISTS trg_aud_promociones_ai;
DROP TRIGGER IF EXISTS trg_aud_promociones_au;
DROP TRIGGER IF EXISTS trg_aud_promociones_ad;
DROP TRIGGER IF EXISTS trg_aud_puntos_historial_ai;
DROP TRIGGER IF EXISTS trg_aud_movimientos_inventario_ai;
DELIMITER $$
CREATE TRIGGER trg_aud_usuarios_ai AFTER INSERT ON usuarios FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'usuarios',NEW.id,'INSERT',JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_usuarios_au AFTER UPDATE ON usuarios FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'usuarios',NEW.id,'UPDATE',JSON_OBJECT('id',OLD.id),JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_usuarios_ad AFTER DELETE ON usuarios FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'usuarios',OLD.id,'DELETE',JSON_OBJECT('id',OLD.id)); END$$

CREATE TRIGGER trg_aud_servicios_ai AFTER INSERT ON servicios FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'servicios',NEW.id,'INSERT',JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_servicios_au AFTER UPDATE ON servicios FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'servicios',NEW.id,'UPDATE',JSON_OBJECT('id',OLD.id),JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_servicios_ad AFTER DELETE ON servicios FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'servicios',OLD.id,'DELETE',JSON_OBJECT('id',OLD.id)); END$$

CREATE TRIGGER trg_aud_disponibilidades_ai AFTER INSERT ON disponibilidades FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'disponibilidades',NEW.id,'INSERT',JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_disponibilidades_au AFTER UPDATE ON disponibilidades FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'disponibilidades',NEW.id,'UPDATE',JSON_OBJECT('id',OLD.id),JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_disponibilidades_ad AFTER DELETE ON disponibilidades FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'disponibilidades',OLD.id,'DELETE',JSON_OBJECT('id',OLD.id)); END$$

CREATE TRIGGER trg_aud_citas_ai AFTER INSERT ON citas FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'citas',NEW.id,'INSERT',JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_citas_au AFTER UPDATE ON citas FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'citas',NEW.id,'UPDATE',JSON_OBJECT('id',OLD.id),JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_citas_ad AFTER DELETE ON citas FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'citas',OLD.id,'DELETE',JSON_OBJECT('id',OLD.id)); END$$

CREATE TRIGGER trg_aud_productos_ai AFTER INSERT ON productos FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'productos',NEW.id,'INSERT',JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_productos_au AFTER UPDATE ON productos FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'productos',NEW.id,'UPDATE',JSON_OBJECT('id',OLD.id),JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_productos_ad AFTER DELETE ON productos FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'productos',OLD.id,'DELETE',JSON_OBJECT('id',OLD.id)); END$$

CREATE TRIGGER trg_aud_pedidos_ai AFTER INSERT ON pedidos FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'pedidos',NEW.id,'INSERT',JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_pedidos_au AFTER UPDATE ON pedidos FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'pedidos',NEW.id,'UPDATE',JSON_OBJECT('id',OLD.id),JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_pedidos_ad AFTER DELETE ON pedidos FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'pedidos',OLD.id,'DELETE',JSON_OBJECT('id',OLD.id)); END$$

CREATE TRIGGER trg_aud_pedido_detalle_ai AFTER INSERT ON pedido_detalle FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'pedido_detalle',NEW.id,'INSERT',JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_pedido_detalle_au AFTER UPDATE ON pedido_detalle FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'pedido_detalle',NEW.id,'UPDATE',JSON_OBJECT('id',OLD.id),JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_pedido_detalle_ad AFTER DELETE ON pedido_detalle FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'pedido_detalle',OLD.id,'DELETE',JSON_OBJECT('id',OLD.id)); END$$

CREATE TRIGGER trg_aud_promociones_ai AFTER INSERT ON promociones FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'promociones',NEW.id,'INSERT',JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_promociones_au AFTER UPDATE ON promociones FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'promociones',NEW.id,'UPDATE',JSON_OBJECT('id',OLD.id),JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_promociones_ad AFTER DELETE ON promociones FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_anteriores) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'promociones',OLD.id,'DELETE',JSON_OBJECT('id',OLD.id)); END$$

CREATE TRIGGER trg_aud_puntos_historial_ai AFTER INSERT ON puntos_historial FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'puntos_historial',NEW.id,'INSERT',JSON_OBJECT('id',NEW.id)); END$$
CREATE TRIGGER trg_aud_movimientos_inventario_ai AFTER INSERT ON movimientos_inventario FOR EACH ROW
BEGIN INSERT INTO auditoria_cambios(usuario_bd,usuario_app_id,ip_app,correlacion_id,tabla,registro_id,operacion,datos_nuevos) VALUES(USER(),@app_usuario_id,@app_ip,@app_correlacion_id,'movimientos_inventario',NEW.id,'INSERT',JSON_OBJECT('id',NEW.id)); END$$
DELIMITER ;
