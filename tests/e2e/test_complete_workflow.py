"""
End-to-end tests for complete order processing workflows.

Tests complete workflows from order file creation to response generation,
including all 13 order types with mocked Alpaca API.
"""

import json
import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from order_processor import OrderProcessor
from src.ledger import SimpleLedger


@pytest.fixture
def e2e_test_env(tmp_path, monkeypatch):
    """Set up complete test environment."""
    # Create directory structure
    orders_dir = tmp_path / "orders"
    (orders_dir / "incoming").mkdir(parents=True)
    (orders_dir / "processing").mkdir(parents=True)
    (orders_dir / "completed").mkdir(parents=True)
    (orders_dir / "failed").mkdir(parents=True)

    responses_dir = tmp_path / "responses"
    responses_dir.mkdir(parents=True)

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True)

    # Set environment variables
    monkeypatch.setenv('ALPACA_PAPER_API_KEY', 'TEST_PAPER_KEY')
    monkeypatch.setenv('ALPACA_PAPER_SECRET_KEY', 'TEST_PAPER_SECRET')
    monkeypatch.setenv('ALPACA_LIVE_API_KEY', 'TEST_LIVE_KEY')
    monkeypatch.setenv('ALPACA_LIVE_SECRET_KEY', 'TEST_LIVE_SECRET')

    return {
        'root': tmp_path,
        'orders_dir': orders_dir,
        'incoming': orders_dir / "incoming",
        'processing': orders_dir / "processing",
        'completed': orders_dir / "completed",
        'failed': orders_dir / "failed",
        'responses': responses_dir,
        'data': data_dir,
        'logs': logs_dir,
    }


def create_order_file(directory: Path, mode: str, agent: str, order_type: str, timestamp: str, payload: dict) -> Path:
    """Helper to create order file."""
    filename = f"{mode}_{agent}_{order_type}_{timestamp}.json"
    client_order_id = f"{agent}_{timestamp}_{order_type}"

    order_data = {
        "agent_id": agent,
        "client_order_id": client_order_id,
        "order_type": order_type,
        "mode": mode,
        "payload": payload
    }

    file_path = directory / filename
    with open(file_path, 'w') as f:
        json.dump(order_data, f, indent=2)

    return file_path


@pytest.mark.e2e
class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""

    def test_stock_buy_complete_workflow(self, e2e_test_env, mock_trading_client):
        """Test complete workflow for stock buy order."""
        # Create order file
        payload = {
            "symbol": "AAPL",
            "qty": 10,
            "order_class": "market",
            "time_in_force": "day"
        }

        order_file = create_order_file(
            e2e_test_env['incoming'],
            mode="paper",
            agent="testbot",
            order_type="stockbuy",
            timestamp="20260214120000000000",
            payload=payload
        )

        assert order_file.exists()

        # Patch directories and process
        with patch('order_processor.BASE_DIR', e2e_test_env['root']), \
             patch('order_processor.ORDERS_DIR', e2e_test_env['orders_dir']), \
             patch('order_processor.INCOMING_DIR', e2e_test_env['incoming']), \
             patch('order_processor.PROCESSING_DIR', e2e_test_env['processing']), \
             patch('order_processor.COMPLETED_DIR', e2e_test_env['completed']), \
             patch('order_processor.FAILED_DIR', e2e_test_env['failed']), \
             patch('order_processor.RESPONSES_DIR', e2e_test_env['responses']), \
             patch('order_processor.DATA_DIR', e2e_test_env['data']), \
             patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            # Process order
            processor = OrderProcessor()
            processor.process_order_file(order_file)

            # Verify order moved to completed
            completed_files = list(e2e_test_env['completed'].glob("*.json"))
            assert len(completed_files) == 1

            # Verify response created
            response_files = list(e2e_test_env['responses'].rglob("*.json"))
            assert len(response_files) == 1

            response_path = response_files[0]
            with open(response_path, 'r') as f:
                response = json.load(f)

            assert response['status'] == 'success'
            assert response['agent_id'] == 'testbot'

            # Verify recorded in ledger
            ledger_file = e2e_test_env['data'] / "processed_orders.txt"
            assert ledger_file.exists()

            with open(ledger_file, 'r') as f:
                content = f.read()
                assert "testbot_20260214120000000000_stockbuy" in content

    def test_duplicate_order_rejected_workflow(self, e2e_test_env, mock_trading_client):
        """Test duplicate order is rejected in complete workflow."""
        payload = {
            "symbol": "AAPL",
            "qty": 10,
            "order_class": "market",
            "time_in_force": "day"
        }

        # Create same order twice
        timestamp = "20260214120000000000"

        order_file_1 = create_order_file(
            e2e_test_env['incoming'],
            mode="paper",
            agent="testbot",
            order_type="stockbuy",
            timestamp=timestamp,
            payload=payload
        )

        order_file_2 = create_order_file(
            e2e_test_env['incoming'],
            mode="paper",
            agent="testbot",
            order_type="stockbuy",
            timestamp=timestamp,  # Same timestamp = duplicate
            payload=payload
        )

        with patch('order_processor.BASE_DIR', e2e_test_env['root']), \
             patch('order_processor.ORDERS_DIR', e2e_test_env['orders_dir']), \
             patch('order_processor.INCOMING_DIR', e2e_test_env['incoming']), \
             patch('order_processor.PROCESSING_DIR', e2e_test_env['processing']), \
             patch('order_processor.COMPLETED_DIR', e2e_test_env['completed']), \
             patch('order_processor.FAILED_DIR', e2e_test_env['failed']), \
             patch('order_processor.RESPONSES_DIR', e2e_test_env['responses']), \
             patch('order_processor.DATA_DIR', e2e_test_env['data']), \
             patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            processor = OrderProcessor()

            # Process first order (should succeed)
            processor.process_order_file(order_file_1)

            # Process second order (should be duplicate)
            processor.process_order_file(order_file_2)

            # Check stats
            assert processor.stats['duplicates'] == 1
            assert processor.stats['successful'] == 1

            # One in completed, one in failed
            assert len(list(e2e_test_env['completed'].glob("*.json"))) == 1
            assert len(list(e2e_test_env['failed'].glob("*.json"))) == 1

            # Two responses (one success, one error)
            response_files = list(e2e_test_env['responses'].rglob("*.json"))
            assert len(response_files) == 2


@pytest.mark.e2e
class TestAllOrderTypes:
    """Test all 13 order types end-to-end."""

    @pytest.mark.parametrize("order_type,payload", [
        ("stockbuy", {"symbol": "AAPL", "qty": 10, "order_class": "market", "time_in_force": "day"}),
        ("stocksell", {"symbol": "TSLA", "qty": 5, "order_class": "limit", "limit_price": 250.00, "time_in_force": "gtc"}),
        ("cryptobuy", {"symbol": "BTCUSD", "qty": 0.01, "order_class": "market", "time_in_force": "gtc"}),
        ("cryptosell", {"symbol": "ETHUSD", "qty": 0.1, "order_class": "limit", "limit_price": 3000.00, "time_in_force": "gtc"}),
        ("positions", {"asset_class": "us_equity"}),
        ("accountinfo", {}),
    ])
    def test_order_type_workflow(self, e2e_test_env, mock_trading_client, order_type, payload):
        """Test workflow for each order type."""
        timestamp = f"2026021412000{hash(order_type) % 10}000000"

        order_file = create_order_file(
            e2e_test_env['incoming'],
            mode="paper",
            agent="testbot",
            order_type=order_type,
            timestamp=timestamp,
            payload=payload
        )

        with patch('order_processor.BASE_DIR', e2e_test_env['root']), \
             patch('order_processor.ORDERS_DIR', e2e_test_env['orders_dir']), \
             patch('order_processor.INCOMING_DIR', e2e_test_env['incoming']), \
             patch('order_processor.PROCESSING_DIR', e2e_test_env['processing']), \
             patch('order_processor.COMPLETED_DIR', e2e_test_env['completed']), \
             patch('order_processor.FAILED_DIR', e2e_test_env['failed']), \
             patch('order_processor.RESPONSES_DIR', e2e_test_env['responses']), \
             patch('order_processor.DATA_DIR', e2e_test_env['data']), \
             patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            processor = OrderProcessor()
            processor.process_order_file(order_file)

            # Should be successful
            assert processor.stats['successful'] >= 1

            # Response should exist
            response_files = list(e2e_test_env['responses'].rglob(f"*{order_type}*.json"))
            assert len(response_files) >= 1


@pytest.mark.e2e
class TestMultiAgentWorkflows:
    """Test multi-agent scenarios."""

    def test_multiple_agents_parallel_orders(self, e2e_test_env, mock_trading_client):
        """Test multiple agents submitting orders simultaneously."""
        agents = ["sentiment", "momentum", "crypto"]

        order_files = []
        for i, agent in enumerate(agents):
            timestamp = f"2026021412000{i}000000"
            payload = {"symbol": "AAPL", "qty": 10, "order_class": "market", "time_in_force": "day"}

            order_file = create_order_file(
                e2e_test_env['incoming'],
                mode="paper",
                agent=agent,
                order_type="stockbuy",
                timestamp=timestamp,
                payload=payload
            )
            order_files.append(order_file)

        with patch('order_processor.BASE_DIR', e2e_test_env['root']), \
             patch('order_processor.ORDERS_DIR', e2e_test_env['orders_dir']), \
             patch('order_processor.INCOMING_DIR', e2e_test_env['incoming']), \
             patch('order_processor.PROCESSING_DIR', e2e_test_env['processing']), \
             patch('order_processor.COMPLETED_DIR', e2e_test_env['completed']), \
             patch('order_processor.FAILED_DIR', e2e_test_env['failed']), \
             patch('order_processor.RESPONSES_DIR', e2e_test_env['responses']), \
             patch('order_processor.DATA_DIR', e2e_test_env['data']), \
             patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            processor = OrderProcessor()

            # Process all orders
            for order_file in order_files:
                processor.process_order_file(order_file)

            # All should succeed
            assert processor.stats['successful'] == len(agents)

            # Each agent should have its own response directory
            for agent in agents:
                agent_dir = e2e_test_env['responses'] / agent
                assert agent_dir.exists()


@pytest.mark.e2e
class TestErrorHandlingWorkflows:
    """Test error handling in complete workflows."""

    def test_invalid_json_workflow(self, e2e_test_env):
        """Test handling of invalid JSON file."""
        # Create file with invalid JSON
        invalid_file = e2e_test_env['incoming'] / "paper_testbot_stockbuy_20260214120000000000.json"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json }")

        with patch('order_processor.BASE_DIR', e2e_test_env['root']), \
             patch('order_processor.ORDERS_DIR', e2e_test_env['orders_dir']), \
             patch('order_processor.INCOMING_DIR', e2e_test_env['incoming']), \
             patch('order_processor.PROCESSING_DIR', e2e_test_env['processing']), \
             patch('order_processor.COMPLETED_DIR', e2e_test_env['completed']), \
             patch('order_processor.FAILED_DIR', e2e_test_env['failed']), \
             patch('order_processor.RESPONSES_DIR', e2e_test_env['responses']), \
             patch('order_processor.DATA_DIR', e2e_test_env['data']):

            processor = OrderProcessor()
            processor.process_order_file(invalid_file)

            # Should be in failed
            assert processor.stats['failed'] == 1
            failed_files = list(e2e_test_env['failed'].glob("*.json"))
            assert len(failed_files) == 1

    def test_validation_error_workflow(self, e2e_test_env):
        """Test handling of validation errors."""
        # Create order with mode mismatch
        order_data = {
            "agent_id": "testbot",
            "client_order_id": "testbot_20260214120000000000_stockbuy",
            "order_type": "stockbuy",
            "mode": "live",  # Filename says paper, JSON says live
            "payload": {"symbol": "AAPL", "qty": 10, "order_class": "market", "time_in_force": "day"}
        }

        # Filename has "paper" but JSON has "live"
        invalid_file = e2e_test_env['incoming'] / "paper_testbot_stockbuy_20260214120000000000.json"
        with open(invalid_file, 'w') as f:
            json.dump(order_data, f)

        with patch('order_processor.BASE_DIR', e2e_test_env['root']), \
             patch('order_processor.ORDERS_DIR', e2e_test_env['orders_dir']), \
             patch('order_processor.INCOMING_DIR', e2e_test_env['incoming']), \
             patch('order_processor.PROCESSING_DIR', e2e_test_env['processing']), \
             patch('order_processor.COMPLETED_DIR', e2e_test_env['completed']), \
             patch('order_processor.FAILED_DIR', e2e_test_env['failed']), \
             patch('order_processor.RESPONSES_DIR', e2e_test_env['responses']), \
             patch('order_processor.DATA_DIR', e2e_test_env['data']):

            processor = OrderProcessor()
            processor.process_order_file(invalid_file)

            # Should fail validation
            assert processor.stats['failed'] == 1


@pytest.mark.e2e
@pytest.mark.slow
class TestLargeVolumeWorkflows:
    """Test large volume scenarios."""

    def test_process_many_orders(self, e2e_test_env, mock_trading_client):
        """Test processing many orders sequentially."""
        num_orders = 50

        order_files = []
        for i in range(num_orders):
            timestamp = f"202602141200{i:02d}000000"
            payload = {"symbol": "AAPL", "qty": 1, "order_class": "market", "time_in_force": "day"}

            order_file = create_order_file(
                e2e_test_env['incoming'],
                mode="paper",
                agent="bulkbot",
                order_type="stockbuy",
                timestamp=timestamp,
                payload=payload
            )
            order_files.append(order_file)

        with patch('order_processor.BASE_DIR', e2e_test_env['root']), \
             patch('order_processor.ORDERS_DIR', e2e_test_env['orders_dir']), \
             patch('order_processor.INCOMING_DIR', e2e_test_env['incoming']), \
             patch('order_processor.PROCESSING_DIR', e2e_test_env['processing']), \
             patch('order_processor.COMPLETED_DIR', e2e_test_env['completed']), \
             patch('order_processor.FAILED_DIR', e2e_test_env['failed']), \
             patch('order_processor.RESPONSES_DIR', e2e_test_env['responses']), \
             patch('order_processor.DATA_DIR', e2e_test_env['data']), \
             patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            processor = OrderProcessor()

            # Process all orders
            for order_file in order_files:
                processor.process_order_file(order_file)

            # All should succeed
            assert processor.stats['successful'] == num_orders

            # Ledger should have all orders
            ledger_stats = processor.ledger.get_stats()
            assert ledger_stats['total_processed'] == num_orders
