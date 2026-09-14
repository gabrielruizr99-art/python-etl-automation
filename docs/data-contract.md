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

1. **A nivel de registro:** `sale_id` es la **clave de negocio principal**. Si el ETL encuentra un `sale_id` duplicado en el mismo archivo, en el lote o que ya exista en la base de datos, lo marcará con el código `DUPLICATE_SALE_ID`.
2. **A nivel de archivo:** El ETL calcula un hash SHA-256 leyendo por bloques.

## Reglas de Carga Transaccional (Fase 6)
- **Transformación Financiera**: Durante la carga, los montos financieros se calculan con base en `quantity` y `unit_price`, aplicando descuentos. Todo se calcula internamente usando el tipo `Decimal` y la política `ROUND_HALF_UP` a 2 decimales para precisión contable. No se usan números de punto flotante en las operaciones.
- **Idempotencia en Base de Datos**: La tabla `warehouse.sales` implementa la restricción `ON CONFLICT (sale_id) DO NOTHING`. Cualquier venta con un `sale_id` que ya existe es omitida silenciosamente a nivel motor, garantizando una ingesta libre de duplicados reales.
- **Manejo de Tabla Temporal (`staging_sales`)**: Cada archivo se carga completo usando la veloz instrucción `COPY` de PostgreSQL hacia una tabla temporal. Una vez llenada, un `INSERT` masivo cruza los datos con la tabla principal. La tabla temporal se desecha automáticamente (`ON COMMIT DROP`).
- **Trazabilidad**: En la tabla final se agregan las columnas `source_file` y `source_hash` para conocer el origen exacto de cada transacción. La fecha de ingesta (`ingested_at`) es gestionada por PostgreSQL.

## Estados de Archivo y Tratamiento de Rechazos
Durante la fase de validación, los archivos descubiertos transitan entre los siguientes estados:
- **`discovered`**: Recién detectado.
- **`processing`**: En proceso de validación.
- **`validated`**: Validado (pudiendo tener todas sus filas correctas, o algunas rechazadas).
- **`rejected`**: Rechazado íntegramente por esquema inválido o archivo vacío sin encabezados.
- **`failed`**: Error técnico impredecible (aislado de los datos).

### Tratamiento de Registros Rechazados
Toda fila inválida es desviada a la tabla `etl.rejected_records`. Cada registro produce una sola entrada de rechazo en base de datos conteniendo todos los `rejection_codes` agrupados, manteniendo en formato `JSONB` seguro la información original, garantizando la trazabilidad sin bloquear la carga de datos correctos del lote.
