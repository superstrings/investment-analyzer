"""
Global settings for Investment Analyzer.

Configuration is loaded from environment variables and defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


@dataclass
class DatabaseSettings:
    """Database configuration."""

    url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://localhost:5432/investment_db"
        )
    )
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = field(
        default_factory=lambda: os.getenv("DB_ECHO", "").lower() == "true"
    )


@dataclass
class FutuSettings:
    """Futu OpenD configuration."""

    default_host: str = "127.0.0.1"
    default_port: int = 11111
    connection_timeout: int = 30
    request_timeout: int = 30


@dataclass
class KlineSettings:
    """K-line data configuration."""

    default_days: int = 250
    cache_hours: int = 4
    markets: tuple = ("HK", "US", "A")


@dataclass
class ChartSettings:
    """Chart generation configuration."""

    output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "charts" / "output")
    dpi: int = 150
    style: str = "yahoo"
    figsize: tuple = (12, 8)
    volume: bool = True
    mav: tuple = (5, 10, 20, 60)


@dataclass
class ReportSettings:
    """Report generation configuration."""

    output_dir: Path = field(
        default_factory=lambda: PROJECT_ROOT / "reports" / "output"
    )
    template_dir: Path = field(
        default_factory=lambda: PROJECT_ROOT / "reports" / "templates"
    )
    date_format: str = "%Y-%m-%d"


@dataclass
class Settings:
    """Main settings container."""

    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    futu: FutuSettings = field(default_factory=FutuSettings)
    kline: KlineSettings = field(default_factory=KlineSettings)
    chart: ChartSettings = field(default_factory=ChartSettings)
    report: ReportSettings = field(default_factory=ReportSettings)

    # Project paths
    project_root: Path = PROJECT_ROOT
    config_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "config")
    users_config_path: Path = field(
        default_factory=lambda: PROJECT_ROOT / "config" / "users.yaml"
    )

    def ensure_directories(self) -> None:
        """Ensure all output directories exist."""
        self.chart.output_dir.mkdir(parents=True, exist_ok=True)
        self.report.output_dir.mkdir(parents=True, exist_ok=True)
        self.report.template_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()


def get_futu_password(username: str) -> Optional[str]:
    """
    Get Futu trade password for a user from environment variable.

    Environment variable format: FUTU_PWD_{USERNAME} (uppercase)

    Args:
        username: The username to get password for

    Returns:
        The trade password or None if not set
    """
    env_key = f"FUTU_PWD_{username.upper()}"
    return os.getenv(env_key)


def get_proxy_settings() -> dict:
    """
    Get proxy settings from environment variables.

    Returns:
        Dict with http and https proxy settings
    """
    return {
        "http": os.getenv("HTTP_PROXY"),
        "https": os.getenv("HTTPS_PROXY"),
    }
