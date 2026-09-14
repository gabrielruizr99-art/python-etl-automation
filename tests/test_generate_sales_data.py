import csv
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from scripts.generate_sales_data import COLUMNS, INCOMING_DIR, SAMPLE_DIR, main


def test_generate_sales_data():
    # Ejecutamos el generador
    main()
    
    # Verificamos archivos diarios normales (ignorando retry)
    daily_files = list(INCOMING_DIR.glob("sales_202604*.csv"))
    normal_files = [f for f in daily_files if "retry" not in f.name]
    
    assert len(normal_files) == 30, "Debe haber 30 archivos diarios normales"
    
    total_normal_rows = 0
    for f in normal_files:
        with f.open("r", encoding="utf-8") as file:
            reader = list(csv.DictReader(file))
            assert len(reader) == 400, f"El archivo {f.name} no tiene 400 filas"
            total_normal_rows += 400
            
    assert total_normal_rows == 12000, "El total de filas normales debe ser 12000"
    
    # Verificamos columnas y formato básico
    first_file = normal_files[0]
    with first_file.open("r", encoding="utf-8") as file:
        reader = csv.reader(file)
        header = next(reader)
        assert header == COLUMNS, "Las columnas no coinciden con el esquema esperado"
        
    # Verificamos creación de casos especiales
    assert (INCOMING_DIR / "sales_20260410_retry.csv").exists(), "Falta archivo de reintento"
    assert (INCOMING_DIR / "sales_invalid_rows.csv").exists(), "Falta archivo de filas inválidas"
    assert (INCOMING_DIR / "sales_invalid_schema.csv").exists(), "Falta archivo de esquema inválido"
    assert (INCOMING_DIR / "sales_empty.csv").exists(), "Falta archivo vacío"
    
    # Verificamos tamaño de muestras
    samples = ["sales_valid_sample.csv", "sales_invalid_rows_sample.csv", "sales_invalid_schema_sample.csv"]
    for sample_name in samples:
        sample_path = SAMPLE_DIR / sample_name
        assert sample_path.exists(), f"Falta muestra {sample_name}"
        with sample_path.open("r", encoding="utf-8") as file:
            # Usar csv.reader normal para no depender del esquema, porque invalid_schema no tiene customer_id
            reader = list(csv.reader(file))
            # restando 1 para el header
            assert len(reader) - 1 <= 25, f"La muestra {sample_name} excede las 25 filas permitidas"
            
    # Verificamos ausencia de datos personales (solo códigos)
    with first_file.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        row = next(reader)
        assert row["customer_id"].startswith("C-")
        assert row["seller_id"].startswith("S-")
        assert row["branch_id"].startswith("BR-")
