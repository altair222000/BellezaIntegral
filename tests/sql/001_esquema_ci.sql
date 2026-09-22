-- Esquema aislado para CI/pruebas de Belleza Integral (MySQL 8+).
-- No crea ni selecciona bases de datos: el workflow crea belleza_integral_test.

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NULL,
    telefono VARCHAR(20) NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('administrador','personal','cliente') NOT NULL DEFAULT 'cliente',
    puntos INT UNSIGNED NOT NULL DEFAULT 0,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_usuarios_email (email),
    UNIQUE KEY uk_usuarios_telefono (telefono),
    CONSTRAINT chk_usuarios_contacto CHECK (email IS NOT NULL OR telefono IS NOT NULL),
    CONSTRAINT chk_usuarios_activo CHECK (activo IN (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS servicios (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT NULL,
    categoria VARCHAR(50) NOT NULL,
    duracion_min SMALLINT UNSIGNED NOT NULL,
    precio DECIMAL(10,2) NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    imagen VARCHAR(255) NULL,
    PRIMARY KEY (id),
    CONSTRAINT chk_servicios_duracion CHECK (duracion_min > 0),
    CONSTRAINT chk_servicios_precio CHECK (precio >= 0),
    CONSTRAINT chk_servicios_activo CHECK (activo IN (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS disponibilidades (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    personal_id INT UNSIGNED NOT NULL,
    dia_semana TINYINT UNSIGNED NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    CONSTRAINT fk_disponibilidades_personal FOREIGN KEY (personal_id) REFERENCES usuarios(id),
    CONSTRAINT chk_disponibilidades_dia CHECK (dia_semana BETWEEN 1 AND 7),
    CONSTRAINT chk_disponibilidades_horas CHECK (hora_fin > hora_inicio),
    CONSTRAINT chk_disponibilidades_activo CHECK (activo IN (0,1)),
    UNIQUE KEY uk_disponibilidad_bloque (personal_id,dia_semana,hora_inicio,hora_fin)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS citas (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    cliente_id INT UNSIGNED NOT NULL,
    personal_id INT UNSIGNED NULL,
    servicio_id INT UNSIGNED NOT NULL,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    duracion_min SMALLINT UNSIGNED NOT NULL,
    estado ENUM('pendiente','confirmada','completada','cancelada') NOT NULL DEFAULT 'pendiente',
    notas VARCHAR(255) NULL,
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_citas_cliente FOREIGN KEY (cliente_id) REFERENCES usuarios(id),
    CONSTRAINT fk_citas_personal FOREIGN KEY (personal_id) REFERENCES usuarios(id),
    CONSTRAINT fk_citas_servicio FOREIGN KEY (servicio_id) REFERENCES servicios(id),
    CONSTRAINT chk_citas_duracion CHECK (duracion_min > 0),
    INDEX idx_citas_personal_fecha_hora (personal_id,fecha,hora),
    INDEX idx_citas_cliente_fecha (cliente_id,fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS productos (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT NULL,
    categoria VARCHAR(50) NOT NULL,
    tipo ENUM('venta','insumo') NOT NULL,
    precio DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    stock INT UNSIGNED NOT NULL DEFAULT 0,
    imagen VARCHAR(255) NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    CONSTRAINT chk_productos_precio CHECK (precio >= 0),
    CONSTRAINT chk_productos_activo CHECK (activo IN (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pedidos (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id INT UNSIGNED NOT NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10,2) NOT NULL,
    estado ENUM('completado','cancelado') NOT NULL DEFAULT 'completado',
    nombre_entrega VARCHAR(100) NOT NULL,
    telefono_entrega VARCHAR(20) NOT NULL,
    direccion_entrega VARCHAR(255) NOT NULL,
    metodo_pago VARCHAR(50) NOT NULL,
    tarjeta_ultimos4 VARCHAR(4) NULL,
    clave_operacion VARCHAR(120) NOT NULL,
    solicitud_hash CHAR(64) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_pedidos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT chk_pedidos_total CHECK (total >= 0),
    UNIQUE KEY uk_pedidos_operacion (usuario_id,clave_operacion),
    INDEX idx_pedidos_usuario_fecha (usuario_id,fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pedido_detalle (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    pedido_id INT UNSIGNED NOT NULL,
    producto_id INT UNSIGNED NOT NULL,
    cantidad INT UNSIGNED NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_detalle_pedido FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_producto FOREIGN KEY (producto_id) REFERENCES productos(id),
    CONSTRAINT chk_detalle_cantidad CHECK (cantidad > 0),
    CONSTRAINT chk_detalle_precio CHECK (precio_unitario >= 0),
    INDEX idx_detalle_pedido (pedido_id),
    INDEX idx_detalle_producto (producto_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS promociones (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    titulo VARCHAR(120) NOT NULL,
    descripcion VARCHAR(255) NULL,
    descuento_porcentaje TINYINT UNSIGNED NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    activa TINYINT(1) NOT NULL DEFAULT 1,
    puntos_costo INT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    CONSTRAINT chk_promociones_descuento CHECK (descuento_porcentaje BETWEEN 0 AND 100),
    CONSTRAINT chk_promociones_fechas CHECK (fecha_fin >= fecha_inicio),
    CONSTRAINT chk_promociones_activa CHECK (activa IN (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS puntos_historial (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id INT UNSIGNED NOT NULL,
    puntos INT NOT NULL,
    motivo VARCHAR(150) NOT NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cita_id INT UNSIGNED NULL,
    promocion_id INT UNSIGNED NULL,
    clave_operacion VARCHAR(120) NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_puntos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_puntos_cita FOREIGN KEY (cita_id) REFERENCES citas(id),
    CONSTRAINT fk_puntos_promocion FOREIGN KEY (promocion_id) REFERENCES promociones(id),
    UNIQUE KEY uk_puntos_cita (cita_id),
    UNIQUE KEY uk_puntos_operacion (usuario_id,clave_operacion),
    INDEX idx_puntos_usuario_fecha (usuario_id,fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    producto_id INT UNSIGNED NOT NULL,
    usuario_id INT UNSIGNED NOT NULL,
    tipo ENUM('entrada','salida') NOT NULL,
    cantidad INT UNSIGNED NOT NULL,
    motivo VARCHAR(150) NOT NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_mov_producto FOREIGN KEY (producto_id) REFERENCES productos(id),
    CONSTRAINT fk_mov_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT chk_mov_cantidad CHECK (cantidad > 0),
    INDEX idx_mov_producto_fecha (producto_id,fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tokens_revocados (
    jti VARCHAR(64) NOT NULL,
    expira DATETIME NOT NULL,
    PRIMARY KEY (jti),
    INDEX idx_tokens_expira (expira)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sesiones_usuario (
    usuario_id INT UNSIGNED NOT NULL,
    version INT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (usuario_id),
    CONSTRAINT fk_sesiones_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
