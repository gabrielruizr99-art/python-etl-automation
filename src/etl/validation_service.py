import csv
import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

from src.etl.repositories import ETLRepository
from src.etl.validation import validate_file_schema, validate_row

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    run_id: uuid.UUID
    files_validated: int
    files_rejected: int
    files_failed: int
    valid_rows_total: int
    rejected_rows_total: int
    rejection_codes_summary: dict
    status: str

class ValidationService:
    def __init__(self, repo: ETLRepository):
        self.repo = repo
        
    def run_validation(self, incoming_dir: Path, run_id: uuid.UUID = None) -> ValidationResult:
        if run_id is None:
            run_id = self.repo.create_pipeline_run()
        logger.info(f"Started validation run {run_id}")
        
        discovered_files = self.repo.get_discovered_files()
        
        files_validated = 0
        files_rejected = 0
        files_failed = 0
        valid_rows_total = 0
        rejected_rows_total = 0
        
        rejection_codes_summary = {}
        
        # Para detectar duplicados entre archivos del mismo lote
        batch_sale_ids = set()
        
        for f_data in discovered_files:
            file_id = f_data["file_id"]
            file_name = f_data["file_name"]
            file_path = incoming_dir / file_name
            
            try:
                self.repo.update_file_status(file_id, "processing")
                
                if not file_path.exists():
                    self.repo.update_file_status(file_id, "failed", "File not found on disk")
                    files_failed += 1
                    continue
                    
                # Leer encabezados
                with file_path.open("r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    try:
                        headers = next(reader)
                    except StopIteration:
                        headers = []
                        
                # 1. Validar esquema
                schema_res = validate_file_schema(headers)
                if not schema_res.is_valid_schema:
                    # Rechazo total de archivo (row_number = 0, datos sanitizados)
                    safe_raw_data = json.dumps({"headers": headers})
                    rejection = (
                        uuid.uuid4(), run_id, file_id, 0, 
                        schema_res.rejection_code, schema_res.rejection_detail, safe_raw_data
                    )
                    self.repo.insert_rejected_records([rejection])
                    self.repo.update_file_status(file_id, "rejected")
                    files_rejected += 1
                    
                    rejection_codes_summary[schema_res.rejection_code] = rejection_codes_summary.get(schema_res.rejection_code, 0) + 1
                    logger.info(f"File {file_name} rejected: {schema_res.rejection_code}")
                    continue
                    
                # 2. Validar filas
                file_valid_rows = 0
                file_rejected_rows = 0
                rejected_records_batch = []
                
                # Necesitamos revisar duplicados en DB de una vez o por lote
                # Extraemos todos los sale_id del archivo para chequear contra DB
                file_sale_ids = set()
                with file_path.open("r", encoding="utf-8") as f:
                    dict_reader = csv.DictReader(f)
                    for row in dict_reader:
                        sid = row.get("sale_id", "").strip()
                        if sid:
                            file_sale_ids.add(sid)
                            
                # Obtener duplicados ya en warehouse
                existing_in_db = self.repo.get_existing_sale_ids_in_warehouse(file_sale_ids)
                
                # Leer de nuevo y procesar fila por fila
                file_seen_ids = set()
                
                with file_path.open("r", encoding="utf-8") as f:
                    dict_reader = csv.DictReader(f)
                    for row_num_idx, row in enumerate(dict_reader, start=2): # header is row 1
                        row_res = validate_row(row)
                        codes = row_res.rejection_codes.copy()
                        details = row_res.rejection_details.copy()
                        
                        sid = str(row.get("sale_id", "")).strip()
                        
                        # Validación de duplicados
                        if sid:
                            if sid in file_seen_ids:
                                codes.append("DUPLICATE_SALE_ID")
                                details.append("sale_id is duplicated within the same file")
                            elif sid in batch_sale_ids:
                                codes.append("DUPLICATE_SALE_ID")
                                details.append("sale_id is duplicated within the current batch")
                            elif sid in existing_in_db:
                                codes.append("DUPLICATE_SALE_ID")
                                details.append("sale_id already exists in warehouse")
                                
                            file_seen_ids.add(sid)
                            batch_sale_ids.add(sid)
                            
                        is_valid = len(codes) == 0
                        
                        if is_valid:
                            file_valid_rows += 1
                        else:
                            file_rejected_rows += 1
                            safe_raw_data = json.dumps(row)
                            
                            # Creamos un registro de rechazo, uniendo los motivos
                            code_str = ",".join(codes)
                            detail_str = "; ".join(details)
                            
                            rejected_records_batch.append((
                                uuid.uuid4(), run_id, file_id, row_num_idx,
                                code_str, detail_str, safe_raw_data
                            ))
                            
                            for c in codes:
                                rejection_codes_summary[c] = rejection_codes_summary.get(c, 0) + 1
                                
                if rejected_records_batch:
                    self.repo.insert_rejected_records(rejected_records_batch)
                    
                self.repo.update_file_status(file_id, "validated")
                files_validated += 1
                valid_rows_total += file_valid_rows
                rejected_rows_total += file_rejected_rows
                
                logger.info(f"File {file_name} validated. Valid rows: {file_valid_rows}, Rejected rows: {file_rejected_rows}")
                
            except Exception: # noqa: BLE001
                safe_error = "Technical error during validation"
                logger.error(f"File {file_name} failed: {safe_error}")
                self.repo.update_file_status(file_id, "failed", safe_error)
                files_failed += 1
                
        self.repo.update_pipeline_run_validation_metrics(run_id, files_validated, files_rejected, valid_rows_total, rejected_rows_total)
        
        return ValidationResult(
            run_id, files_validated, files_rejected, files_failed, 
            valid_rows_total, rejected_rows_total, rejection_codes_summary, "completed"
        )
