"""
Configuration module for Investment Analyzer.

This module provides:
- Global settings (settings.py)
- User configuration management (users.py)
- Configuration validation

Usage:
    from config import settings, get_users_config

    # Access global settings
    db_url = settings.database.url
    chart_dir = settings.chart.output_dir

    # Access user configuration
    users_config = get_users_config()
    user = users_config.get_user("dyson")
"""

from .settings import (
    ChartSettings,
    DatabaseSettings,
    FutuSettings,
    KlineSettings,
    ReportSettings,
    Settings,
    get_futu_password,
    get_proxy_settings,
    settings,
)
from .users import (
    ConfigurationError,
    OpenDConfig,
    UserConfig,
    UsersConfig,
    get_users_config,
    load_users_config,
    reload_users_config,
    validate_all_users,
    validate_user_config,
)

__all__ = [
    # Settings classes
    "Settings",
    "DatabaseSettings",
    "FutuSettings",
    "KlineSettings",
    "ChartSettings",
    "ReportSettings",
    # Settings instance
    "settings",
    # Settings functions
    "get_futu_password",
    "get_proxy_settings",
    # User config classes
    "ConfigurationError",
    "OpenDConfig",
    "UserConfig",
    "UsersConfig",
    # User config functions
    "get_users_config",
    "load_users_config",
    "reload_users_config",
    "validate_user_config",
    "validate_all_users",
]
