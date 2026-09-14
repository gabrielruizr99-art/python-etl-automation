# Configuración de la Base de Datos

Este documento explica cómo configurar el entorno y la base de datos PostgreSQL de manera segura e idempotente.

## 1. Creación segura de `.env`
El proyecto requiere un archivo `.env` en la raíz del repositorio para almacenar de forma segura las credenciales de conexión. **Este archivo nunca se publica ni se añade a Git** para evitar la filtración de secretos.
Copia el archivo `.env.example` como `.env` e ingresa tus valores locales:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=etl_automation
DB_USER=postgres
DB_PASSWORD=tu_password_aqui
DB_ADMIN_DB=postgres
```
*Nota:* Las credenciales están protegidas dentro de la aplicación mediante `SecretStr` de `pydantic-settings` y jamás serán emitidas por logs o mensajes de error.

## 2. Ejecución del script de configuración
Para crear la base de datos y construir las tablas iniciales, ejecuta el script de configuración:
```bash
.venv\Scripts\python.exe scripts\setup_database.py
```
**Naturaleza Idempotente:** Este script es completamente idempotente. Primero se conecta a la base de datos administrativa (`DB_ADMIN_DB`) para crear la base de datos objetivo si esta no existe (sin eliminarla ni recrearla en ejecuciones subsecuentes). Luego, se conecta a la nueva base y ejecuta el script de inicialización SQL (`sql/001_initial_schema.sql`), el cual está diseñado con comandos `IF NOT EXISTS` para que puedas correr el script múltiples veces sin causar errores ni pérdida de datos.

## 3. Propósito de cada esquema
El diseño de la base de datos separa conceptualmente el estado operativo del resultado analítico.

### Esquema `etl`
Este esquema actúa como el "cuarto de máquinas" del flujo de datos, documentando todo lo que sucede:
- `etl.pipeline_runs`: Registra el inicio, fin y métricas resumidas de cada ejecución completa del proceso.
- `etl.file_registry`: Lleva un inventario de cada archivo ingerido utilizando un hash criptográfico para garantizar **idempotencia** a nivel de archivo (evitando re-procesar los mismos archivos).
- `etl.rejected_records`: Almacena filas anómalas o inválidas separándolas por motivos específicos (`reason_code`), permitiendo auditoría y reparación posterior sin detener la carga útil.

### Esquema `warehouse`
Este esquema expone la información final limpia y estructurada.
- `warehouse.sales`: Es la tabla central de hechos analíticos donde reside toda la data validada e ingestada. Cuenta con restricciones (`CHECK`) fuertes e índices estratégicos para garantizar la calidad final de los reportes.

## 4. Ejecución del Descubrimiento de Archivos
La primera etapa operativa del ETL es descubrir qué archivos CSV nuevos existen en `data/incoming/`. Ejecuta:
```bash
.venv\Scripts\python.exe scripts\discover_files.py
```

### Idempotencia en Acción
El proceso de descubrimiento está diseñado para ser seguro e idempotente. 
- **Primera ejecución:** Registra todos los archivos nuevos en la tabla `etl.file_registry` con estado "discovered". Si encuentra algún archivo duplicado (archivos con el mismo contenido exacto y, por lo tanto, el mismo hash SHA-256), lo registrará como duplicado y no lo insertará de nuevo, sin lanzar excepciones gracias al mecanismo `ON CONFLICT DO NOTHING`.
- **Segunda ejecución:** Si no has agregado nuevos archivos a la carpeta, el script los analizará, calculará sus hashes y determinará que todos ya existen, resultando en 0 archivos nuevos y todos duplicados. Esto previene dobles cargas y mantiene la integridad del sistema.
El hash `SHA-256` se calcula leyendo el archivo por bloques para optimizar memoria, y se detectan modificaciones de archivos en tiempo de ejecución.

## 5. Ejecución de la Validación (Validation)
Una vez descubiertos los archivos, estos deben ser validados:
```bash
.venv\Scripts\python.exe scripts\validate_files.py
```
Esta etapa comprueba la integridad del esquema (encabezados correctos) y el contenido de las filas (reglas de negocio como límites en precios y catálogos válidos). Los registros inválidos son separados en `etl.rejected_records` con motivos codificados en `reason_code` sin bloquear la carga útil. Una segunda corrida ignorará los archivos que ya se encuentren en estado distinto a "discovered".
