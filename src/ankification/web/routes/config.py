"""Configuration API routes."""

from typing import Any

from fastapi import APIRouter, Depends

from ...config import Config
from ...config.manager import ConfigManager

router = APIRouter(prefix="/api/config", tags=["config"])


def get_config_manager() -> ConfigManager:
    """Dependency to get config manager."""
    return ConfigManager()


@router.get("", response_model=dict[str, Any])
async def get_config(manager: ConfigManager = Depends(get_config_manager)) -> dict[str, Any]:
    """Get current configuration.

    Args:
        manager: Config manager

    Returns:
        Current configuration as dict
    """
    config = manager.load()
    return config.model_dump()


@router.put("", response_model=dict[str, Any])
async def update_config(
    updates: dict[str, Any], manager: ConfigManager = Depends(get_config_manager)
) -> dict[str, Any]:
    """Update configuration.

    Args:
        updates: Configuration updates
        manager: Config manager

    Returns:
        Updated configuration
    """
    # Load current config
    config = manager.load()

    # Apply updates (simplified - in production would validate each field)
    config_dict = config.model_dump()
    config_dict.update(updates)

    # Create new config and save
    new_config = Config(**config_dict)
    manager.save(new_config)

    return new_config.model_dump()


@router.get("/tags", response_model=list[str])
async def get_tags(manager: ConfigManager = Depends(get_config_manager)) -> list[str]:
    """Get available tags from config.

    Args:
        manager: Config manager

    Returns:
        List of available tags
    """
    config = manager.load()
    return config.tags.pools
