# Security Policy

## Manejo de Credenciales y Uso de `.env`
Este proyecto requiere variables de entorno y credenciales para conectarse a PostgreSQL. Bajo ningún concepto deben agregarse credenciales al historial de control de versiones. 
- Utilice siempre el archivo `.env`, el cual está explícitamente ignorado en `.gitignore`.
- Se provee una plantilla segura denominada `.env.example` para referenciar las variables necesarias.

## Archivos Ignorados
Los directorios operativos (`logs`, `data/incoming`, `data/processed`, `data/rejected`) y los entornos virtuales (`.venv`) están intencionalmente ignorados para prevenir fugas de información operacional y de la infraestructura local del desarrollador.

## Datos Ficticios
El dataset de muestra y los archivos generados con el script de simulación contienen **datos exclusivamente ficticios**. No se incluye ni se procesa Información de Identificación Personal (PII) real en este repositorio.

## Privilegios de Base de Datos
- **Entornos de Producción:** Se recomienda encarecidamente la creación de un usuario específico de base de datos con **privilegios mínimos** restringidos a las operaciones de inserción, lectura y manipulación de los esquemas `etl` y `warehouse`.
- **Advertencia:** No utilice el superusuario `postgres` como usuario de conexión de la aplicación en ningún despliegue productivo.

## Reporte Responsable de Vulnerabilidades
Si descubre una vulnerabilidad de seguridad dentro del diseño transaccional o la implementación de este pipeline, por favor no cree un "Issue" público. En su lugar, reporte responsablemente mediante contacto directo con el autor del repositorio.
