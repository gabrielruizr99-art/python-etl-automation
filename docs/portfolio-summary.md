# Portfolio Summary

## GitHub Summary (Short)
Automated ETL pipeline in Python with robust PostgreSQL transactional loading, cryptographic idempotency (SHA-256), and Pydantic validation. Enforces strict schema validations and data integrity for sales records. Includes automated testing and CI workflows.

## LinkedIn Description
🚀 **Automated Financial ETL Pipeline**

I developed an enterprise-grade ETL pipeline designed to automate the discovery, validation, and loading of decentralized CSV sales records into a PostgreSQL Data Warehouse. 

Instead of traditional fragile script automation, this system guarantees 100% data integrity through cryptographic idempotency (SHA-256) and strict ACID transactional guarantees. If an operation fails mid-way, the entire process is rolled back, preventing orphaned data or partial states.

**Key Achievements:**
- Detected and bypassed duplicated files dynamically using cryptographic hashing.
- Successfully loaded and transformed over 12,000 valid sales with zero missing rows or duplicates.
- Integrated `pg_advisory_lock` for secure concurrency control.
- Designed comprehensive CI/CD quality gates with GitHub Actions (100% Pytest pass rate, 0 Ruff warnings).

## Workana Description
**Enterprise ETL Pipeline (Python + PostgreSQL)**

Do you need to consolidate messy Excel or CSV data into a clean, analytical database without losing your mind over duplicate rows or invalid data types?

I have built a fully automated ETL (Extract, Transform, Load) system that solves exactly this problem. This pipeline constantly monitors directories for new sales files, validates structure and business rules natively via Python (Pydantic), and inserts clean financial calculations into a PostgreSQL Warehouse using high-speed `COPY` commands.

If you are looking for an engineer that treats data engineering as software engineering—implementing automated testing, deployment wrappers, and continuous integration—I can scale this pattern to fit your operational needs.

## Tres Puntos de Valor Empresarial
1. **Erradicación de Pérdidas por Duplicidad:** El sistema identifica duplicados silenciosos a nivel de archivo (SHA-256) y a nivel de transacción comercial (`ON CONFLICT`), evitando inflación artificial de KPIs de ventas.
2. **Consistencia Transaccional:** La paridad entre la base de datos y los archivos (compensación y rollback) elimina la necesidad de intervenciones manuales por limpiezas a medias ante errores de infraestructura.
3. **Escalabilidad y Seguridad:** Diseñado en torno al principio de confianza cero, cada inserción se documenta con la traza de su archivo original y se valida cada regla de negocio, garantizando un Data Warehouse siempre analizable.

## Tecnologías
- Python 3.13
- PostgreSQL 18.6
- Pydantic & Pydantic-Settings
- Psycopg 3
- Pytest (29 automated tests)
- Ruff (Strict linting)
- GitHub Actions (CI)
- PowerShell (Wrappers)

## Resultados Verificables
- 34 archivos procesados (CSV).
- 12,001 ventas válidas cargadas al Data Warehouse.
- 11 filas físicamente rechazadas por inconsistencias en los datos.
- 1 archivo rechazado totalmente por esquema inválido.
- 0 ventas duplicadas (`sale_id` constraints y SHA-256).
- 100% cobertura de pruebas automatizadas aprobadas.
