import sqlite3
from pathlib import Path


def backup_database(source: Path, destination: Path) -> None:
    source = source.resolve(strict=True)
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as destination_connection:
        source_connection.backup(destination_connection)


def restore_database(backup: Path, destination: Path) -> None:
    backup = backup.resolve(strict=True)
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(backup) as source_connection, sqlite3.connect(destination) as destination_connection:
        source_connection.backup(destination_connection)

