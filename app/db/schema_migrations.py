from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_sha256_hash_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "files" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("files")}
    if "sha256_hash" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE files ADD COLUMN sha256_hash VARCHAR(64)"))
