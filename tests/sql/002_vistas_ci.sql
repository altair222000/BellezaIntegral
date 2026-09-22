-- Vistas mínimas requeridas por los endpoints usados en CI.
-- El entorno de pruebas es desechable y se crea desde cero en cada ejecución.

CREATE OR REPLACE VIEW vw_promociones_vigentes AS
SELECT
    id,
    titulo,
    descripcion,
    descuento_porcentaje,
    fecha_inicio,
    fecha_fin,
    activa,
    puntos_costo
FROM promociones
WHERE activa = 1
  AND CURRENT_DATE BETWEEN fecha_inicio AND fecha_fin;
