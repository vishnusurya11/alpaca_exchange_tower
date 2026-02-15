"""
Integration tests for the complete order processing pipeline.

Tests the integration of:
- Validators + Ledger + AlpacaClient + ResponseWriter
- Complete order processing flow
- Error handling across modules
- Duplicate detection in pipeline
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.validators import validate_order_file
from src.ledger import SimpleLedger
from src.alpaca_client import AlpacaClient
from src.response_writer import ResponseWriter


@pytest.fixture
def pipeline_dirs(tmp_path):
    """Create directory structure for pipeline testing."""
    dirs = {
        'orders': tmp_path / "orders",
        'incoming': tmp_path / "orders" / "incoming",
        'processing': tmp_path / "orders" / "processing",
        'completed': tmp_path / "orders" / "completed",
        'failed': tmp_path / "orders" / "failed",
        'responses': tmp_path / "responses",
        'data': tmp_path / "data",
    }

    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return dirs


@pytest.fixture
def pipeline_components(pipeline_dirs):
    """Initialize all pipeline components."""
    ledger = SimpleLedger(pipeline_dirs['data'] / "ledger.txt")
    response_writer = ResponseWriter(pipeline_dirs['responses'])

    return {
        'ledger': ledger,
        'response_writer': response_writer,
    }


@pytest.mark.integration
class TestCompleteOrderPipeline:
    """Test complete order processing pipeline."""

    def test_successful_order_flow(self, pipeline_dirs, pipeline_components, mock_env_vars, mock_trading_client, valid_stock_buy_payload, fixed_timestamp):
        """Test complete successful order processing."""
        # Step 1: Create order file
        filename = f"paper_testbot_stockbuy_{fixed_timestamp}.json"
        order_data = {
            "agent_id": "testbot",
            "client_order_id": f"testbot_{fixed_timestamp}_stockbuy",
            "order_type": "stockbuy",
            "mode": "paper",
            "payload": valid_stock_buy_payload
        }

        order_file = pipeline_dirs['incoming'] / filename
        with open(order_file, 'w') as f:
            json.dump(order_data, f)

        # Step 2: Validate
        filename_parts, validated_order = validate_order_file(order_file)

        assert filename_parts['mode'] == 'paper'
        assert validated_order.order_type == 'stockbuy'

        # Step 3: Check ledger (should not be duplicate)
        is_dup, reason = pipeline_components['ledger'].is_duplicate(order_data['client_order_id'])
        assert is_dup is False

        # Step 4: Process with Alpaca (mocked)
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            alpaca_client = AlpacaClient(mode="paper")
            response_data = alpaca_client.process_order(
                order_type="stockbuy",
                payload=validated_order.payload,
                client_order_id=order_data['client_order_id']
            )

            assert response_data['symbol'] == 'AAPL'

        # Step 5: Record in ledger
        pipeline_components['ledger'].record(order_data['client_order_id'])

        # Step 6: Write response
        response_path = pipeline_components['response_writer'].write_success(
            agent_id=filename_parts['agent_id'],
            mode=filename_parts['mode'],
            order_type=filename_parts['order_type'],
            timestamp=filename_parts['timestamp'],
            client_order_id=order_data['client_order_id'],
            data=response_data
        )

        assert response_path.exists()

        # Step 7: Verify ledger recorded
        is_dup, reason = pipeline_components['ledger'].is_duplicate(order_data['client_order_id'])
        assert is_dup is True

    def test_duplicate_order_detected(self, pipeline_dirs, pipeline_components, valid_stock_buy_payload, fixed_timestamp):
        """Test duplicate order is detected and rejected."""
        client_order_id = f"testbot_{fixed_timestamp}_stockbuy"

        # Record order in ledger first
        pipeline_components['ledger'].record(client_order_id)

        # Try to process same order again
        is_dup, reason = pipeline_components['ledger'].is_duplicate(client_order_id)

        assert is_dup is True
        assert "already processed" in reason.lower()

        # Write duplicate error response
        response_path = pipeline_components['response_writer'].write_error(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=client_order_id,
            error_type="duplicate_error",
            error_message=reason
        )

        assert response_path.exists()

        # Verify error response content
        with open(response_path, 'r') as f:
            response = json.load(f)

        assert response['status'] == 'error'
        assert response['error']['type'] == 'duplicate_error'

    def test_validation_error_flow(self, pipeline_dirs, pipeline_components, fixed_timestamp):
        """Test validation error is handled correctly."""
        # Create invalid order (missing required field)
        filename = f"paper_testbot_stockbuy_{fixed_timestamp}.json"
        invalid_order_data = {
            "agent_id": "testbot",
            # Missing client_order_id
            "order_type": "stockbuy",
            "mode": "paper",
            "payload": {"symbol": "AAPL", "qty": 10}
        }

        order_file = pipeline_dirs['incoming'] / filename
        with open(order_file, 'w') as f:
            json.dump(invalid_order_data, f)

        # Validation should fail
        from src.validators import ValidationError
        with pytest.raises(ValidationError):
            validate_order_file(order_file)

        # Write error response
        response_path = pipeline_components['response_writer'].write_error(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id="unknown",
            error_type="validation_error",
            error_message="Missing required field: client_order_id"
        )

        assert response_path.exists()

    def test_api_error_flow(self, pipeline_dirs, pipeline_components, mock_env_vars, valid_stock_buy_payload, fixed_timestamp):
        """Test API error is handled correctly."""
        mock_client = MagicMock()
        mock_client.submit_order.side_effect = Exception("Insufficient funds")

        client_order_id = f"testbot_{fixed_timestamp}_stockbuy"

        with patch('src.alpaca_client.TradingClient', return_value=mock_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            from src.alpaca_client import AlpacaClientError
            alpaca_client = AlpacaClient(mode="paper")

            # Should raise AlpacaClientError
            with pytest.raises(AlpacaClientError):
                alpaca_client.process_order(
                    order_type="stockbuy",
                    payload=valid_stock_buy_payload,
                    client_order_id=client_order_id
                )

        # Write error response
        response_path = pipeline_components['response_writer'].write_error(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp=fixed_timestamp,
            client_order_id=client_order_id,
            error_type="api_error",
            error_message="Insufficient funds"
        )

        assert response_path.exists()


@pytest.mark.integration
class TestMultipleOrderProcessing:
    """Test processing multiple orders."""

    def test_process_multiple_orders_sequentially(self, pipeline_dirs, pipeline_components, mock_env_vars, mock_trading_client, fixed_timestamp):
        """Test processing multiple orders in sequence."""
        orders = [
            ("stockbuy", "AAPL", 10),
            ("stocksell", "TSLA", 5),
            ("cryptobuy", "BTCUSD", 0.01),
        ]

        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            alpaca_client = AlpacaClient(mode="paper")

            for i, (order_type, symbol, qty) in enumerate(orders):
                client_order_id = f"testbot_2026021412000{i}000000_{order_type}"

                # Check not duplicate
                is_dup, _ = pipeline_components['ledger'].is_duplicate(client_order_id)
                assert is_dup is False

                # Process order
                payload = {
                    "symbol": symbol,
                    "qty": qty,
                    "order_class": "market",
                    "time_in_force": "day"
                }

                if order_type in ["stockbuy", "stocksell"]:
                    response_data = alpaca_client.process_order(
                        order_type=order_type,
                        payload=payload,
                        client_order_id=client_order_id
                    )
                else:  # crypto
                    response_data = alpaca_client.process_order(
                        order_type=order_type,
                        payload=payload,
                        client_order_id=client_order_id
                    )

                # Record in ledger
                pipeline_components['ledger'].record(client_order_id)

        # Verify all recorded
        stats = pipeline_components['ledger'].get_stats()
        assert stats['total_processed'] == len(orders)

    def test_duplicate_in_batch_rejected(self, pipeline_dirs, pipeline_components):
        """Test duplicate in batch of orders is rejected."""
        client_order_id = "testbot_20260214120000000000_stockbuy"

        # First order
        is_dup, _ = pipeline_components['ledger'].is_duplicate(client_order_id)
        assert is_dup is False

        pipeline_components['ledger'].record(client_order_id)

        # Try same order again (duplicate)
        is_dup, reason = pipeline_components['ledger'].is_duplicate(client_order_id)
        assert is_dup is True

        # Second occurrence should be rejected
        response_path = pipeline_components['response_writer'].write_error(
            agent_id="testbot",
            mode="paper",
            order_type="stockbuy",
            timestamp="20260214120000000000",
            client_order_id=client_order_id,
            error_type="duplicate_error",
            error_message=reason
        )

        assert response_path.exists()


@pytest.mark.integration
class TestPersistenceAcrossRestarts:
    """Test pipeline persistence across restarts."""

    def test_ledger_persists_across_sessions(self, pipeline_dirs):
        """Test ledger persists processed orders across sessions."""
        ledger_file = pipeline_dirs['data'] / "ledger.txt"

        # Session 1: Process orders
        ledger1 = SimpleLedger(ledger_file)
        ledger1.record("order1_20260214120000000000_stockbuy")
        ledger1.record("order2_20260214120100000000_stocksell")

        # Session 2: New instance (simulates restart)
        ledger2 = SimpleLedger(ledger_file)

        # Previously processed orders should be duplicates
        is_dup, _ = ledger2.is_duplicate("order1_20260214120000000000_stockbuy")
        assert is_dup is True

        is_dup, _ = ledger2.is_duplicate("order2_20260214120100000000_stocksell")
        assert is_dup is True

        # New order should not be duplicate
        is_dup, _ = ledger2.is_duplicate("order3_20260214120200000000_cryptobuy")
        assert is_dup is False


@pytest.mark.integration
class TestMultiAgentScenarios:
    """Test multi-agent scenarios."""

    def test_multiple_agents_separate_responses(self, pipeline_dirs, pipeline_components, mock_env_vars, mock_trading_client):
        """Test multiple agents get separate response directories."""
        agents = ["sentiment", "momentum", "crypto"]

        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            alpaca_client = AlpacaClient(mode="paper")

            for agent in agents:
                client_order_id = f"{agent}_20260214120000000000_stockbuy"

                # Process order
                response_data = alpaca_client.process_order(
                    order_type="stockbuy",
                    payload={"symbol": "AAPL", "qty": 10, "order_class": "market", "time_in_force": "day"},
                    client_order_id=client_order_id
                )

                # Write response
                response_path = pipeline_components['response_writer'].write_success(
                    agent_id=agent,
                    mode="paper",
                    order_type="stockbuy",
                    timestamp="20260214120000000000",
                    client_order_id=client_order_id,
                    data=response_data
                )

                # Verify response in correct agent directory
                assert agent in str(response_path)
                assert response_path.exists()

        # Verify all agent directories exist
        for agent in agents:
            agent_dir = pipeline_dirs['responses'] / agent
            assert agent_dir.exists()

    def test_agents_share_ledger(self, pipeline_dirs, pipeline_components):
        """Test all agents share the same ledger (prevent duplicate orders across agents)."""
        # Agent 1 processes order
        client_order_id = "agent1_20260214120000000000_stockbuy"
        pipeline_components['ledger'].record(client_order_id)

        # Agent 2 tries same order (should be duplicate even from different agent)
        is_dup, reason = pipeline_components['ledger'].is_duplicate(client_order_id)
        assert is_dup is True


@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery scenarios."""

    def test_partial_failure_recovery(self, pipeline_dirs, pipeline_components, mock_env_vars, fixed_timestamp):
        """Test recovery from partial failures."""
        # Order 1: Success
        mock_success_client = MagicMock()
        mock_order = MagicMock()
        mock_order.symbol = "AAPL"
        mock_order.side = "buy"
        mock_order.status = "filled"
        mock_order.id = "order_1"
        mock_order.client_order_id = f"testbot_{fixed_timestamp}_stockbuy"
        for attr in ['created_at', 'updated_at', 'submitted_at', 'filled_at', 'canceled_at',
                     'failed_at', 'asset_class', 'qty', 'filled_qty', 'filled_avg_price',
                     'order_type', 'time_in_force', 'limit_price', 'stop_price', 'extended_hours']:
            setattr(mock_order, attr, None)
        mock_success_client.submit_order.return_value = mock_order

        # Order 2: Failure
        mock_fail_client = MagicMock()
        mock_fail_client.submit_order.side_effect = Exception("API Error")

        # Process first order (success)
        with patch('src.alpaca_client.TradingClient', return_value=mock_success_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            alpaca_client = AlpacaClient(mode="paper")
            client_order_id_1 = f"testbot_{fixed_timestamp}_stockbuy"

            response_data = alpaca_client.process_order(
                order_type="stockbuy",
                payload={"symbol": "AAPL", "qty": 10, "order_class": "market", "time_in_force": "day"},
                client_order_id=client_order_id_1
            )

            pipeline_components['ledger'].record(client_order_id_1)

        # Process second order (failure)
        with patch('src.alpaca_client.TradingClient', return_value=mock_fail_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            from src.alpaca_client import AlpacaClientError
            alpaca_client = AlpacaClient(mode="paper")
            client_order_id_2 = "testbot_20260214120100000000_stocksell"

            with pytest.raises(AlpacaClientError):
                alpaca_client.process_order(
                    order_type="stocksell",
                    payload={"symbol": "TSLA", "qty": 5, "order_class": "market", "time_in_force": "day"},
                    client_order_id=client_order_id_2
                )

        # Verify first order still in ledger
        is_dup, _ = pipeline_components['ledger'].is_duplicate(client_order_id_1)
        assert is_dup is True

        # Second order should not be in ledger
        is_dup, _ = pipeline_components['ledger'].is_duplicate(client_order_id_2)
        assert is_dup is False
