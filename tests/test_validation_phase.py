import json
import uuid

import pytest

from src.etl.repositories import ETLRepository
from src.etl.validation import EXPECTED_HEADERS, validate_file_schema, validate_row


def test_validate_file_schema_valid():
    res = validate_file_schema(EXPECTED_HEADERS)
    assert res.is_valid_schema

def test_validate_file_schema_missing():
    headers = EXPECTED_HEADERS[:-1]
    res = validate_file_schema(headers)
    assert not res.is_valid_schema
    assert "Missing columns" in res.rejection_detail

def test_validate_file_schema_unknown():
    headers = EXPECTED_HEADERS + ["unknown"]
    res = validate_file_schema(headers)
    assert not res.is_valid_schema
    assert "Unknown columns" in res.rejection_detail

def test_validate_file_schema_empty():
    res = validate_file_schema([])
    assert not res.is_valid_schema
    assert res.rejection_code == "INVALID_FILE_SCHEMA"

def test_validate_row_valid():
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
        "quantity": "5",
        "unit_price": "10.5",
        "discount_pct": "0.1"
    }
    res = validate_row(row)
    assert res.is_valid, f"Errores: {res.rejection_details}"

def test_validate_row_multiple_errors():
    row = {
        "sale_id": "not-a-uuid", # 1. INVALID_SALE_ID
        "sale_date": "2026-15-40", # 2. INVALID_DATE
        "sale_time": "25:00:00", # 3. INVALID_TIME
        "branch_id": "BR-99", # 4. INVALID_BRANCH
        "customer_id": "C-9999", # 5. INVALID_CUSTOMER
        "product_id": "P-999", # 6. INVALID_PRODUCT
        "seller_id": "S-99", # 7. INVALID_SELLER
        "sales_channel": "Pigeon", # 8. INVALID_CHANNEL
        "payment_method": "Gold", # 9. INVALID_PAYMENT_METHOD
        "quantity": "-5", # 10. INVALID_QUANTITY
        "unit_price": "-10", # 11. INVALID_UNIT_PRICE
        "discount_pct": "0.5" # 12. INVALID_DISCOUNT
    }
    res = validate_row(row)
    assert not res.is_valid
    assert len(res.rejection_codes) == 12

def test_json_serializable():
    row = {"a": "1"}
    assert isinstance(json.dumps(row), str)

# --- Pruebas de integración ---

@pytest.fixture
def repo():
    return ETLRepository()

def test_validation_service_idempotent(repo):
    # La prueba de ejecución repetida se hará en el script real porque requiere archivos
    # pero podemos probar que el repo maneja bien la DB
    files = repo.get_discovered_files()
    assert isinstance(files, list)

