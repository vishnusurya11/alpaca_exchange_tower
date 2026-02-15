"""
Shared pytest fixtures and utilities for all tests.
Provides common test data, mocks, and helper functions.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest


# ============================================================================
# Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def test_orders_dir(tmp_path):
    """Create temporary orders directory structure."""
    orders_dir = tmp_path / "orders"
    (orders_dir / "incoming").mkdir(parents=True)
    (orders_dir / "processing").mkdir(parents=True)
    (orders_dir / "completed").mkdir(parents=True)
    (orders_dir / "failed").mkdir(parents=True)
    return orders_dir


@pytest.fixture
def test_responses_dir(tmp_path):
    """Create temporary responses directory."""
    responses_dir = tmp_path / "responses"
    responses_dir.mkdir(parents=True)
    return responses_dir


@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    return data_dir


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables for testing."""
    test_env = {
        'ALPACA_PAPER_API_KEY': 'TEST_PAPER_KEY_12345',
        'ALPACA_PAPER_SECRET_KEY': 'TEST_PAPER_SECRET_67890',
        'ALPACA_LIVE_API_KEY': 'TEST_LIVE_KEY_ABCDE',
        'ALPACA_LIVE_SECRET_KEY': 'TEST_LIVE_SECRET_FGHIJ',
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    return test_env


# ============================================================================
# Timestamp Fixtures
# ============================================================================

@pytest.fixture
def fixed_timestamp():
    """Return a fixed timestamp for consistent testing."""
    return "20260214120000000000"


@pytest.fixture
def fixed_datetime():
    """Return a fixed datetime object."""
    return datetime(2026, 2, 14, 12, 0, 0, 0)


# ============================================================================
# Sample Order Data Fixtures
# ============================================================================

@pytest.fixture
def valid_stock_buy_payload():
    """Sample valid stock buy payload."""
    return {
        "symbol": "AAPL",
        "qty": 10,
        "order_class": "market",
        "time_in_force": "day"
    }


@pytest.fixture
def valid_stock_sell_payload():
    """Sample valid stock sell payload."""
    return {
        "symbol": "TSLA",
        "qty": 5,
        "order_class": "limit",
        "limit_price": 250.00,
        "time_in_force": "gtc"
    }


@pytest.fixture
def valid_crypto_buy_payload():
    """Sample valid crypto buy payload."""
    return {
        "symbol": "BTCUSD",
        "qty": 0.01,
        "order_class": "market",
        "time_in_force": "gtc"
    }


@pytest.fixture
def valid_option_single_payload():
    """Sample valid single-leg option payload."""
    return {
        "symbol": "AAPL250321C00150000",
        "qty": 1,
        "side": "buy",
        "order_class": "limit",
        "limit_price": 5.50,
        "time_in_force": "day"
    }


@pytest.fixture
def valid_option_multi_payload():
    """Sample valid multi-leg option payload."""
    return {
        "order_class": "mleg",
        "type": "limit",
        "limit_price": 2.00,
        "time_in_force": "day",
        "legs": [
            {
                "symbol": "AAPL250321C00150000",
                "side": "buy",
                "ratio_qty": 1
            },
            {
                "symbol": "AAPL250321C00155000",
                "side": "sell",
                "ratio_qty": 1
            }
        ]
    }


@pytest.fixture
def valid_positions_payload():
    """Sample valid positions query payload."""
    return {
        "asset_class": "us_equity"
    }


@pytest.fixture
def valid_order_status_payload():
    """Sample valid order status query payload."""
    return {
        "client_order_id": "testbot_20260214120000000000_stockbuy"
    }


# ============================================================================
# Complete Order Request Fixtures
# ============================================================================

@pytest.fixture
def valid_order_request(fixed_timestamp, valid_stock_buy_payload):
    """Sample complete valid order request."""
    return {
        "agent_id": "testbot",
        "client_order_id": f"testbot_{fixed_timestamp}_stockbuy",
        "order_type": "stockbuy",
        "mode": "paper",
        "payload": valid_stock_buy_payload
    }


@pytest.fixture
def create_order_file(temp_dir):
    """Factory fixture to create order JSON files."""
    def _create(filename: str, data: Dict[str, Any]) -> Path:
        """Create an order file with given filename and data."""
        file_path = temp_dir / filename
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return file_path
    return _create


# ============================================================================
# Mock Alpaca API Responses
# ============================================================================

@pytest.fixture
def mock_alpaca_order_response():
    """Mock successful Alpaca order response."""
    return {
        "id": "61e69015-8549-4bfd-b9c3-01e75843f47d",
        "client_order_id": "testbot_20260214120000000000_stockbuy",
        "created_at": "2026-02-14T12:00:01.000000Z",
        "updated_at": "2026-02-14T12:00:02.000000Z",
        "submitted_at": "2026-02-14T12:00:01.500000Z",
        "filled_at": "2026-02-14T12:00:02.000000Z",
        "canceled_at": None,
        "failed_at": None,
        "symbol": "AAPL",
        "asset_class": "us_equity",
        "qty": "10",
        "filled_qty": "10",
        "filled_avg_price": "150.00",
        "order_type": "market",
        "side": "buy",
        "time_in_force": "day",
        "limit_price": None,
        "stop_price": None,
        "status": "filled",
        "extended_hours": False
    }


@pytest.fixture
def mock_alpaca_account_response():
    """Mock Alpaca account information response."""
    return {
        "status": "ACTIVE",
        "buying_power": "100000.00",
        "cash": "100000.00",
        "portfolio_value": "100000.00",
        "equity": "100000.00",
        "last_equity": "99500.00",
        "long_market_value": "0.00",
        "short_market_value": "0.00"
    }


@pytest.fixture
def mock_alpaca_position_response():
    """Mock Alpaca position response."""
    return {
        "symbol": "AAPL",
        "qty": "10",
        "avg_entry_price": "149.75",
        "current_price": "150.00",
        "market_value": "1500.00",
        "unrealized_pl": "2.50",
        "unrealized_plpc": "0.0017",
        "side": "long",
        "asset_class": "us_equity"
    }


# ============================================================================
# Mock Alpaca Client Fixtures
# ============================================================================

@pytest.fixture
def mock_trading_client(mock_alpaca_order_response):
    """Mock Alpaca TradingClient."""
    mock_client = MagicMock()

    # Mock order object
    mock_order = MagicMock()
    for key, value in mock_alpaca_order_response.items():
        setattr(mock_order, key, value)

    mock_client.submit_order.return_value = mock_order
    mock_client.get_order_by_id.return_value = mock_order
    mock_client.get_order_by_client_id.return_value = mock_order
    mock_client.get_orders.return_value = [mock_order]

    # Mock account
    mock_account = MagicMock()
    mock_account.status = "ACTIVE"
    mock_account.buying_power = "100000.00"
    mock_account.cash = "100000.00"
    mock_account.portfolio_value = "100000.00"
    mock_account.equity = "100000.00"
    mock_client.get_account.return_value = mock_account

    # Mock positions
    mock_position = MagicMock()
    mock_position.symbol = "AAPL"
    mock_position.qty = "10"
    mock_position.avg_entry_price = "149.75"
    mock_position.current_price = "150.00"
    mock_position.market_value = "1500.00"
    mock_position.unrealized_pl = "2.50"
    mock_position.unrealized_plpc = "0.0017"
    mock_position.side = "long"
    mock_position.asset_class = "us_equity"
    mock_client.get_all_positions.return_value = [mock_position]

    return mock_client


# ============================================================================
# Filename Test Data
# ============================================================================

@pytest.fixture
def valid_filenames():
    """List of valid order filenames."""
    return [
        "paper_testbot_stockbuy_20260214120000000000.json",
        "live_sentiment_stocksell_20260214120100000000.json",
        "paper_crypto1_cryptobuy_20260214120200000000.json",
        "live_option99_optionsingle_20260214120300000000.json",
        "paper_riskbot_positions_20260214120400000000.json",
        "live_monitor_openorders_20260214120500000000.json",
    ]


@pytest.fixture
def invalid_filenames():
    """List of invalid order filenames for testing validation."""
    return [
        "PAPER_testbot_stockbuy_20260214120000000000.json",  # Uppercase mode
        "paper_TestBot_stockbuy_20260214120000000000.json",  # Uppercase agent
        "paper_test_bot_stockbuy_20260214120000000000.json",  # Underscore in agent
        "paper_testbot_stock_buy_20260214120000000000.json",  # Underscore in order type
        "paper_testbot_stockbuy_2026021412.json",  # Short timestamp
        "paper_testbot_invalidtype_20260214120000000000.json",  # Invalid order type
        "paper_testbot_stockbuy.json",  # Missing timestamp
        "testbot_stockbuy_20260214120000000000.json",  # Missing mode
        "paper_testbot_stockbuy_20260214120000000000.txt",  # Wrong extension
    ]


# ============================================================================
# Helper Functions
# ============================================================================

def create_sample_order_file(directory: Path, filename: str, order_data: Dict[str, Any]) -> Path:
    """
    Helper function to create a sample order file.

    Args:
        directory: Directory to create file in
        filename: Name of the file
        order_data: Order data to write

    Returns:
        Path to created file
    """
    file_path = directory / filename
    with open(file_path, 'w') as f:
        json.dump(order_data, f, indent=2)
    return file_path


@pytest.fixture
def sample_order_factory(temp_dir):
    """Factory to create sample order files."""
    def _factory(filename: str, order_data: Dict[str, Any]) -> Path:
        return create_sample_order_file(temp_dir, filename, order_data)
    return _factory
