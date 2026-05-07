from app.config import AppSettings


class MigrationDatabaseUrl:
    def __init__(self, postgres_dsn: str | None = None) -> None:
        self.postgres_dsn = postgres_dsn or AppSettings().postgres_dsn

    def sqlalchemy_url(self) -> str:
        if self.postgres_dsn.startswith("postgresql+psycopg://"):
            return self.postgres_dsn
        if self.postgres_dsn.startswith("postgresql://"):
            return self.postgres_dsn.replace("postgresql://", "postgresql+psycopg://", 1)
        if self.postgres_dsn.startswith("postgres://"):
            return self.postgres_dsn.replace("postgres://", "postgresql+psycopg://", 1)
        return self.postgres_dsn

    def escaped_sqlalchemy_url(self) -> str:
        return self.sqlalchemy_url().replace("%", "%%")
