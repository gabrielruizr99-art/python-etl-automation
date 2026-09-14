# Manual Operativo

Este documento describe la operativa diaria, solución de problemas y tareas de mantenimiento del pipeline ETL.

## Operación Diaria

El pipeline está diseñado para correr automáticamente a través del programador de tareas de Windows.
Se recomienda correrlo al final del día (ej. 20:00) cuando todos los CSV de ventas hayan sido depositados en la carpeta `data/incoming`.

Para consultar el estado general de las ejecuciones, ejecute:
```powershell
.venv\Scripts\python.exe scripts\pipeline_status.py
```
Este script proporcionará una vista rápida de:
- Ejecuciones recientes y su estado.
- Volumen de ventas procesadas.
- Registro de errores y motivos de rechazo.

## Códigos de Salida

El script `run_pipeline.ps1` y `run_pipeline.py` devolverán uno de los siguientes códigos de salida:
- `0`: Ejecución exitosa. Todos los archivos válidos fueron procesados.
- `1`: Fallo del pipeline (errores de base de datos, excepciones en tiempo de ejecución).
- `2`: Configuración inválida (falta `.env`, credenciales incorrectas, falta entorno virtual).
- `3`: Ejecución omitida. Otro pipeline se encuentra en ejecución activa.

## Tareas Programadas de Windows

Para registrar la tarea automática en Windows:
```powershell
.\scripts\register_scheduled_task.ps1 -ConfirmRegistration
```
(Si omite `-ConfirmRegistration`, el script sólo simulará la acción mostrando la configuración propuesta).

Para eliminar manualmente la tarea registrada:
```powershell
Unregister-ScheduledTask -TaskName "Python ETL Automation" -Confirm:$false
```

## Prevención de Ejecuciones Simultáneas

El sistema utiliza *Advisory Locks* de PostgreSQL (`pg_try_advisory_lock`).
Esto garantiza de forma robusta y nativa en la base de datos que jamás existirán dos pipelines modificando el `file_registry` o cargando ventas al mismo tiempo.
Si una segunda instancia despierta mientras la primera sigue corriendo, la segunda finalizará de inmediato devolviendo el código `3`.

## Revisión de Logs y Recuperación ante Fallos

- **Logs Diarios**: Puede consultar `logs/scheduler.log` para revisar a qué hora inició y finalizó la tarea programada.
- **Logs Detallados**: Puede consultar `logs/pipeline.log` para revisar trazas específicas en Python.
- **Fallos y Recuperación**: El pipeline es idempotente. Si falla a la mitad, puede ser ejecutado nuevamente sin riesgo de duplicar información en `warehouse.sales`. Las filas rechazadas se archivan automáticamente y no bloquean el resto de la ejecución.
