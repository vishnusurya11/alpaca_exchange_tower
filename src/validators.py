"""
Validation logic for order files and JSON schemas.
Validates filenames, JSON structure, and ensures consistency.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field, validator

# Allowed values for validation
ALLOWED_MODES = ["paper", "live"]
ALLOWED_ORDER_TYPES = [
    "stockbuy", "stocksell",
    "optionsingle", "optionmulti",
    "cryptobuy", "cryptosell",
    "marketdata", "orderstatus", "openorders", "allorders",
    "positions", "accountinfo", "cancelorder"
]

# Regex patterns
MODE_PATTERN = r"^(paper|live)$"
AGENT_ID_PATTERN = r"^[a-z0-9]{1,20}$"
ORDER_TYPE_PATTERN = r"^[a-z]+$"
TIMESTAMP_PATTERN = r"^\d{20}$"


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_filename(filename: str) -> Dict[str, str]:
    """
    Validate filename format and extract components.

    Expected format: {mode}_{agentid}_{ordertype}_{timestamp}.json

    Args:
        filename: The filename to validate

    Returns:
        Dict with keys: mode, agent_id, order_type, timestamp

    Raises:
        ValidationError: If filename is invalid
    """
    # Remove .json extension
    if not filename.endswith('.json'):
        raise ValidationError(f"Filename must end with .json: {filename}")

    base_name = filename[:-5]  # Remove '.json'

    # Split by underscore
    parts = base_name.split('_')

    if len(parts) != 4:
        raise ValidationError(
            f"Filename must have exactly 4 parts separated by underscores. "
            f"Expected: {{mode}}_{{agentid}}_{{ordertype}}_{{timestamp}}.json, "
            f"Got: {filename}"
        )

    mode, agent_id, order_type, timestamp = parts

    # Validate mode
    if not re.match(MODE_PATTERN, mode):
        raise ValidationError(
            f"Invalid mode '{mode}'. Must be 'paper' or 'live' (lowercase)"
        )

    # Validate agent_id
    if not re.match(AGENT_ID_PATTERN, agent_id):
        raise ValidationError(
            f"Invalid agent_id '{agent_id}'. Must be lowercase alphanumeric (a-z, 0-9), "
            f"1-20 characters, no underscores or special characters"
        )

    # Validate order_type
    if order_type not in ALLOWED_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order_type '{order_type}'. Must be one of: {', '.join(ALLOWED_ORDER_TYPES)}"
        )

    # Validate timestamp format
    if not re.match(TIMESTAMP_PATTERN, timestamp):
        raise ValidationError(
            f"Invalid timestamp '{timestamp}'. Must be exactly 20 digits (YYYYMMDDHHMMSSffffff)"
        )

    # Try to parse timestamp
    try:
        dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S%f')
    except ValueError as e:
        raise ValidationError(f"Invalid timestamp format '{timestamp}': {e}")

    return {
        "mode": mode,
        "agent_id": agent_id,
        "order_type": order_type,
        "timestamp": timestamp,
        "parsed_datetime": dt
    }


# Pydantic models for JSON validation

class StockOrderPayload(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    qty: float = Field(..., gt=0)
    order_class: str = Field(..., pattern="^(market|limit|stop|stop_limit)$")
    limit_price: Optional[float] = Field(None, gt=0)
    stop_price: Optional[float] = Field(None, gt=0)
    time_in_force: str = Field(..., pattern="^(day|gtc|ioc|fok)$")


class OptionSinglePayload(BaseModel):
    symbol: str = Field(..., min_length=1)  # OCC format
    qty: int = Field(..., gt=0)
    side: str = Field(..., pattern="^(buy|sell)$")
    order_class: str = Field(..., pattern="^(market|limit)$")
    limit_price: Optional[float] = Field(None, gt=0)
    time_in_force: str = Field(..., pattern="^(day|gtc|ioc|fok)$")


class OptionLeg(BaseModel):
    symbol: str
    side: str = Field(..., pattern="^(buy|sell)$")
    ratio_qty: int = Field(..., gt=0)


class OptionMultiPayload(BaseModel):
    order_class: str = Field(..., pattern="^mleg$")
    type: str = Field(..., pattern="^limit$")
    limit_price: float = Field(..., gt=0)
    time_in_force: str = Field(..., pattern="^(day|gtc|ioc|fok)$")
    legs: list[OptionLeg] = Field(..., min_items=2)


class CryptoOrderPayload(BaseModel):
    symbol: str = Field(..., pattern="^[A-Z]+USD$")  # e.g., BTCUSD
    qty: float = Field(..., gt=0)
    order_class: str = Field(..., pattern="^(market|limit)$")
    limit_price: Optional[float] = Field(None, gt=0)
    time_in_force: str = Field(..., pattern="^(day|gtc|ioc|fok)$")


class MarketDataPayload(BaseModel):
    symbols: list[str] = Field(..., min_items=1)
    data_type: str = Field(..., pattern="^(quote|bar|trade)$")


class OrderStatusPayload(BaseModel):
    alpaca_order_id: Optional[str] = None
    client_order_id: Optional[str] = None


class OpenOrdersPayload(BaseModel):
    status: Optional[str] = Field("open", pattern="^(open|closed|all)$")
    limit: Optional[int] = Field(100, gt=0, le=500)
    symbols: Optional[list[str]] = None


class AllOrdersPayload(BaseModel):
    status: Optional[str] = Field("all", pattern="^(open|closed|all)$")
    limit: Optional[int] = Field(100, gt=0, le=500)
    after: Optional[str] = None  # ISO 8601
    until: Optional[str] = None  # ISO 8601
    direction: Optional[str] = Field("desc", pattern="^(asc|desc)$")


class PositionsPayload(BaseModel):
    asset_class: Optional[str] = Field(None, pattern="^(us_equity|us_option|crypto)$")


class AccountInfoPayload(BaseModel):
    pass  # No payload needed


class CancelOrderPayload(BaseModel):
    alpaca_order_id: Optional[str] = None
    client_order_id: Optional[str] = None


class OrderRequest(BaseModel):
    agent_id: str = Field(..., pattern=AGENT_ID_PATTERN)
    client_order_id: str
    order_type: str
    mode: str = Field(..., pattern=MODE_PATTERN)
    payload: Dict[str, Any]

    @validator('order_type')
    def validate_order_type(cls, v):
        if v not in ALLOWED_ORDER_TYPES:
            raise ValueError(f"order_type must be one of: {', '.join(ALLOWED_ORDER_TYPES)}")
        return v


def validate_json_order(data: Dict[str, Any], filename_parts: Dict[str, str]) -> OrderRequest:
    """
    Validate JSON order data and ensure it matches filename.

    Args:
        data: The parsed JSON data
        filename_parts: Parsed filename components

    Returns:
        Validated OrderRequest object

    Raises:
        ValidationError: If JSON is invalid or doesn't match filename
    """
    # Basic structure validation
    try:
        order = OrderRequest(**data)
    except Exception as e:
        raise ValidationError(f"Invalid JSON structure: {e}")

    # Check mode matches filename
    if order.mode != filename_parts['mode']:
        raise ValidationError(
            f"Mode mismatch: filename has '{filename_parts['mode']}', "
            f"JSON has '{order.mode}'"
        )

    # Check agent_id matches filename
    if order.agent_id != filename_parts['agent_id']:
        raise ValidationError(
            f"Agent ID mismatch: filename has '{filename_parts['agent_id']}', "
            f"JSON has '{order.agent_id}'"
        )

    # Check order_type matches filename
    if order.order_type != filename_parts['order_type']:
        raise ValidationError(
            f"Order type mismatch: filename has '{filename_parts['order_type']}', "
            f"JSON has '{order.order_type}'"
        )

    # Validate payload based on order type
    try:
        if order.order_type in ['stockbuy', 'stocksell']:
            StockOrderPayload(**order.payload)
        elif order.order_type == 'optionsingle':
            OptionSinglePayload(**order.payload)
        elif order.order_type == 'optionmulti':
            OptionMultiPayload(**order.payload)
        elif order.order_type in ['cryptobuy', 'cryptosell']:
            CryptoOrderPayload(**order.payload)
        elif order.order_type == 'marketdata':
            MarketDataPayload(**order.payload)
        elif order.order_type == 'orderstatus':
            payload = OrderStatusPayload(**order.payload)
            if not payload.alpaca_order_id and not payload.client_order_id:
                raise ValueError("Must provide either alpaca_order_id or client_order_id")
        elif order.order_type == 'openorders':
            OpenOrdersPayload(**order.payload)
        elif order.order_type == 'allorders':
            AllOrdersPayload(**order.payload)
        elif order.order_type == 'positions':
            PositionsPayload(**order.payload)
        elif order.order_type == 'accountinfo':
            AccountInfoPayload(**order.payload)
        elif order.order_type == 'cancelorder':
            payload = CancelOrderPayload(**order.payload)
            if not payload.alpaca_order_id and not payload.client_order_id:
                raise ValueError("Must provide either alpaca_order_id or client_order_id")
    except Exception as e:
        raise ValidationError(f"Invalid payload for {order.order_type}: {e}")

    return order


def validate_order_file(file_path: Path) -> Tuple[Dict[str, str], OrderRequest]:
    """
    Complete validation of an order file (filename + JSON content).

    Args:
        file_path: Path to the order file

    Returns:
        Tuple of (filename_parts, validated_order)

    Raises:
        ValidationError: If validation fails
    """
    import json

    # Validate filename
    filename = file_path.name
    filename_parts = validate_filename(filename)

    # Load and validate JSON
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")
    except Exception as e:
        raise ValidationError(f"Failed to read file: {e}")

    # Validate JSON structure and cross-check with filename
    validated_order = validate_json_order(data, filename_parts)

    return filename_parts, validated_order
