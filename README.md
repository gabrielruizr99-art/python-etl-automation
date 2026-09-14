# Python ETL Automation

## Objetivo
Este proyecto forma parte de un portafolio profesional de automatización, análisis de datos y Business Intelligence. Su objetivo es construir una canalización ETL automatizada que procese archivos CSV de ventas, limpiando, validando y cargando los datos de forma segura e idempotente.

## Problema que resuelve
Las empresas suelen recibir datos de ventas crudos en archivos CSV que contienen errores, valores nulos o duplicados. Este sistema automatiza la ingesta, asegurando la calidad de los datos antes de introducirlos en la base de datos principal y aislando los registros problemáticos.

## Arquitectura prevista
1. **Extracción**: Detección de nuevos archivos CSV en el directorio `data/incoming`.
2. **Validación y Transformación**: Uso de pandas y pydantic para asegurar que la estructura y los tipos de datos sean correctos. Limpieza y normalización de la información.
3. **Carga**: Inserción de los registros válidos en una base de datos PostgreSQL usando psycopg3, garantizando que el proceso sea idempotente.
4. **Manejo de rechazos**: Los registros inválidos o duplicados se aíslan en la carpeta `data/rejected` junto a su motivo.
5. **Histórico y Logs**: Los archivos procesados se mueven a un archivo histórico, y se genera un registro detallado de las ejecuciones.

## Dataset Sintético
Los datos utilizados son ficticios y son generados automáticamente para asegurar la reproducibilidad del proyecto mediante una semilla determinista.

- **Volumen Generado:** Se producen datos de ventas correspondientes a abril de 2026. Hay 30 archivos diarios normales, conteniendo cada uno exactamente 400 filas. El total normal esperado es de 12,000 registros.
- **Comando de generación:**
  ```bash
  .venv\Scripts\python.exe scripts\generate_sales_data.py
  ```
- **Casos contemplados:** Además del flujo válido (archivos diarios), el generador inyecta casos especiales (archivos repetidos, filas duplicadas o inválidas, esquemas rotos y archivos vacíos) para probar la resiliencia del ETL y asegurar el correcto manejo de errores.

> **Aviso de Privacidad y Repositorio:** El directorio de operaciones principal (`data/incoming/`, `data/processed/`, etc.) está ignorado y no se publica en GitHub por seguridad y volumen. Solo se conservan en control de versiones algunas pequeñas muestras ilustrativas de <=25 filas ubicadas en `data/sample/`.

## Tecnologías
- Python 3.11+
- Pandas (Procesamiento tabular)
- Pydantic (Validación de esquemas)
- PostgreSQL & psycopg3 (Base de datos relacional)
- pytest (Pruebas automatizadas)
- Ruff (Linter y formateador)

## Estado actual
Contrato de datos diseñado, generador de datos configurado y base de datos PostgreSQL (`etl_automation`) implementada localmente con esquemas de trazabilidad (`etl`) y analíticos (`warehouse`).
El módulo de **Descubrimiento Idempotente** ya está operativo, garantizando que el ETL registre archivos nuevos y salte archivos previamente procesados (mediante hash SHA-256) sin generar errores.

## Configuración Base de Datos
Para información detallada sobre la creación segura de credenciales, el esquema PostgreSQL y cómo ejecutar la configuración inicial de la base de datos de manera idempotente, revisa la documentación: [docs/setup.md](docs/setup.md).

## Fase de Descubrimiento (Discovery)
El sistema puede inspeccionar el directorio `data/incoming/` para encontrar y registrar nuevos archivos CSV de ventas. Para ejecutar este proceso:
```bash
.venv\Scripts\python.exe scripts\discover_files.py
```
Esta fase calcula el hash de los archivos por bloques sin saturar la memoria y asegura que no se procese dos veces el mismo archivo, registrando el progreso en `etl.pipeline_runs` y el inventario en `etl.file_registry`.
