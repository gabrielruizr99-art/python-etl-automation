import logging
import shutil
import sys
import time
from pathlib import Path

import psycopg

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.etl.discovery_service import DiscoveryService
from src.etl.load_service import LoadService
from src.etl.repositories import ETLRepository
from src.etl.validation_service import ValidationService


def setup_logging():
    log_dir = ROOT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8")
        ]
    )

def _get_anticollision_path(dest_dir: Path, original_name: str, file_hash: str) -> Path:
    from datetime import datetime, timezone
    target_path = dest_dir / original_name
    if target_path.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        short_hash = file_hash[:8] if file_hash else "nohash"
        stem = target_path.stem
        suffix = target_path.suffix
        new_name = f"{stem}_{timestamp}_{short_hash}{suffix}"
        return dest_dir / new_name
    return target_path

def main():
    setup_logging()
    
    start_time = time.time()
    repo = ETLRepository()
    
    incoming_dir = ROOT_DIR / "data" / "incoming"
    processed_dir = ROOT_DIR / "data" / "processed"
    rejected_dir = ROOT_DIR / "data" / "rejected"
    duplicates_dir = ROOT_DIR / "data" / "processed" / "duplicates"
    
    processed_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)
    duplicates_dir.mkdir(parents=True, exist_ok=True)
    
    run_id = repo.create_pipeline_run()
    
    # 1. Descubrimiento
    discovery_svc = DiscoveryService(repo)
    disc_res = discovery_svc.run_discovery(incoming_dir, run_id)
    
    # Archivar duplicados puros
    for path, f_hash in disc_res.duplicate_paths:
        target_path = _get_anticollision_path(duplicates_dir, path.name, f_hash)
        try:
            shutil.move(str(path), str(target_path))
        except Exception as e:
            logging.error(f"Error moving duplicate {path.name}: {e}")
            
    # 2. Validación
    validation_svc = ValidationService(repo)
    val_res = validation_svc.run_validation(incoming_dir, run_id)
    
    # 3. Carga Transaccional
    load_svc = LoadService(repo)
    load_res = load_svc.run_load(incoming_dir, processed_dir, run_id)
    
    # 4. Archivado de archivos rechazados
    try:
        with psycopg.connect(**repo.db_info) as conn, conn.cursor() as cur:
            cur.execute("SELECT file_name, file_hash FROM etl.file_registry WHERE status = 'rejected'")
            rejected_files = cur.fetchall()
            
            for file_name, file_hash in rejected_files:
                src_path = incoming_dir / file_name
                if src_path.exists():
                    target_path = _get_anticollision_path(rejected_dir, file_name, file_hash)
                    try:
                        shutil.move(str(src_path), str(target_path))
                    except Exception as e:
                        logging.error(f"Error moving rejected file {file_name}: {e}")
    except Exception as e:
        logging.error(f"Error moving rejected files: {e}")
        
    duration = time.time() - start_time
    
    filas_omitidas = val_res.valid_rows_total - load_res.rows_inserted
    
    print(f"Run ID: {run_id}")
    print(f"Archivos encontrados: {disc_res.files_discovered}")
    print(f"Archivos nuevos: {disc_res.files_new}")
    print(f"Archivos duplicados: {disc_res.files_duplicate}")
    print(f"Archivos validados: {val_res.files_validated}")
    print(f"Archivos procesados: {load_res.files_processed}")
    print(f"Archivos rechazados: {val_res.files_rejected}")
    print(f"Filas insertadas: {load_res.rows_inserted}")
    print(f"Filas omitidas por duplicidad: {max(0, filas_omitidas)}")
    print(f"Filas rechazadas: {val_res.rejected_rows_total}")
    print(f"Duración: {duration:.2f} segundos")
    print(f"Estado final: {'COMPLETED' if disc_res.status == 'completed' and val_res.status == 'completed' else 'WITH ERRORS'}")

if __name__ == "__main__":
    main()
