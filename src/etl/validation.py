import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

EXPECTED_HEADERS = [
    "sale_id", "sale_date", "sale_time", "branch_id",
    "customer_id", "product_id", "seller_id", "sales_channel",
    "payment_method", "quantity", "unit_price", "discount_pct"
]

VALID_CHANNELS = {"Store", "Web", "Phone"}
VALID_PAYMENTS = {"Cash", "Card", "Transfer", "DigitalWallet"}

@dataclass
class FileValidationResult:
    is_valid_schema: bool
    rejection_code: str | None
    rejection_detail: str | None

@dataclass
class RowValidationResult:
    is_valid: bool
    rejection_codes: list[str]
    rejection_details: list[str]

def validate_file_schema(headers: list[str]) -> FileValidationResult:
    if not headers:
        return FileValidationResult(False, "INVALID_FILE_SCHEMA", "File is empty or missing headers")
    
    if len(headers) != len(set(headers)):
        return FileValidationResult(False, "INVALID_FILE_SCHEMA", "Duplicate headers found")
        
    if headers != EXPECTED_HEADERS:
        missing = [h for h in EXPECTED_HEADERS if h not in headers]
        unknown = [h for h in headers if h not in EXPECTED_HEADERS]
        details = []
        if missing:
            details.append(f"Missing columns: {', '.join(missing)}")
        if unknown:
            details.append(f"Unknown columns: {', '.join(unknown)}")
        if headers != EXPECTED_HEADERS and not missing and not unknown:
            details.append("Columns are not in the expected order")
            
        return FileValidationResult(False, "INVALID_FILE_SCHEMA", "; ".join(details))
        
    return FileValidationResult(True, None, None)

def validate_row(row: dict[str, str]) -> RowValidationResult:
    codes = []
    details = []
    
    # Valores requeridos no vacíos
    for col in EXPECTED_HEADERS:
        val = str(row.get(col, "")).strip()
        if not val:
            # Evitamos agregar el mismo código repetidas veces si faltan varios
            if "MISSING_REQUIRED_VALUE" not in codes:
                codes.append("MISSING_REQUIRED_VALUE")
            details.append(f"Field {col} is empty")

    sale_id = str(row.get("sale_id", "")).strip()
    if sale_id:
        try:
            val = uuid.UUID(sale_id, version=4)
            if str(val) != sale_id:
                codes.append("INVALID_SALE_ID")
                details.append("sale_id is not a valid UUIDv4 string")
        except ValueError:
            codes.append("INVALID_SALE_ID")
            details.append("sale_id is not a valid UUID format")
            
    sale_date = str(row.get("sale_date", "")).strip()
    if sale_date:
        try:
            datetime.strptime(sale_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            codes.append("INVALID_DATE")
            details.append(f"sale_date '{sale_date}' does not match YYYY-MM-DD")
            
    sale_time = str(row.get("sale_time", "")).strip()
    if sale_time:
        try:
            datetime.strptime(sale_time, "%H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            codes.append("INVALID_TIME")
            details.append(f"sale_time '{sale_time}' does not match HH:MM:SS")
            
    branch_id = str(row.get("branch_id", "")).strip()
    if branch_id and not re.match(r'^BR-0[1-6]$', branch_id):
        codes.append("INVALID_BRANCH")
        details.append(f"branch_id '{branch_id}' not in catalog")

    customer_id = str(row.get("customer_id", "")).strip()
    if customer_id and not (customer_id.startswith("C-") and customer_id[2:].isdigit() and 1 <= int(customer_id[2:]) <= 500):
        codes.append("INVALID_CUSTOMER")
        details.append(f"customer_id '{customer_id}' not in catalog")
            
    product_id = str(row.get("product_id", "")).strip()
    if product_id and not (product_id.startswith("P-") and product_id[2:].isdigit() and 1 <= int(product_id[2:]) <= 80):
        codes.append("INVALID_PRODUCT")
        details.append(f"product_id '{product_id}' not in catalog")
            
    seller_id = str(row.get("seller_id", "")).strip()
    if seller_id and not (seller_id.startswith("S-") and seller_id[2:].isdigit() and 1 <= int(seller_id[2:]) <= 18):
        codes.append("INVALID_SELLER")
        details.append(f"seller_id '{seller_id}' not in catalog")
            
    channel = str(row.get("sales_channel", "")).strip()
    if channel and channel not in VALID_CHANNELS:
        codes.append("INVALID_CHANNEL")
        details.append(f"sales_channel '{channel}' is not allowed")
        
    payment = str(row.get("payment_method", "")).strip()
    if payment and payment not in VALID_PAYMENTS:
        codes.append("INVALID_PAYMENT_METHOD")
        details.append(f"payment_method '{payment}' is not allowed")
        
    qty_str = str(row.get("quantity", "")).strip()
    if qty_str:
        try:
            qty = int(qty_str)
            if qty <= 0:
                codes.append("INVALID_QUANTITY")
                details.append("quantity must be greater than 0")
        except ValueError:
            codes.append("INVALID_QUANTITY")
            details.append("quantity must be an integer")
            
    price_str = str(row.get("unit_price", "")).strip()
    if price_str:
        try:
            price = float(price_str)
            if price <= 0:
                codes.append("INVALID_UNIT_PRICE")
                details.append("unit_price must be greater than 0")
        except ValueError:
            codes.append("INVALID_UNIT_PRICE")
            details.append("unit_price must be a numeric value")
            
    disc_str = str(row.get("discount_pct", "")).strip()
    if disc_str:
        try:
            disc = float(disc_str)
            if not (0.0 <= disc <= 0.30):
                codes.append("INVALID_DISCOUNT")
                details.append("discount_pct must be between 0 and 0.30")
        except ValueError:
            codes.append("INVALID_DISCOUNT")
            details.append("discount_pct must be a numeric value")
            
    return RowValidationResult(
        is_valid=len(codes) == 0,
        rejection_codes=codes,
        rejection_details=details
    )
