import sys
from pathlib import Path

import psycopg
import pytest
from pydantic import ValidationError

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from scripts.setup_database import main as setup_db_main
from src.etl.config import Settings, get_settings


def test_config_missing_variables(monkeypatch):
    # Deshabilita temporalmente variables de entorno obligatorias
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)

def test_config_password_hidden():
    settings = get_settings()
    # Asegura que repr no expone la contraseña
    rep = repr(settings)
    password = settings.db_password.get_secret_value()
    assert password not in rep
    assert "Settings" in rep

def test_setup_idempotency_and_objects():
    # Ejecuta el script dos veces para probar idempotencia
    setup_db_main()
    setup_db_main()
    
    settings = get_settings()
    db_info = settings.get_psycopg_connection_info()
    
    with psycopg.connect(**db_info) as conn, conn.cursor() as cur:
        # 1. Comprobar que los esquemas existen
            cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('etl', 'warehouse')")
            schemas = {row[0] for row in cur.fetchall()}
            assert "etl" in schemas
            assert "warehouse" in schemas
            
            # 2. Comprobar que las 4 tablas existen
            cur.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema IN ('etl', 'warehouse')
            """)
            tables = {(row[0], row[1]) for row in cur.fetchall()}
            expected_tables = {
                ("etl", "pipeline_runs"),
                ("etl", "file_registry"),
                ("etl", "rejected_records"),
                ("warehouse", "sales")
            }
            assert expected_tables.issubset(tables)
            
            # 3. Comprobar columnas de restricción (e.g. validación básica)
            cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'warehouse' AND table_name = 'sales'")
            columns = {row[0]: row[1] for row in cur.fetchall()}
            assert "quantity" in columns
            assert "unit_price" in columns
            assert columns["quantity"] == "integer"
            assert columns["unit_price"] == "numeric"
            
            # 4. No comprobamos que estén vacías porque los tests comparten la base de datos real.
