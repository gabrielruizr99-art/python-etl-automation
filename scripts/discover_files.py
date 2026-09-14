import logging
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.etl.discovery_service import DiscoveryService
from src.etl.repositories import ETLRepository


def setup_logging():
    log_dir = ROOT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Solo escribimos a archivo para no ensuciar la salida estándar solicitada
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "discovery.log", encoding="utf-8")
        ]
    )

def main():
    setup_logging()
    
    start_time = time.time()
    
    repo = ETLRepository()
    service = DiscoveryService(repo)
    
    incoming_dir = ROOT_DIR / "data" / "incoming"
    
    result = service.run_discovery(incoming_dir)
    
    duration = time.time() - start_time
    
    # Imprimir exclusivamente lo solicitado por el usuario
    print(f"Run ID: {result.run_id}")
    print(f"Archivos encontrados: {result.files_discovered}")
    print(f"Archivos nuevos: {result.files_new}")
    print(f"Archivos duplicados: {result.files_duplicate}")
    print(f"Duracion: {duration:.2f} segundos")
    print(f"Estado final: {result.status}")
    
if __name__ == "__main__":
    main()
