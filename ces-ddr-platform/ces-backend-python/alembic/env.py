from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.migration_config import MigrationDatabaseUrl


class AlembicEnvironment:
    def __init__(self) -> None:
        self.config = context.config
        self.database = MigrationDatabaseUrl()
        self.target_metadata = None

    def database_url(self) -> str:
        return self.database.sqlalchemy_url()

    def configure(self) -> None:
        if self.config.config_file_name is not None:
            fileConfig(self.config.config_file_name)
        self.config.set_main_option("sqlalchemy.url", self.database.escaped_sqlalchemy_url())

    def run_offline(self) -> None:
        context.configure(
            url=self.database_url(),
            target_metadata=self.target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )

        with context.begin_transaction():
            context.run_migrations()

    def run_online(self) -> None:
        connectable = engine_from_config(
            self.config.get_section(self.config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=self.target_metadata)

            with context.begin_transaction():
                context.run_migrations()

    def run(self) -> None:
        self.configure()
        if context.is_offline_mode():
            self.run_offline()
            return
        self.run_online()


AlembicEnvironment().run()
