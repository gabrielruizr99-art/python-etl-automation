import logging
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.etl.repositories import ETLRepository
from src.etl.validation_service import ValidationService


def setup_logging():
    log_dir = ROOT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "validation.log", encoding="utf-8")
        ]
    )

def main():
    setup_logging()
    
    start_time = time.time()
    repo = ETLRepository()
    service = ValidationService(repo)
    
    incoming_dir = ROOT_DIR / "data" / "incoming"
    
    res = service.run_validation(incoming_dir)
    
    duration = time.time() - start_time
    
    print(f"Run ID: {res.run_id}")
    print(f"Archivos validados (parcial o totalmente): {res.files_validated}")
    print(f"Archivos rechazados (por esquema): {res.files_rejected}")
    print(f"Archivos fallidos (error técnico): {res.files_failed}")
    print(f"Filas válidas totales: {res.valid_rows_total}")
    print(f"Filas rechazadas (en DB): {res.rejected_rows_total}")
    print("Códigos de rechazo agrupados:")
    for code, count in sorted(res.rejection_codes_summary.items()):
        print(f"  - {code}: {count}")
    print(f"Duración: {duration:.2f} segundos")

if __name__ == "__main__":
    main()
