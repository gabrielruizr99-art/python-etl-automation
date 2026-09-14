import sys
from pathlib import Path

import psycopg

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.etl.config import get_settings


def print_separator(title: str):
    print(f"\n{'-' * 15} {title.upper()} {'-' * 15}")

def main():
    try:
        settings = get_settings()
        db_info = settings.get_psycopg_connection_info()
    except Exception as e:  # noqa: BLE001 # Justificación: Evitar crashear ante fallo de entorno
        print(f"Error cargando configuración: {e}")
        sys.exit(1)
        
    try:
        with psycopg.connect(**db_info) as conn:
            # Forzamos transacción a modo lectura
            conn.read_only = True
            
            with conn.cursor() as cur:
                # 1. Archivos por estado
                print_separator("Estado de Archivos")
                cur.execute("SELECT status, count(*) FROM etl.file_registry GROUP BY status ORDER BY count(*) DESC")
                for status, count in cur.fetchall():
                    print(f"{status.capitalize():<12}: {count} archivos")
                    
                # 2. Últimas 10 ejecuciones
                print_separator("Últimas 10 Ejecuciones")
                cur.execute("""
                    SELECT run_id, status, started_at, finished_at 
                    FROM etl.pipeline_runs 
                    ORDER BY started_at DESC LIMIT 10
                """)
                for run_id, status, start, end in cur.fetchall():
                    duration = "N/A"
                    if start and end:
                        dur_sec = (end - start).total_seconds()
                        duration = f"{dur_sec:.2f}s"
                    start_str = start.strftime("%Y-%m-%d %H:%M:%S") if start else "N/A"
                    print(f"[{start_str}] {status.upper():<10} | Duración: {duration:<8} | ID: {run_id}")
                    
                # 3. Métricas de Ventas
                print_separator("Warehouse Sales")
                cur.execute("SELECT count(*), max(sale_date) FROM warehouse.sales")
                count, max_date = cur.fetchone()
                print(f"Total de ventas cargadas : {count}")
                print(f"Última fecha registrada  : {max_date if max_date else 'N/A'}")
                
                # 4. Último archivo procesado
                cur.execute("""
                    SELECT file_name, processed_at 
                    FROM etl.file_registry 
                    WHERE status = 'processed' 
                    ORDER BY processed_at DESC NULLS LAST LIMIT 1
                """)
                last_file = cur.fetchone()
                print_separator("Último Archivo Procesado")
                if last_file:
                    print(f"Archivo: {last_file[0]}")
                else:
                    print("Ningún archivo procesado aún.")
                    
                # 5. Rechazos
                print_separator("Motivos de Rechazo")
                cur.execute("SELECT reason_code, count(*) FROM etl.rejected_records GROUP BY reason_code ORDER BY count(*) DESC")
                rejections = cur.fetchall()
                if rejections:
                    for reason, r_count in rejections:
                        print(f"{reason:<25}: {r_count} filas")
                else:
                    print("No hay filas rechazadas.")
                    
                # 6. Última ejecución fallida
                cur.execute("""
                    SELECT run_id, started_at, finished_at 
                    FROM etl.pipeline_runs 
                    WHERE status = 'failed' 
                    ORDER BY started_at DESC LIMIT 1
                """)
                failed_run = cur.fetchone()
                if failed_run:
                    print_separator("Última Ejecución Fallida")
                    start_str = failed_run[1].strftime("%Y-%m-%d %H:%M:%S") if failed_run[1] else "N/A"
                    print(f"Fecha de inicio : {start_str}")
                    print(f"Run ID          : {failed_run[0]}")
                    
    except Exception as e:  # noqa: BLE001 # Justificación: Límite del script para abortar limpiamente
        print(f"Error consultando el estado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
