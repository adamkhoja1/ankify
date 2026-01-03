"""Shared dependencies for web routes."""

from typing import AsyncGenerator

from ..config import Config
from ..config.manager import ConfigManager
from ..storage.database import Database


def get_config() -> Config:
    """Dependency to get application configuration.

    Returns:
        Application config
    """
    manager = ConfigManager()
    return manager.load()


async def get_db() -> AsyncGenerator[Database, None]:
    """Dependency to get database connection.

    Yields:
        Connected database instance
    """
    config = get_config()
    db = Database(config.storage.database_path)
    await db.connect()
    try:
        yield db
    finally:
        await db.close()
