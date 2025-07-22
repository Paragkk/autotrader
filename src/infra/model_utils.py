"""
Common data model utilities and converters
Extracted from broker-specific implementations
"""

import logging
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any, TypeVar

import pendulum

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ModelConversionError(Exception):
    """Error during model conversion"""


def safe_get_value(data_dict: dict, key: str, default: Any = None) -> Any:
    """Safely get value from dictionary"""
    return data_dict.get(key, default)


def parse_date_string(date_str: str) -> datetime:
    """
    Parse date string using pendulum for robust date handling

    Args:
        date_str: Date string in various formats

    Returns:
        datetime object

    Raises:
        ModelConversionError: If date parsing fails
    """
    if not date_str:
        return None

    try:
        # Use pendulum for robust date parsing
        parsed = pendulum.parse(date_str)
        return parsed.to_datetime_string()
    except Exception as e:
        logger.warning("Failed to parse date '%s': %s", date_str, e)
        msg = f"Invalid date format: {date_str}"
        raise ModelConversionError(msg) from e


def convert_to_type(value: Any, target_type: type) -> Any:
    """
    Convert value to target type with error handling

    Args:
        value: Value to convert
        target_type: Target type

    Returns:
        Converted value

    Raises:
        ModelConversionError: If conversion fails
    """
    if value is None:
        return None

    try:
        # Handle datetime conversion
        if target_type is datetime and isinstance(value, str):
            return parse_date_string(value)

        # Handle boolean conversion
        if target_type is bool:
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)

        # Handle list conversion
        if target_type is list or (hasattr(target_type, "__origin__") and target_type.__origin__ is list):
            if not isinstance(value, list):
                return [value] if value is not None else []
            return value

        # Handle numeric conversions
        if target_type in (int, float):
            if isinstance(value, str) and not value.strip():
                return 0
            return target_type(value)

        # Handle string conversion
        if target_type is str:
            return str(value) if value is not None else ""

        # Default conversion
        return target_type(value)

    except (ValueError, TypeError):
        logger.warning("Failed to convert '%s' to %s", value, target_type)
        # Return default value for the type
        return get_default_value(target_type)


def get_default_value(target_type: type) -> Any:
    """Get default value for a type"""
    defaults = {
        str: "",
        int: 0,
        float: 0.0,
        bool: False,
        list: [],
        dict: {},
        datetime: None,
    }
    return defaults.get(target_type)


def extract_dataclass_data(
    data_dict: dict[str, Any],
    dataclass_type: type[T],
    field_mappings: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Extract and convert data for dataclass creation

    Args:
        data_dict: Source data dictionary
        dataclass_type: Target dataclass type
        field_mappings: Optional field name mappings (source_key -> dataclass_field)

    Returns:
        Dictionary with converted data for dataclass creation

    Raises:
        ModelConversionError: If extraction fails
    """
    if not data_dict:
        msg = "Data dictionary is empty or None"
        raise ModelConversionError(msg)

    try:
        # Get dataclass fields and their types
        dataclass_fields = {f.name: f.type for f in fields(dataclass_type)}
        field_mappings = field_mappings or {}

        converted_data = {}

        for field_name, field_type in dataclass_fields.items():
            # Determine source key (use mapping if available)
            source_key = field_mappings.get(field_name, field_name)

            # Get value from source data
            raw_value = data_dict.get(source_key)

            # Convert value to target type
            converted_value = convert_to_type(raw_value, field_type)
            converted_data[field_name] = converted_value

        return converted_data

    except Exception as e:
        logger.exception("Failed to extract data for %s", dataclass_type.__name__)
        msg = f"Data extraction failed: {e}"
        raise ModelConversionError(msg) from e


def create_dataclass_from_dict(
    data_dict: dict[str, Any],
    dataclass_type: type[T],
    field_mappings: dict[str, str] | None = None,
    strict: bool = False,
) -> T:
    """
    Create dataclass instance from dictionary

    Args:
        data_dict: Source data dictionary
        dataclass_type: Target dataclass type
        field_mappings: Optional field name mappings
        strict: If True, raise error for missing required fields

    Returns:
        Dataclass instance

    Raises:
        ModelConversionError: If creation fails
    """
    try:
        converted_data = extract_dataclass_data(data_dict, dataclass_type, field_mappings)

        if strict:
            # Check for missing required fields (no default value)
            required_fields = [f.name for f in fields(dataclass_type) if f.default == dataclass.MISSING and f.default_factory == dataclass.MISSING]
            missing_fields = [f for f in required_fields if f not in data_dict and (not field_mappings or field_mappings.get(f) not in data_dict)]

            if missing_fields:
                msg = f"Missing required fields: {missing_fields}"
                raise ModelConversionError(msg)

        return dataclass_type(**converted_data)

    except Exception as e:
        logger.exception("Failed to create %s from dict", dataclass_type.__name__)
        msg = f"Failed to create {dataclass_type.__name__}: {e}"
        raise ModelConversionError(msg) from e


def convert_dict_list_to_dataclass_list(
    dict_list: list[dict[str, Any]],
    dataclass_type: type[T],
    field_mappings: dict[str, str] | None = None,
) -> list[T]:
    """
    Convert list of dictionaries to list of dataclass instances

    Args:
        dict_list: List of source dictionaries
        dataclass_type: Target dataclass type
        field_mappings: Optional field name mappings

    Returns:
        List of dataclass instances
    """
    if not dict_list:
        return []

    converted_items = []
    for i, item_dict in enumerate(dict_list):
        try:
            converted_item = create_dataclass_from_dict(item_dict, dataclass_type, field_mappings)
            converted_items.append(converted_item)
        except ModelConversionError as e:
            logger.warning(
                "Failed to convert item %d to %s: %s",
                i,
                dataclass_type.__name__,
                e,
            )
            # Skip invalid items rather than failing the entire conversion
            continue

    return converted_items


def get_field_mappings(broker_name: str) -> dict[str, str]:
    """
    Get field mappings for converting broker-specific fields to standard format

    Args:
        broker_name: Name of the broker (e.g., 'alpaca')

    Returns:
        Dictionary mapping broker fields to standard fields
    """
    mappings = {
        "alpaca": {
            # Order response mappings
            "id": "order_id",
            "qty": "quantity",
            "filled_qty": "filled_qty",
            "filled_avg_price": "avg_fill_price",
            # Position mappings
            "market_value": "market_value",
            "cost_basis": "cost_basis",
            "unrealized_pl": "unrealized_pl",
            "unrealized_plpc": "unrealized_pl_percent",
            "current_price": "current_price",
            "avg_entry_price": "entry_price",
            # Account mappings
            "portfolio_value": "portfolio_value",
            "buying_power": "buying_power",
            "daytrading_buying_power": "day_trading_power",
            "pattern_day_trader": "pattern_day_trader",
            "daytrade_count": "day_trade_count",
            "account_blocked": "account_status",
            "currency": "currency",
        }
    }

    return mappings.get(broker_name, {})


def get_order_type_mappings(broker_name: str) -> dict[str, str]:
    """
    Get order type mappings for converting between broker-specific and standard formats

    Args:
        broker_name: Name of the broker (e.g., 'alpaca')

    Returns:
        Dictionary mapping standard order types to broker-specific formats
    """
    # Standard order type mappings used by most brokers
    standard_mappings = {
        "market": "market",
        "limit": "limit",
        "stop": "stop",
        "stop_limit": "stop_limit",
        "trailing_stop": "trailing_stop",
    }

    # Broker-specific overrides
    broker_mappings = {
        "alpaca": standard_mappings,  # Alpaca uses standard naming
        # Add other brokers here as needed
    }

    return broker_mappings.get(broker_name, standard_mappings)


def get_status_mappings(broker_name: str) -> dict[str, str]:
    """
    Get status mappings for converting broker-specific statuses to standard format

    Args:
        broker_name: Name of the broker (e.g., 'alpaca')

    Returns:
        Dictionary mapping broker-specific statuses to standard status format
    """
    # Standard status mappings used by most brokers
    standard_mappings = {
        "new": "NEW",
        "partially_filled": "PARTIALLY_FILLED",
        "filled": "FILLED",
        "done_for_day": "DONE_FOR_DAY",
        "canceled": "CANCELED",
        "expired": "EXPIRED",
        "replaced": "REPLACED",
        "pending_cancel": "PENDING_CANCEL",
        "pending_replace": "PENDING_REPLACE",
        "pending_review": "PENDING_REVIEW",
        "rejected": "REJECTED",
        "suspended": "SUSPENDED",
        "pending_new": "PENDING_NEW",
    }

    # Broker-specific status mappings
    broker_mappings = {
        "alpaca": standard_mappings,  # Alpaca uses standard naming
        # Add other brokers here as needed with their specific status strings
    }

    return broker_mappings.get(broker_name, standard_mappings)


def get_reverse_status_mappings(broker_name: str) -> dict[str, str]:
    """
    Get reverse status mappings for converting standard statuses to
    broker-specific format

    Args:
        broker_name: Name of the broker (e.g., 'alpaca')

    Returns:
        Dictionary mapping standard statuses to broker-specific formats
    """
    status_mappings = get_status_mappings(broker_name)
    return {v.lower(): k for k, v in status_mappings.items()}
