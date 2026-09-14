import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from src.etl.discovery import discover_csv_files
from src.etl.repositories import ETLRepository

logger = logging.getLogger(__name__)

@dataclass
class DiscoveryResult:
    run_id: uuid.UUID
    files_discovered: int
    files_new: int
    files_duplicate: int
    status: str

class DiscoveryService:
    def __init__(self, repo: ETLRepository):
        self.repo = repo

    def run_discovery(self, incoming_dir: Path) -> DiscoveryResult:
        run_id = self.repo.create_pipeline_run()
        logger.info(f"Started pipeline run {run_id} for discovery.")
        
        discovered_count = 0
        new_count = 0
        duplicate_count = 0
        
        try:
            files = discover_csv_files(incoming_dir)
            discovered_count = len(files)
            
            for file in files:
                # Log solo hash abreviado (máx 12 caracteres)
                short_hash = file.file_hash[:12]
                logger.info(f"Processing {file.file_name} (hash: {short_hash}...)")
                
                is_new = self.repo.register_file(run_id, file)
                if is_new:
                    new_count += 1
                else:
                    duplicate_count += 1
                    
            self.repo.complete_pipeline_run(run_id, discovered_count, duplicate_count)
            logger.info(f"Completed run {run_id}. Discovered: {discovered_count}, New: {new_count}, Duplicates: {duplicate_count}.")
            
            return DiscoveryResult(run_id, discovered_count, new_count, duplicate_count, "completed")
            
        except Exception:  # noqa: BLE001
            # Sanitizar el error en la base de datos para no exponer credenciales ni stack traces
            safe_error_msg = "Unexpected error occurred during file discovery phase."
            logger.error(f"Run {run_id} failed due to internal error. Details kept in secure logs if needed.")
            self.repo.fail_pipeline_run(run_id, safe_error_msg)
            return DiscoveryResult(run_id, discovered_count, new_count, duplicate_count, "failed")
