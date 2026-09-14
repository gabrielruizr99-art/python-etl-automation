import csv
import logging
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from src.etl.hashing import calculate_sha256
from src.etl.repositories import ETLRepository
from src.etl.transformation import transform_row
from src.etl.validation import validate_row

logger = logging.getLogger(__name__)

@dataclass
class LoadResult:
    run_id: uuid.UUID
    files_processed: int
    files_failed: int
    rows_inserted: int

class LoadService:
    def __init__(self, repo: ETLRepository):
        self.repo = repo
        
    def _get_anticollision_path(self, dest_dir: Path, original_name: str, file_hash: str) -> Path:
        target_path = dest_dir / original_name
        if target_path.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            short_hash = file_hash[:8]
            stem = target_path.stem
            suffix = target_path.suffix
            new_name = f"{stem}_{timestamp}_{short_hash}{suffix}"
            return dest_dir / new_name
        return target_path

    def run_load(self, incoming_dir: Path, processed_dir: Path, run_id: uuid.UUID = None) -> LoadResult:
        if run_id is None:
            run_id = self.repo.create_pipeline_run()
            
        logger.info(f"Started load run {run_id}")
        
        validated_files = self.repo.get_validated_files()
        
        files_processed = 0
        files_failed = 0
        rows_inserted = 0
        
        for f_data in validated_files:
            file_id = f_data["file_id"]
            file_name = f_data["file_name"]
            expected_hash = f_data["file_hash"]
            file_path = incoming_dir / file_name
            
            if not file_path.exists():
                logger.error(f"File {file_name} not found before loading.")
                self.repo.update_file_status(file_id, "failed", "File not found on disk")
                files_failed += 1
                continue
                
            try:
                current_hash = calculate_sha256(file_path)
                if current_hash != expected_hash:
                    logger.error(f"File {file_name} hash mismatch.")
                    self.repo.update_file_status(file_id, "failed", "Hash mismatch before loading")
                    files_failed += 1
                    continue
            except Exception as e:
                logger.error(f"Error calculating hash for {file_name}: {e}")
                self.repo.update_file_status(file_id, "failed", "Error hashing file")
                files_failed += 1
                continue
                
            self.repo.update_file_status(file_id, "processing")
            
            valid_rows = []
            file_seen_ids = set()
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    dict_reader = csv.DictReader(f)
                    for row in dict_reader:
                        row_res = validate_row(row)
                        if row_res.is_valid:
                            sid = str(row.get("sale_id", "")).strip()
                            if sid in file_seen_ids:
                                continue
                            file_seen_ids.add(sid)
                            transformed = transform_row(row, file_name, current_hash)
                            valid_rows.append(transformed)
            except Exception as e:
                logger.error(f"Error reading/transforming file {file_name}: {e}")
                self.repo.update_file_status(file_id, "failed", "Error processing file rows")
                files_failed += 1
                continue
                
            conn = None
            try:
                conn = psycopg.connect(**self.repo.db_info)
                
                inserted_count = self.repo.load_file_to_warehouse(conn, valid_rows)
                
                target_path = self._get_anticollision_path(processed_dir, file_name, current_hash)
                
                try:
                    shutil.move(str(file_path), str(target_path))
                except Exception as e:
                    logger.error(f"Failed to move file {file_name} to {target_path}: {e}")
                    conn.rollback()
                    self.repo.update_file_status(file_id, "failed", "File move failed")
                    files_failed += 1
                    conn.close()
                    continue
                
                try:
                    conn.commit()
                except Exception as e:
                    logger.error(f"Failed to commit transaction for {file_name}: {e}")
                    try:
                        shutil.move(str(target_path), str(file_path))
                    except Exception as comp_e:
                        logger.critical(f"CRITICAL: Compensation failed for {file_name}. File is at {target_path} but DB is rolled back. Error: {comp_e}")
                    self.repo.update_file_status(file_id, "failed", "DB commit failed")
                    files_failed += 1
                    conn.close()
                    continue
                    
                conn.close()
                self.repo.update_file_status(file_id, "processed")
                files_processed += 1
                rows_inserted += inserted_count
                
            except Exception as e:
                if conn:
                    conn.rollback()
                    conn.close()
                logger.error(f"Technical error loading {file_name}: {e}")
                self.repo.update_file_status(file_id, "failed", "Technical error during DB load")
                files_failed += 1
                
        return LoadResult(run_id, files_processed, files_failed, rows_inserted)
