import os
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
    with psycopg.connect(normalize_database_url(raw_url)) as connection:
        for migration in sorted(migration_dir.glob("*.sql")):
            print(f"Applying {migration.name}", flush=True)
            connection.execute(migration.read_text(encoding="utf-8"))
        connection.commit()
    print("Database migrations completed", flush=True)


if __name__ == "__main__":
    main()
