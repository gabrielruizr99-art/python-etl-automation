from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = Field(alias="DB_HOST")
    db_port: int = Field(alias="DB_PORT")
    db_name: str = Field(alias="DB_NAME")
    db_user: str = Field(alias="DB_USER")
    db_password: SecretStr = Field(alias="DB_PASSWORD")
    db_admin_db: str = Field(alias="DB_ADMIN_DB", default="postgres")

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    def get_connection_string(self) -> str:
        """Get the connection string for the main ETL database."""
        # Using .get_secret_value() extracts the real password but keeps it out of logs/repr
        return f"postgresql://{self.db_user}:{self.db_password.get_secret_value()}@{self.db_host}:{self.db_port}/{self.db_name}"

    def get_admin_connection_string(self) -> str:
        """Get the connection string for the admin database (to create other DBs)."""
        return f"postgresql://{self.db_user}:{self.db_password.get_secret_value()}@{self.db_host}:{self.db_port}/{self.db_admin_db}"

    def get_psycopg_connection_info(self) -> dict:
        """Return dict for psycopg.connect(**info) without exposing it in a URL."""
        return {
            "host": self.db_host,
            "port": self.db_port,
            "dbname": self.db_name,
            "user": self.db_user,
            "password": self.db_password.get_secret_value()
        }
    
    def get_psycopg_admin_connection_info(self) -> dict:
        """Return dict for psycopg.connect(**info) to the admin DB."""
        return {
            "host": self.db_host,
            "port": self.db_port,
            "dbname": self.db_admin_db,
            "user": self.db_user,
            "password": self.db_password.get_secret_value()
        }

    def __repr__(self) -> str:
        """Ensure password is not printed if settings is printed directly."""
        return f"Settings(host='{self.db_host}', port={self.db_port}, name='{self.db_name}', user='{self.db_user}')"

def get_settings() -> Settings:
    """Helper function to load settings, useful for testing overrides."""
    return Settings()
