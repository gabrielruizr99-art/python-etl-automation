# Data Contract: Sales Data

Este documento define el esquema, las reglas de validación y el tratamiento de errores para los archivos de ventas entrantes (`sales_*.csv`) de la distribuidora minorista.

## Esquema de Archivos CSV de Entrada

Cada fila representa una línea de venta. Las columnas `source_file` y `ingestion_timestamp` **no** deben estar presentes en el archivo CSV; el proceso ETL se encargará de añadirlas durante la ingestión.

| Columna | Tipo | Obligatorio | Reglas de Validación | Ejemplo Válido | Tratamiento si es Inválido |
|---------|------|-------------|----------------------|----------------|----------------------------|
| `sale_id` | String | Sí | Identificador único. | `a1b2c3d4-e5f6-7890-1234-56789abcdef0` | Rechazo de fila |
| `sale_date` | Date | Sí | Formato `YYYY-MM-DD`. Fecha válida. | `2026-04-15` | Rechazo de fila |
| `sale_time` | Time | Sí | Formato `HH:MM:SS`. Hora válida. | `14:30:00` | Rechazo de fila |
| `branch_id` | String | Sí | Identificador de sucursal válido. | `BR-001` | Rechazo de fila |
| `customer_id` | String | Sí | Identificador de cliente. | `C-0500` | Rechazo de fila |
| `product_id` | String | Sí | Identificador de producto. | `P-0080` | Rechazo de fila |
| `seller_id` | String | Sí | Identificador del vendedor. | `S-0018` | Rechazo de fila |
| `sales_channel` | String | Sí | Valores permitidos: `Store`, `Web`, `Phone`. | `Store` | Rechazo de fila |
| `payment_method` | String | Sí | Valores: `Cash`, `Card`, `Transfer`, `DigitalWallet`. | `Card` | Rechazo de fila |
| `quantity` | Integer | Sí | Número entero > 0. | `3` | Rechazo de fila |
| `unit_price` | Decimal | Sí | Número decimal > 0.0, punto como separador. | `25.50` | Rechazo de fila |
| `discount_pct` | Decimal | Sí | Número decimal entre 0.0 y 0.30. | `0.15` | Rechazo de fila |

## Campos Agregados por el ETL
| Columna | Tipo | Origen | Descripción |
|---------|------|--------|-------------|
| `source_file` | String | ETL | Nombre del archivo original procesado. |
| `ingestion_timestamp` | Timestamp | ETL | Marca de tiempo de cuándo se procesó el registro. |

## Claves de Idempotencia y Deduplicación

1. **A nivel de registro:** `sale_id` es la **clave de negocio principal**. Si el ETL encuentra un `sale_id` que ya existe en la base de datos (y pertenece a la misma venta exitosa), se omitirá su inserción para evitar duplicación.
2. **A nivel de archivo:** El ETL calculará un **hash MD5 o SHA-256** del archivo entrante. Si el hash ya ha sido procesado anteriormente con éxito, se considerará un archivo repetido y se registrará en los logs saltando su procesamiento general.
