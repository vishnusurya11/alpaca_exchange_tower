"""
Unit tests for src/alpaca_client.py

Tests Alpaca API client wrapper with mocked API calls:
- Client initialization for paper and live modes
- All 13 order type routing
- Error handling
- API response transformation
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from src.alpaca_client import AlpacaClient, AlpacaClientError


class TestAlpacaClientInitialization:
    """Test client initialization."""

    def test_initialize_paper_mode(self, mock_env_vars):
        """Test initializing client in paper mode."""
        with patch('src.alpaca_client.TradingClient'), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")

            assert client.mode == "paper"
            assert client.api_key == mock_env_vars['ALPACA_PAPER_API_KEY']
            assert client.secret_key == mock_env_vars['ALPACA_PAPER_SECRET_KEY']

    def test_initialize_live_mode(self, mock_env_vars):
        """Test initializing client in live mode."""
        with patch('src.alpaca_client.TradingClient'), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="live")

            assert client.mode == "live"
            assert client.api_key == mock_env_vars['ALPACA_LIVE_API_KEY']
            assert client.secret_key == mock_env_vars['ALPACA_LIVE_SECRET_KEY']

    def test_missing_api_keys_raises_error(self, monkeypatch):
        """Test missing API keys raises error."""
        # Clear environment variables
        monkeypatch.delenv('ALPACA_PAPER_API_KEY', raising=False)
        monkeypatch.delenv('ALPACA_PAPER_SECRET_KEY', raising=False)

        with pytest.raises(AlpacaClientError, match="Missing API keys"):
            AlpacaClient(mode="paper")


class TestStockOrders:
    """Test stock order routing."""

    def test_stock_buy_market_order(self, mock_env_vars, mock_trading_client, valid_stock_buy_payload):
        """Test submitting market buy order for stocks."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="stockbuy",
                payload=valid_stock_buy_payload,
                client_order_id="testbot_20260214120000000000_stockbuy"
            )

            assert result['symbol'] == 'AAPL'
            assert result['side'] == 'buy'
            mock_trading_client.submit_order.assert_called_once()

    def test_stock_sell_limit_order(self, mock_env_vars, mock_trading_client, valid_stock_sell_payload):
        """Test submitting limit sell order for stocks."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="stocksell",
                payload=valid_stock_sell_payload,
                client_order_id="testbot_20260214120000000000_stocksell"
            )

            assert result['symbol'] == 'TSLA'
            assert result['side'] == 'sell'
            mock_trading_client.submit_order.assert_called_once()

    def test_stock_stop_order(self, mock_env_vars, mock_trading_client):
        """Test submitting stop order."""
        stop_payload = {
            "symbol": "AAPL",
            "qty": 10,
            "order_class": "stop",
            "stop_price": 145.00,
            "time_in_force": "day"
        }

        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="stockbuy",
                payload=stop_payload,
                client_order_id="testbot_20260214120000000000_stockbuy"
            )

            mock_trading_client.submit_order.assert_called_once()

    def test_stock_stop_limit_order(self, mock_env_vars, mock_trading_client):
        """Test submitting stop-limit order."""
        stop_limit_payload = {
            "symbol": "AAPL",
            "qty": 10,
            "order_class": "stop_limit",
            "limit_price": 150.00,
            "stop_price": 145.00,
            "time_in_force": "day"
        }

        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="stockbuy",
                payload=stop_limit_payload,
                client_order_id="testbot_20260214120000000000_stockbuy"
            )

            mock_trading_client.submit_order.assert_called_once()


class TestCryptoOrders:
    """Test cryptocurrency order routing."""

    def test_crypto_buy_order(self, mock_env_vars, mock_trading_client, valid_crypto_buy_payload):
        """Test submitting crypto buy order."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="cryptobuy",
                payload=valid_crypto_buy_payload,
                client_order_id="cryptobot_20260214120000000000_cryptobuy"
            )

            assert result['symbol'] == 'AAPL'  # Mock returns AAPL
            mock_trading_client.submit_order.assert_called_once()

    def test_crypto_sell_order(self, mock_env_vars, mock_trading_client):
        """Test submitting crypto sell order."""
        crypto_sell_payload = {
            "symbol": "BTCUSD",
            "qty": 0.01,
            "order_class": "limit",
            "limit_price": 45000.00,
            "time_in_force": "gtc"
        }

        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="cryptosell",
                payload=crypto_sell_payload,
                client_order_id="cryptobot_20260214120000000000_cryptosell"
            )

            mock_trading_client.submit_order.assert_called_once()


class TestOptionOrders:
    """Test option order routing."""

    def test_option_single_buy(self, mock_env_vars, mock_trading_client, valid_option_single_payload):
        """Test submitting single-leg option order."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="optionsingle",
                payload=valid_option_single_payload,
                client_order_id="optionbot_20260214120000000000_optionsingle"
            )

            mock_trading_client.submit_order.assert_called_once()

    def test_option_multi_leg(self, mock_env_vars, valid_option_multi_payload):
        """Test submitting multi-leg option order."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "mleg_order_123",
            "order_class": "mleg",
            "status": "accepted"
        }

        with patch('src.alpaca_client.TradingClient'), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'), \
             patch('src.alpaca_client.requests.post', return_value=mock_response):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="optionmulti",
                payload=valid_option_multi_payload,
                client_order_id="spreadbot_20260214120000000000_optionmulti"
            )

            assert result['order_class'] == 'mleg'


class TestQueryOperations:
    """Test query and management operations."""

    def test_order_status_by_id(self, mock_env_vars, mock_trading_client):
        """Test getting order status by Alpaca order ID."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="orderstatus",
                payload={"alpaca_order_id": "abc-123"},
                client_order_id="monitor_20260214120000000000_orderstatus"
            )

            mock_trading_client.get_order_by_id.assert_called_once_with("abc-123")

    def test_order_status_by_client_id(self, mock_env_vars, mock_trading_client):
        """Test getting order status by client order ID."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="orderstatus",
                payload={"client_order_id": "testbot_20260214120000000000_stockbuy"},
                client_order_id="monitor_20260214120000000000_orderstatus"
            )

            mock_trading_client.get_order_by_client_id.assert_called_once()

    def test_open_orders(self, mock_env_vars, mock_trading_client):
        """Test getting open orders."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="openorders",
                payload={"status": "open", "limit": 100},
                client_order_id="monitor_20260214120000000000_openorders"
            )

            assert 'orders' in result
            mock_trading_client.get_orders.assert_called_once()

    def test_all_orders(self, mock_env_vars, mock_trading_client):
        """Test getting all orders."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="allorders",
                payload={"status": "all", "limit": 500},
                client_order_id="monitor_20260214120000000000_allorders"
            )

            assert 'orders' in result
            mock_trading_client.get_orders.assert_called_once()

    def test_positions(self, mock_env_vars, mock_trading_client):
        """Test getting positions."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="positions",
                payload={"asset_class": "us_equity"},
                client_order_id="portfolio_20260214120000000000_positions"
            )

            assert 'positions' in result
            mock_trading_client.get_all_positions.assert_called_once()

    def test_account_info(self, mock_env_vars, mock_trading_client):
        """Test getting account information."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="accountinfo",
                payload={},
                client_order_id="dashboard_20260214120000000000_accountinfo"
            )

            assert 'status' in result
            assert 'buying_power' in result
            mock_trading_client.get_account.assert_called_once()

    def test_cancel_order_by_id(self, mock_env_vars, mock_trading_client):
        """Test canceling order by Alpaca order ID."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="cancelorder",
                payload={"alpaca_order_id": "order_123"},
                client_order_id="riskbot_20260214120000000000_cancelorder"
            )

            assert result['cancelled'] is True
            mock_trading_client.cancel_order_by_id.assert_called_once_with("order_123")

    def test_cancel_order_by_client_id(self, mock_env_vars, mock_trading_client):
        """Test canceling order by client order ID."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="cancelorder",
                payload={"client_order_id": "testbot_20260214120000000000_stockbuy"},
                client_order_id="riskbot_20260214120000000000_cancelorder"
            )

            assert result['cancelled'] is True
            # Should get order first, then cancel
            mock_trading_client.get_order_by_client_id.assert_called_once()
            mock_trading_client.cancel_order_by_id.assert_called_once()


class TestMarketData:
    """Test market data operations."""

    def test_market_data_stock_quote(self, mock_env_vars, mock_trading_client):
        """Test getting stock quote."""
        mock_stock_data_client = MagicMock()
        mock_quote = MagicMock()
        mock_quote.bid_price = 150.00
        mock_quote.ask_price = 150.10
        mock_quote.timestamp = "2026-02-14T12:00:00Z"
        mock_stock_data_client.get_stock_latest_quote.return_value = {"AAPL": mock_quote}

        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient', return_value=mock_stock_data_client), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="marketdata",
                payload={"symbols": ["AAPL"], "data_type": "quote"},
                client_order_id="databot_20260214120000000000_marketdata"
            )

            assert 'quotes' in result
            assert 'AAPL' in result['quotes']


class TestErrorHandling:
    """Test error handling."""

    def test_unknown_order_type_raises_error(self, mock_env_vars):
        """Test unknown order type raises error."""
        with patch('src.alpaca_client.TradingClient'), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")

            with pytest.raises(AlpacaClientError, match="Unknown order type"):
                client.process_order(
                    order_type="invalidtype",
                    payload={},
                    client_order_id="test_20260214120000000000_invalid"
                )

    def test_api_exception_wrapped(self, mock_env_vars, mock_trading_client):
        """Test API exceptions are wrapped in AlpacaClientError."""
        mock_trading_client.submit_order.side_effect = Exception("API error")

        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")

            with pytest.raises(AlpacaClientError, match="API call failed"):
                client.process_order(
                    order_type="stockbuy",
                    payload={"symbol": "AAPL", "qty": 10, "order_class": "market", "time_in_force": "day"},
                    client_order_id="test_20260214120000000000_stockbuy"
                )

    def test_cancel_order_missing_ids_raises_error(self, mock_env_vars):
        """Test cancel order without IDs raises error."""
        with patch('src.alpaca_client.TradingClient'), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")

            with pytest.raises(AlpacaClientError, match="Must provide either"):
                client.process_order(
                    order_type="cancelorder",
                    payload={},  # Missing both IDs
                    client_order_id="test_20260214120000000000_cancelorder"
                )

    def test_order_status_missing_ids_raises_error(self, mock_env_vars):
        """Test order status without IDs raises error."""
        with patch('src.alpaca_client.TradingClient'), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")

            with pytest.raises(AlpacaClientError, match="Must provide either"):
                client.process_order(
                    order_type="orderstatus",
                    payload={},  # Missing both IDs
                    client_order_id="test_20260214120000000000_orderstatus"
                )


class TestOrderConversion:
    """Test order object to dictionary conversion."""

    def test_order_to_dict_conversion(self, mock_env_vars, mock_trading_client, valid_stock_buy_payload):
        """Test order object is correctly converted to dict."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client), \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")
            result = client.process_order(
                order_type="stockbuy",
                payload=valid_stock_buy_payload,
                client_order_id="testbot_20260214120000000000_stockbuy"
            )

            # Check all expected fields are present
            expected_fields = [
                'id', 'client_order_id', 'symbol', 'qty', 'side',
                'order_type', 'status', 'time_in_force'
            ]
            for field in expected_fields:
                assert field in result


class TestClientCaching:
    """Test that clients can be reused efficiently."""

    def test_single_client_instance_per_mode(self, mock_env_vars, mock_trading_client, valid_stock_buy_payload):
        """Test client instances are created once per mode."""
        with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client) as mock_trading_constructor, \
             patch('src.alpaca_client.StockHistoricalDataClient'), \
             patch('src.alpaca_client.CryptoHistoricalDataClient'):

            client = AlpacaClient(mode="paper")

            # Submit multiple orders
            for i in range(3):
                client.process_order(
                    order_type="stockbuy",
                    payload=valid_stock_buy_payload,
                    client_order_id=f"testbot_2026021412000{i}000000_stockbuy"
                )

            # TradingClient should only be initialized once
            assert mock_trading_constructor.call_count == 1
