from __future__ import annotations

from app.db.database import initialize_database


def main() -> None:
    path = initialize_database()
    print(f"PhytoScan SQLite database is ready: {path}")


if __name__ == "__main__":
    main()
