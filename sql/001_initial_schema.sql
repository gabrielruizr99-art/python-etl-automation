-- Crear esquemas
CREATE SCHEMA IF NOT EXISTS etl;
CREATE SCHEMA IF NOT EXISTS warehouse;

-- Tabla de control de ejecuciones (runs)
CREATE TABLE IF NOT EXISTS etl.pipeline_runs (
    run_id UUID PRIMARY KEY,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    files_discovered INT NOT NULL DEFAULT 0,
    files_processed INT NOT NULL DEFAULT 0,
    files_rejected INT NOT NULL DEFAULT 0,
    duplicate_files INT NOT NULL DEFAULT 0,
    valid_rows INT NOT NULL DEFAULT 0,
    rejected_rows INT NOT NULL DEFAULT 0,
    error_message TEXT
);

-- Tabla de registro de archivos procesados
CREATE TABLE IF NOT EXISTS etl.file_registry (
    file_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES etl.pipeline_runs(run_id),
    file_name VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE, -- Garantiza la idempotencia por archivo
    file_size_bytes BIGINT NOT NULL,
    row_count INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    discovered_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_file_registry_hash ON etl.file_registry(file_hash);
CREATE INDEX IF NOT EXISTS idx_file_registry_status ON etl.file_registry(status);

-- Tabla de registros rechazados
CREATE TABLE IF NOT EXISTS etl.rejected_records (
    rejection_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES etl.pipeline_runs(run_id),
    file_id UUID NOT NULL REFERENCES etl.file_registry(file_id),
    row_number INT NOT NULL,
    reason_code VARCHAR(100) NOT NULL,
    reason_detail TEXT,
    raw_data JSONB NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabla principal de ventas en el Data Warehouse
CREATE TABLE IF NOT EXISTS warehouse.sales (
    sale_id UUID PRIMARY KEY,
    sale_date DATE NOT NULL,
    sale_time TIME NOT NULL,
    branch_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    seller_id VARCHAR(50) NOT NULL,
    sales_channel VARCHAR(50) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0),
    discount_pct NUMERIC(4, 2) NOT NULL CHECK (discount_pct >= 0 AND discount_pct <= 0.30),
    gross_amount NUMERIC(12, 2) NOT NULL CHECK (gross_amount >= 0),
    discount_amount NUMERIC(12, 2) NOT NULL CHECK (discount_amount >= 0),
    net_amount NUMERIC(12, 2) NOT NULL CHECK (net_amount >= 0),
    source_file VARCHAR(255) NOT NULL,
    source_hash VARCHAR(64) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sales_date ON warehouse.sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_branch ON warehouse.sales(branch_id);
CREATE INDEX IF NOT EXISTS idx_sales_product ON warehouse.sales(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_source_hash ON warehouse.sales(source_hash);
