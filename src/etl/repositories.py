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

    def get_discovered_files(self) -> list:
        """Devuelve los archivos con estado 'discovered' para ser procesados."""
        query = """
            SELECT file_id, run_id, file_name, file_hash, file_size_bytes 
            FROM etl.file_registry 
            WHERE status = 'discovered'
            ORDER BY file_name
        """
        try:
            with psycopg.connect(**self.db_info) as conn, conn.cursor() as cur:
                cur.execute(query)
                # Retornamos dicts para facilidad
                return [
                    {
                        "file_id": row[0], "run_id": row[1], 
                        "file_name": row[2], "file_hash": row[3], "file_size_bytes": row[4]
                    } 
                    for row in cur.fetchall()
                ]
        except Exception as e:
            logger.error("Failed to get discovered files.")
            raise RuntimeError("Database error") from e

    def get_validated_files(self) -> list:
        """Devuelve los archivos con estado 'validated' para ser cargados."""
        query = """
            SELECT file_id, run_id, file_name, file_hash, file_size_bytes 
            FROM etl.file_registry 
            WHERE status = 'validated'
            ORDER BY file_name
        """
        try:
            with psycopg.connect(**self.db_info) as conn, conn.cursor() as cur:
                cur.execute(query)
                return [
                    {
                        "file_id": row[0], "run_id": row[1], 
                        "file_name": row[2], "file_hash": row[3], "file_size_bytes": row[4]
                    } 
                    for row in cur.fetchall()
                ]
        except Exception as e:
            logger.error("Failed to get validated files.")
            raise RuntimeError("Database error") from e

    def update_file_status(self, file_id: uuid.UUID, status: str, error_message: str | None = None):
        """Actualiza el estado de un archivo en file_registry."""
        now = datetime.now(timezone.utc)
        query = """
            UPDATE etl.file_registry 
            SET status = %s, processed_at = %s, error_message = %s
            WHERE file_id = %s
        """
        try:
            with psycopg.connect(**self.db_info) as conn, conn.cursor() as cur:
                cur.execute(query, (status, now, error_message, file_id))
        except Exception as e:
            logger.error(f"Failed to update status for file {file_id}.")
            raise RuntimeError("Database error") from e

    def insert_rejected_records(self, records: list):
        """
        Inserta un lote de registros rechazados.
        records: lista de tuplas (rejection_id, run_id, file_id, row_number, reason_code, reason_detail, raw_data_json)
        """
        if not records:
            return
            
        query = """
            INSERT INTO etl.rejected_records 
            (rejection_id, run_id, file_id, row_number, reason_code, reason_detail, raw_data, rejected_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        now = datetime.now(timezone.utc)
        # Añadir rejected_at a cada registro
        records_with_time = [(*r, now) for r in records]
        
        try:
            with psycopg.connect(**self.db_info) as conn, conn.cursor() as cur:
                cur.executemany(query, records_with_time)
        except Exception as e:
            logger.error("Failed to insert rejected records.")
            raise RuntimeError("Database error") from e

    def get_existing_sale_ids_in_warehouse(self, sale_ids: set) -> set:
        """Devuelve los sale_id que ya existen en warehouse.sales."""
        if not sale_ids:
            return set()
            
        query = "SELECT sale_id FROM warehouse.sales WHERE sale_id = ANY(%s)"
        try:
            with psycopg.connect(**self.db_info) as conn, conn.cursor() as cur:
                cur.execute(query, (list(sale_ids),))
                return {row[0] for row in cur.fetchall()}
        except Exception as e:
            logger.error("Failed to check existing sale_ids.")
            raise RuntimeError("Database error") from e

    def update_pipeline_run_validation_metrics(self, run_id: uuid.UUID, processed: int, rejected: int, valid_rows: int, rejected_rows: int):
        """Actualiza las métricas de validación para una ejecución."""
        query = """
            UPDATE etl.pipeline_runs
            SET status = 'completed', 
                finished_at = %s,
                files_processed = %s,
                files_rejected = %s,
                valid_rows = %s,
                rejected_rows = %s
            WHERE run_id = %s
        """
        now = datetime.now(timezone.utc)
        try:
            with psycopg.connect(**self.db_info) as conn, conn.cursor() as cur:
                cur.execute(query, (now, processed, rejected, valid_rows, rejected_rows, run_id))
        except Exception as e:
            logger.error("Failed to update validation metrics.")
            raise RuntimeError("Database error") from e

    def load_file_to_warehouse(self, conn, rows: list) -> int:
        """
        Carga filas transformadas al data warehouse usando una tabla temporal
        y COPY dentro de la conexión proporcionada. Retorna el número de registros insertados.
        """
        if not rows:
            return 0
            
        columns = [
            "sale_id", "sale_date", "sale_time", "branch_id", "customer_id", 
            "product_id", "seller_id", "sales_channel", "payment_method", 
            "quantity", "unit_price", "discount_pct", "gross_amount", 
            "discount_amount", "net_amount", "source_file", "source_hash"
        ]
        
        with conn.cursor() as cur:
            # Tabla temporal para la transacción actual
            cur.execute("CREATE TEMP TABLE staging_sales (LIKE warehouse.sales INCLUDING DEFAULTS) ON COMMIT DROP")
            
            with cur.copy(f"COPY staging_sales ({', '.join(columns)}) FROM STDIN") as copy:
                for row in rows:
                    copy.write_row([row[col] for col in columns])
                    
            # Insertar en tabla final con ON CONFLICT
            insert_query = f"""
                INSERT INTO warehouse.sales ({', '.join(columns)})
                SELECT {', '.join(columns)}
                FROM staging_sales
                ON CONFLICT (sale_id) DO NOTHING
                RETURNING sale_id
            """
            cur.execute(insert_query)
            inserted = cur.fetchall()
            return len(inserted)
