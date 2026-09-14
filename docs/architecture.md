# ETL Architecture

Esta documentación detalla la arquitectura de nuestro pipeline ETL, diseñado para cargar de manera segura e idempotente las ventas diarias hacia PostgreSQL.

## Límites del Sistema

El pipeline se encuentra delimitado a la validación, transformación financiera y carga de archivos CSV de ventas. La integración visual mediante herramientas como Power BI está contemplada para el consumo del esquema `warehouse`, pero no forma parte de este servicio automatizado.

## Flujo Completo

1. **Descubrimiento (Discovery):** Identifica archivos `.csv` en `data/incoming`. Calcula un SHA-256 por archivo para garantizar la idempotencia.
2. **Validación:** Analiza tanto la estructura del archivo como el tipo de datos en cada fila (usando `pydantic`). Las filas inválidas se derivan a la tabla de auditoría, mientras que las filas válidas continúan el proceso.
3. **Transformación:** Las filas válidas son sometidas a cálculos financieros (Gross Amount, Discount Amount, Net Amount) con exactitud decimal, usando estrategias de redondeo bancario (HALF_UP).
4. **Carga Transaccional:** Se introducen los registros limpios en `warehouse.sales`. El archivo físico se mueve a la bóveda correspondiente (`processed` o `rejected`) y su estado definitivo se registra.

## Esquemas PostgreSQL

El proyecto aísla la responsabilidad en dos esquemas de base de datos separados:

- **`etl`**: Contiene la infraestructura de control del sistema (`pipeline_runs`, `file_registry`, `rejected_records`). Maneja el estado, auditoría y bloqueos de ejecución.
- **`warehouse`**: Diseñado para el consumo final analítico. Contiene la tabla transaccional limpia y calculada `sales`.

## Estados de Archivos

Los archivos circulan a través de diferentes estados, garantizando total trazabilidad:
- `discovered`: Detectado por primera vez; SHA-256 generado.
- `processing`: El archivo ha iniciado su validación.
- `validated`: Validaciones de esquema completadas; filas aptas.
- `processed`: Procesamiento completado exitosamente; movido a `data/processed`.
- `rejected`: Procesamiento abortado debido a un esquema no conforme; movido a `data/rejected`.
- `failed`: Fallo inesperado o catastrófico del sistema durante el procesamiento del archivo.

## Transacciones, Compensación e Idempotencia

### Idempotencia por Archivo y Venta
El identificador criptográfico **SHA-256** generado durante la fase de Descubrimiento evita la duplicidad por archivo. A su vez, una restricción `ON CONFLICT DO NOTHING` en la tabla `warehouse.sales` previene la inserción de ventas duplicadas a nivel de fila mediante el `sale_id`.

### Transacciones
Cada archivo se carga dentro de una transacción exclusiva `READ COMMITTED`. La tabla temporal `staging_sales` se instancia mediante `ON COMMIT DROP`, de manera que los datos staging existen única y exclusivamente durante el scope de su transacción correspondiente.

### Sistema de Compensación
Si surge un error al intentar mover los archivos físicos post-inserción hacia el archivo procesado (`os.replace`), la transacción en PostgreSQL se somete a **ROLLBACK**. Esto mantiene al File System en estricta paridad y congruencia con el registro de PostgreSQL.

## Control de Concurrencia (Advisory Lock)

Con el propósito de evitar colisiones catastróficas entre múltiples ejecuciones programadas, el sistema adquiere un candado consultivo a nivel de sesión en PostgreSQL (`pg_try_advisory_lock` usando la llave fija `100200300`). Si el lock ya está siendo poseído por otra instancia, el sistema de CI/CD abortará la ejecución limpiamente (Exit Code 3).

## Modos de Ejecución

1. **Ejecución Local:** Pruebas controladas y debugging manual ejecutando directamente los módulos en Python.
2. **Scheduled Task:** Tarea del programador de Windows (Task Scheduler), gestionada mediante los envoltorios PowerShell.
3. **CI (Integración Continua):** Pruebas integrales de flujo en GitHub Actions, corriendo infraestructura efímera en `ubuntu-latest`.
