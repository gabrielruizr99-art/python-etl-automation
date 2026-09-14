# Changelog

## [1.0.0] - 2026-09-14

### Added
- **Generación de Datos:** Script sintético automatizado para la creación de escenarios complejos (CSV válidos, registros inválidos y esquemas corruptos).
- **Esquema PostgreSQL:** Estructura dual de bases de datos separando la capa analítica (`warehouse`) de la infraestructura de auditoría y control (`etl`).
- **Descubrimiento (Discovery):** Escaneo de directorios con encriptado y cálculo de hashes criptográficos (SHA-256) sobre cada archivo.
- **Validación:** Comprobación rigurosa a nivel de fila empleando Pydantic. Redireccionamiento de errores a `etl.rejected_records`.
- **Carga (Load) Transaccional:** Cálculos financieros mediante `Decimal` (half-up) e inserción hacia el Data Warehouse a través de tablas temporales staging e instrucciones `COPY`.
- **Idempotencia:** Protección robusta de duplicados mediante control combinado del hash a nivel de archivo y llaves primarias en PostgreSQL para registros de venta.
- **Automatización:** Candados a nivel de conexión (Advisory Locks) en PostgreSQL e infraestructura completa de scripts envoltorios para Task Scheduler en PowerShell.
- **Pruebas y CI:** Cobertura exhaustiva compuesta por 29 tests unitarios/integración en Pytest e integración continua vía GitHub Actions (validación de linting y aserciones de estado post-ejecución).
