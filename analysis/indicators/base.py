"""
Base classes for technical indicators.

Provides common functionality for all indicator calculations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Union

import numpy as np
import pandas as pd


@dataclass
class IndicatorResult:
    """Result of an indicator calculation."""

    name: str
    values: Union[pd.Series, pd.DataFrame]
    params: dict = field(default_factory=dict)

    @property
    def is_series(self) -> bool:
        """Check if result is a single series."""
        return isinstance(self.values, pd.Series)

    @property
    def is_dataframe(self) -> bool:
        """Check if result is a DataFrame (multiple columns)."""
        return isinstance(self.values, pd.DataFrame)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        if self.is_series:
            return {self.name: self.values}
        else:
            return {col: self.values[col] for col in self.values.columns}


class BaseIndicator(ABC):
    """
    Abstract base class for technical indicators.

    All indicators should inherit from this class and implement
    the calculate method.
    """

    name: str = "base"

    @abstractmethod
    def calculate(
        self,
        df: pd.DataFrame,
        **kwargs,
    ) -> IndicatorResult:
        """
        Calculate the indicator.

        Args:
            df: DataFrame with OHLCV data
            **kwargs: Additional parameters

        Returns:
            IndicatorResult with calculated values
        """
        pass

    def _validate_dataframe(
        self,
        df: pd.DataFrame,
        required_columns: list[str],
    ) -> None:
        """
        Validate DataFrame has required columns.

        Args:
            df: DataFrame to validate
            required_columns: List of required column names

        Raises:
            ValueError: If required columns are missing
        """
        df_cols = set(df.columns.str.lower())
        missing = set(col.lower() for col in required_columns) - df_cols
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def _get_column(
        self,
        df: pd.DataFrame,
        column: str,
    ) -> pd.Series:
        """
        Get column from DataFrame (case-insensitive).

        Args:
            df: DataFrame
            column: Column name

        Returns:
            Column as Series
        """
        # Try exact match first
        if column in df.columns:
            return df[column]

        # Try lowercase
        col_lower = column.lower()
        for col in df.columns:
            if col.lower() == col_lower:
                return df[col]

        raise ValueError(f"Column '{column}' not found in DataFrame")


def validate_period(period: int, min_val: int = 1) -> None:
    """
    Validate period parameter.

    Args:
        period: Period value to validate
        min_val: Minimum allowed value

    Raises:
        ValueError: If period is invalid
    """
    if not isinstance(period, int) or period < min_val:
        raise ValueError(f"Period must be an integer >= {min_val}, got {period}")
