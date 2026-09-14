import logging
from datetime import datetime, timezone
from pathlib import Path

from src.etl.hashing import calculate_sha256
from src.etl.models import DiscoveredFile

logger = logging.getLogger(__name__)

def discover_csv_files(directory_path: Path) -> list[DiscoveredFile]:
    """
    Busca archivos .csv directamente en el directorio especificado.
    Ignora subdirectorios, archivos ocultos y temporales.
    Retorna la lista ordenada determinísticamente por nombre.
    """
    if not directory_path.is_dir():
        logger.warning(f"Directory {directory_path} does not exist or is not a directory.")
        return []
        
    discovered = []
    # iterdir() para hijos directos, ordenados por nombre para ser determinista
    sorted_files = sorted(directory_path.iterdir(), key=lambda x: x.name)
    
    for file_path in sorted_files:
        if not file_path.is_file():
            continue
            
        # Filtros de exclusión: solo csv, no ocultos/temporales
        if file_path.suffix.lower() != '.csv':
            continue
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            continue
            
        try:
            stat = file_path.stat()
            file_hash = calculate_sha256(file_path)
            
            modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            
            discovered.append(DiscoveredFile(
                file_name=file_path.name,
                file_path=str(file_path.resolve()),
                file_hash=file_hash,
                file_size_bytes=stat.st_size,
                modified_at=modified_at
            ))
        except Exception as e:  # noqa: BLE001
            # Captura de error sanitizada
            logger.error(f"Error processing file {file_path.name}: {e!s}")
            continue
            
    return discovered
