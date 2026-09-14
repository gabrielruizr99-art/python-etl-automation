import csv
import shutil
import uuid
from decimal import Decimal

import psycopg
import pytest

from src.etl.discovery_service import DiscoveryService
from src.etl.load_service import LoadService
from src.etl.repositories import ETLRepository
from src.etl.transformation import transform_row
from src.etl.validation_service import ValidationService


def test_transformation_financial_calcs():
    row = {
        "sale_id": str(uuid.uuid4()),
        "sale_date": "2026-04-01",
        "sale_time": "10:30:00",
        "branch_id": "BR-01",
        "customer_id": "C-0100",
        "product_id": "P-0010",
        "seller_id": "S-10",
        "sales_channel": "Store",
        "payment_method": "Cash",
        "quantity": "3",
        "unit_price": "10.125",
        "discount_pct": "0.15"
    }
    
    res = transform_row(row, "test.csv", "hash123")
    assert isinstance(res["quantity"], int)
    assert isinstance(res["unit_price"], Decimal)
    assert res["unit_price"] == Decimal("10.13") # ROUND_HALF_UP applied
    assert res["discount_pct"] == Decimal("0.15")
    
    # gross = 3 * 10.125 = 30.375 -> rounded to 30.38
    assert res["gross_amount"] == Decimal("30.38")
    
    # discount = 30.38 * 0.15 = 4.557 -> rounded to 4.56
    assert res["discount_amount"] == Decimal("4.56")
    
    # net = 30.38 - 4.56 = 25.82
    assert res["net_amount"] == Decimal("25.82")

@pytest.fixture
def repo():
    return ETLRepository()

@pytest.fixture
def db_transaction(monkeypatch, repo):
    conn = psycopg.connect(**repo.db_info)
    conn.autocommit = False
    
    def mock_connect(*args, **kwargs):
        return conn
        
    original_commit = conn.commit
    original_close = conn.close
    
    def mock_commit():
        pass
        
    def mock_close():
        pass
        
    monkeypatch.setattr(psycopg, "connect", mock_connect)
    monkeypatch.setattr(conn, "commit", mock_commit)
    monkeypatch.setattr(conn, "close", mock_close)
    
    yield conn
    
    original_close() # This will close and rollback implicitly since it was not committed

def test_rollback_on_move_failure(tmp_path, monkeypatch, repo, db_transaction):
    incoming_dir = tmp_path / "incoming"
    processed_dir = tmp_path / "processed"
    incoming_dir.mkdir()
    processed_dir.mkdir()
    
    file_name = "test_load_rollback.csv"
    file_path = incoming_dir / file_name
    headers = ["sale_id", "sale_date", "sale_time", "branch_id", "customer_id", "product_id", "seller_id", "sales_channel", "payment_method", "quantity", "unit_price", "discount_pct"]
    row = [str(uuid.uuid4()), "2026-04-01", "10:30:00", "BR-01", "C-0100", "P-01", "S-01", "Store", "Cash", "1", "10.0", "0.0"]
    with file_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(row)
        
    # We need a record in file_registry to simulate validation
    run_id = repo.create_pipeline_run()
    disc_svc = DiscoveryService(repo)
    disc_svc.run_discovery(incoming_dir, run_id)
    
    val_svc = ValidationService(repo)
    val_svc.run_validation(incoming_dir, run_id)
    
    # Simulate move failure
    def mock_move(*args, **kwargs):
        raise OSError("Simulated move failure")
    monkeypatch.setattr(shutil, "move", mock_move)
    
    load_svc = LoadService(repo)
    res = load_svc.run_load(incoming_dir, processed_dir, run_id)
    
    assert res.files_failed == 1
    assert res.rows_inserted == 0
    assert file_path.exists()
    
    # Verify rollback by checking DB directly
    with db_transaction.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM warehouse.sales WHERE sale_id = %s", (row[0],))
        assert cur.fetchone()[0] == 0

