from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

from backend.app.db.session import create_sqlite_engine


@pytest.fixture
def migrated_database(monkeypatch: pytest.MonkeyPatch):
    runtime_path = Path(__file__).parent / ".runtime" / uuid4().hex
    runtime_path.mkdir(parents=True)
    database_path = runtime_path / "test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    from backend.app.core.config import get_settings

    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    engine = create_sqlite_engine(database_url)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield database_path, engine, session_factory
    finally:
        engine.dispose()
        get_settings.cache_clear()
        shutil.rmtree(runtime_path, ignore_errors=True)
