import os
import time
from pathlib import Path

import psycopg


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def main() -> None:
    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url:
        raise RuntimeError("DATABASE_URL must be set before running migrations")
    migration_dir = Path(__file__).parent / "migrations"
    database_url = normalize_database_url(raw_url)
    last_error = None
    for attempt in range(1, 13):
        try:
            with psycopg.connect(database_url, connect_timeout=10) as connection:
                for migration in sorted(migration_dir.glob("*.sql")):
                    print(f"Applying {migration.name}", flush=True)
                    connection.execute(migration.read_text(encoding="utf-8"))
                connection.commit()
            print("Database migrations completed", flush=True)
            return
        except psycopg.OperationalError as error:
            last_error = error
            print(f"Database not ready (attempt {attempt}/12): {error}", flush=True)
            if attempt < 12:
                time.sleep(5)
    raise RuntimeError(f"Could not connect to DATABASE_URL after 12 attempts: {last_error}")


if __name__ == "__main__":
    main()
