import sys
from pathlib import Path

import psycopg
from psycopg import sql
from pydantic import ValidationError

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.etl.config import get_settings


def main():
    try:
        settings = get_settings()
    except ValidationError as e:
        print("Configuration error. Please check your .env variables.")
        print(e)
        sys.exit(1)
        
    admin_info = settings.get_psycopg_admin_connection_info()
    
    try:
        # Usamos autocommit porque CREATE DATABASE no puede correr en un bloque de transacción
        with psycopg.connect(**admin_info, autocommit=True) as conn, conn.cursor() as cur:
            # Comprobar existencia
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (settings.db_name,)
                )
                exists = cur.fetchone()
                
                if not exists:
                    # Uso seguro de identificadores con psycopg.sql
                    query = sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(settings.db_name)
                    )
                    cur.execute(query)
                    print(f"Database '{settings.db_name}' created successfully.")
                else:
                    print(f"Database '{settings.db_name}' already exists. Skipping creation.")
    except Exception as e:  # noqa: BLE001
        print(f"Error checking or creating database: {e}")
        sys.exit(1)
        
    # Conectarse a la nueva base y aplicar esquema
    db_info = settings.get_psycopg_connection_info()
    sql_dir = ROOT_DIR / "sql"
    sql_files = sorted(sql_dir.glob("*.sql"))
    
    try:
        with psycopg.connect(**db_info) as conn, conn.cursor() as cur:
            for schema_path in sql_files:
                with schema_path.open("r", encoding="utf-8") as f:
                    schema_sql = f.read()
                    cur.execute(schema_sql)
                print(f"Schema {schema_path.name} applied successfully.")
    except Exception as e:  # noqa: BLE001
        print(f"Error applying schema: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
