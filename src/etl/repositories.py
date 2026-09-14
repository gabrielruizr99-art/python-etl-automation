import logging
import uuid
from datetime import datetime, timezone

import psycopg

from src.etl.config import get_settings
from src.etl.models import DiscoveredFile

logger = logging.getLogger(__name__)

class ETLRepository:
    def __init__(self):
        self.settings = get_settings()
        self.db_info = self.settings.get_psycopg_connection_info()

    def create_pipeline_run(self) -> uuid.UUID:
        run_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        
        query = """
            INSERT INTO etl.pipeline_runs (run_id, status, started_at)
            VALUES (%s, %s, %s)
        """
        try:
            with psycopg.connect(**self.db_info) as conn, conn.cursor() as cur:
                cur.execute(query, (run_id, "running", now))
            return run_id
        except Exception as e:
            logger.error("Failed to create pipeline run.")
            raise RuntimeError("Database error during run creation") from e

    def register_file(self, run_id: uuid.UUID, file: DiscoveredFile) -> bool:
        """
        Registra el archivo descubierto.
        Devuelve True si el hash es nuevo y fue insertado, 
        Devuelve False si ya existía (gracias a ON CONFLICT DO NOTHING).
        """
        file_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        
        query = """
            INSERT INTO etl.file_registry 
            (file_id, run_id, file_name, file_hash, file_size_bytes, row_count, status, discovered_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (file_hash) DO NOTHING
            RETURNING file_id
        """
        # row_count se inicializa en 0
        params = (
            file_id, run_id, file.file_name, file.file_hash, 
            file.file_size_bytes, 0, "discovered", now
        )
        
        try:
            with psycopg.connect(**self.db_info) as conn, conn.cursor() as cur:
                cur.execute(query, params)
                result = cur.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Failed to register file {file.file_name}.")
            raise RuntimeError("Database error during file registration") from e

    def complete_pipeline_run(self, run_id: uuid.UUID, discovered: int, duplicates: int):
        now = datetime.now(timezone.utc)
        query = """
            UPDATE etl.pipeline_runs
            SET status = 'completed', 
                finished_at = %s, 
                files_discovered = %s,
                duplicate_files = %s
            WHERE run_id = %s
        """
        params = (now, discovered, duplicates, run_id)
        
        try:
            with psycopg.connect(**self.db_info) as conn, conn.cursor() as cur:
                cur.execute(query, params)
        except Exception as e:
            logger.error("Failed to complete pipeline run.")
            raise RuntimeError("Database error during run completion") from e

    def fail_pipeline_run(self, run_id: uuid.UUID, error_msg: str):
        now = datetime.now(timezone.utc)
        query = """
            UPDATE etl.pipeline_runs
            SET status = 'failed', finished_at = %s, error_message = %s
            WHERE run_id = %s
        """
        try:
            with psycopg.connect(**self.db_info) as conn, conn.cursor() as cur:
                cur.execute(query, (now, error_msg, run_id))
        except Exception as e:
            logger.error("Failed to mark pipeline run as failed.")
            raise RuntimeError("Database error during run failure") from e
