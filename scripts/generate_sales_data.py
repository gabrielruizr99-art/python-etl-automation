import csv
import random
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configuración
SEED = 42
NUM_DAYS = 30
ROWS_PER_DAY = 400
START_DATE = datetime(2026, 4, 1, tzinfo=timezone.utc)


# Rutas
ROOT_DIR = Path(__file__).resolve().parent.parent
INCOMING_DIR = ROOT_DIR / "data" / "incoming"
SAMPLE_DIR = ROOT_DIR / "data" / "sample"

# Dimensiones
BRANCHES = [f"BR-{i:02d}" for i in range(1, 7)]
CUSTOMERS = [f"C-{i:04d}" for i in range(1, 501)]
SELLERS = [f"S-{i:02d}" for i in range(1, 19)]
CHANNELS = ["Store", "Web", "Phone"]
PAYMENTS = ["Cash", "Card", "Transfer", "DigitalWallet"]
COLUMNS = [
    "sale_id", "sale_date", "sale_time", "branch_id",
    "customer_id", "product_id", "seller_id", "sales_channel",
    "payment_method", "quantity", "unit_price", "discount_pct"
]

def clean_directories():
    for f in INCOMING_DIR.glob("sales_*.csv"):
        f.unlink()
    for f in SAMPLE_DIR.glob("sales_*.csv"):
        f.unlink()

def get_deterministic_uuid():
    return str(uuid.UUID(int=random.getrandbits(128), version=4))

def generate_row(current_date, products):
    # Mayor actividad viernes (4) y sábado (5)
    is_weekend = current_date.weekday() in (4, 5)
    if is_weekend and random.random() < 0.7:
        hour = random.choice(list(range(10, 15)) + list(range(16, 21)))
    else:
        hour = random.randint(8, 21)
    
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    sale_time = f"{hour:02d}:{minute:02d}:{second:02d}"
    
    product_id = random.choice(list(products.keys()))
    quantity = random.randint(1, 5)
    
    # Descuentos ocasionales
    discount_pct = round(random.uniform(0.05, 0.30), 2) if random.random() < 0.2 else 0.0

    return {
        "sale_id": get_deterministic_uuid(),
        "sale_date": current_date.strftime("%Y-%m-%d"),
        "sale_time": sale_time,
        "branch_id": random.choice(BRANCHES),
        "customer_id": random.choice(CUSTOMERS),
        "product_id": product_id,
        "seller_id": random.choice(SELLERS),
        "sales_channel": random.choice(CHANNELS),
        "payment_method": random.choice(PAYMENTS),
        "quantity": quantity,
        "unit_price": products[product_id],
        "discount_pct": discount_pct
    }

def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

def main():
    random.seed(SEED)
    
    # Pre-generar productos para que los precios sean constantes
    products = {f"P-{i:04d}": round(random.uniform(5.0, 250.0), 2) for i in range(1, 81)}
    
    clean_directories()
    
    first_day_rows = []
    tenth_day_path = None
    
    # Generar archivos diarios normales
    for i in range(NUM_DAYS):
        current_date = START_DATE + timedelta(days=i)
        file_name = f"sales_{current_date.strftime('%Y%m%d')}.csv"
        file_path = INCOMING_DIR / file_name
        
        daily_rows = [generate_row(current_date, products) for _ in range(ROWS_PER_DAY)]
        write_csv(file_path, COLUMNS, daily_rows)
        
        if i == 0:
            first_day_rows = daily_rows
        if i == 9:
            tenth_day_path = file_path
            
    # 1. Retry file
    if tenth_day_path:
        shutil.copy2(tenth_day_path, INCOMING_DIR / "sales_20260410_retry.csv")
        
    # 2. Invalid rows
    invalid_rows = []
    base_invalid = generate_row(START_DATE, products)
    
    # sale_id duplicado
    dup_row = base_invalid.copy()
    invalid_rows.extend([base_invalid, dup_row])
    
    # sale_id vacío
    row_empty_id = generate_row(START_DATE, products)
    row_empty_id["sale_id"] = ""
    invalid_rows.append(row_empty_id)
    
    # fecha inválida
    row_inv_date = generate_row(START_DATE, products)
    row_inv_date["sale_date"] = "2026-15-40"
    invalid_rows.append(row_inv_date)
    
    # cantidad igual a cero
    row_zero_q = generate_row(START_DATE, products)
    row_zero_q["quantity"] = 0
    invalid_rows.append(row_zero_q)
    
    # cantidad negativa
    row_neg_q = generate_row(START_DATE, products)
    row_neg_q["quantity"] = -5
    invalid_rows.append(row_neg_q)
    
    # precio negativo
    row_neg_p = generate_row(START_DATE, products)
    row_neg_p["unit_price"] = -10.50
    invalid_rows.append(row_neg_p)
    
    # descuento mayor que 0.30
    row_high_d = generate_row(START_DATE, products)
    row_high_d["discount_pct"] = 0.50
    invalid_rows.append(row_high_d)
    
    # canal desconocido
    row_inv_c = generate_row(START_DATE, products)
    row_inv_c["sales_channel"] = "Pigeon"
    invalid_rows.append(row_inv_c)
    
    # medio de pago desconocido
    row_inv_pay = generate_row(START_DATE, products)
    row_inv_pay["payment_method"] = "Gold"
    invalid_rows.append(row_inv_pay)
    
    # producto inexistente
    row_inv_prod = generate_row(START_DATE, products)
    row_inv_prod["product_id"] = "P-9999"
    invalid_rows.append(row_inv_prod)
    
    # valor obligatorio vacío
    row_empty_val = generate_row(START_DATE, products)
    row_empty_val["branch_id"] = ""
    invalid_rows.append(row_empty_val)
    
    write_csv(INCOMING_DIR / "sales_invalid_rows.csv", COLUMNS, invalid_rows)
    
    # 3. Invalid schema
    invalid_schema_rows = [generate_row(START_DATE, products) for _ in range(5)]
    schema_cols = [c for c in COLUMNS if c != "customer_id"] + ["unknown_column"]
    for row in invalid_schema_rows:
        del row["customer_id"]
        row["unknown_column"] = "test"
    write_csv(INCOMING_DIR / "sales_invalid_schema.csv", schema_cols, invalid_schema_rows)
    
    # 4. Empty file
    write_csv(INCOMING_DIR / "sales_empty.csv", COLUMNS, [])
    
    # Muestras
    write_csv(SAMPLE_DIR / "sales_valid_sample.csv", COLUMNS, first_day_rows[:25])
    write_csv(SAMPLE_DIR / "sales_invalid_rows_sample.csv", COLUMNS, invalid_rows[:25])
    write_csv(SAMPLE_DIR / "sales_invalid_schema_sample.csv", schema_cols, invalid_schema_rows[:25])

if __name__ == "__main__":
    main()
