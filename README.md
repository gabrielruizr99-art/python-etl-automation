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

## Tecnologías
- Python 3.11+
- Pandas (Procesamiento tabular)
- Pydantic (Validación de esquemas)
- PostgreSQL & psycopg3 (Base de datos relacional)
- pytest (Pruebas automatizadas)
- Ruff (Linter y formateador)

## Estado actual
Configuración inicial completada. Estructura de carpetas, entorno virtual y reglas del proyecto establecidas.

> **Aviso:** Los datos utilizados en este proyecto para demostración serán generados y completamente ficticios.
