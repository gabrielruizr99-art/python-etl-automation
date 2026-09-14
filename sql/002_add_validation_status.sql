DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_constraint 
        WHERE conname = 'chk_file_registry_status'
    ) THEN
        ALTER TABLE etl.file_registry 
        ADD CONSTRAINT chk_file_registry_status 
        CHECK (status IN ('discovered', 'processing', 'validated', 'processed', 'rejected', 'failed'));
    END IF;
END $$;
