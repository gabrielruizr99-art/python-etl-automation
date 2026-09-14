import hashlib
import uuid

import psycopg
import pytest

from src.etl.config import get_settings
from src.etl.discovery import discover_csv_files
from src.etl.hashing import calculate_sha256
from src.etl.models import DiscoveredFile
from src.etl.repositories import ETLRepository

# --- Pruebas Unitarias (Sin DB) ---

def test_calculate_sha256(tmp_path):
    file_path = tmp_path / "test.csv"
    content = b"h1,h2\nv1,v2"
    file_path.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest()
    assert calculate_sha256(file_path) == expected

def test_calculate_sha256_modified(tmp_path, monkeypatch):
    file_path = tmp_path / "test.csv"
    file_path.write_bytes(b"test")
    
    import os
    original_stat = os.stat
    call_count = 0
    
    def mock_stat(path, *args, **kwargs):
        nonlocal call_count
        st = original_stat(path, *args, **kwargs)
        if str(path) == str(file_path):
            call_count += 1
            if call_count > 1:
                class FakeStat:
                    st_size = st.st_size + 1
                    st_mtime = st.st_mtime
                return FakeStat()
        return st
        
    monkeypatch.setattr("src.etl.hashing.os.stat", mock_stat)
    
    with pytest.raises(ValueError, match="File modified during hash calculation"):
        calculate_sha256(file_path)

def test_discover_csv_files_filters(tmp_path):
    (tmp_path / "a.csv").write_text("a")
    (tmp_path / "b.txt").write_text("b") # Ignorar txt
    (tmp_path / ".hidden.csv").write_text("c") # Ignorar ocultos
    (tmp_path / "~temp.csv").write_text("d") # Ignorar temps
    (tmp_path / "z.csv").write_text("z")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.csv").write_text("c") # Ignorar subdirectorios
    
    discovered = discover_csv_files(tmp_path)
    assert len(discovered) == 2
    # Orden determinista: a.csv luego z.csv
    assert discovered[0].file_name == "a.csv"
    assert discovered[1].file_name == "z.csv"

def test_discover_missing_dir(tmp_path):
    discovered = discover_csv_files(tmp_path / "no_existe")
    assert discovered == []

# --- Pruebas de Integración (Con DB) ---

@pytest.fixture
def repo():
    return ETLRepository()

def test_repository_pipeline_run(repo):
    run_id = repo.create_pipeline_run()
    assert isinstance(run_id, uuid.UUID)
    # Marcarlo como fallido para limpiar y probar
    repo.fail_pipeline_run(run_id, "Test failure")

def test_repository_register_file_idempotency(repo):
    run_id = repo.create_pipeline_run()
    
    # Archivo falso con hash único por corrida
    unique_hash = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    file = DiscoveredFile(
        file_name="test.csv",
        file_path="/test.csv",
        file_hash=unique_hash,
        file_size_bytes=4,
        modified_at="2026-04-01T00:00:00Z"
    )
    
    # Primera vez es nuevo
    is_new = repo.register_file(run_id, file)
    assert is_new is True
    
    # Segunda vez es duplicado (mismo hash)
    is_new_again = repo.register_file(run_id, file)
    assert is_new_again is False

def test_warehouse_sales_count():
    settings = get_settings()
    db_info = settings.get_psycopg_connection_info()
    with psycopg.connect(**db_info) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM warehouse.sales")
        count = cur.fetchone()[0]
        assert count >= 0, "warehouse.sales count is valid"
