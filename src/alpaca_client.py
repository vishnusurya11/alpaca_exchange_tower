"""
Alpaca API client wrapper for all order types.
Handles routing, API calls, and error handling.
"""

import os
from typing import Any, Dict, Optional
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
    GetOrdersRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, CryptoLatestQuoteRequest


class AlpacaClientError(Exception):
    """Custom exception for Alpaca API errors."""
    pass


class AlpacaClient:
    """
    Wrapper around Alpaca API clients.
    Handles all 13 order types and routes to appropriate endpoints.
    """

    def __init__(self, mode: str = "paper"):
        """
        Initialize Alpaca client.

        Args:
            mode: 'paper' or 'live'
        """
        self.mode = mode

        # Load API keys from environment
        if mode == "paper":
            self.api_key = os.getenv('ALPACA_PAPER_API_KEY')
            self.secret_key = os.getenv('ALPACA_PAPER_SECRET_KEY')
            self.base_url = os.getenv('ALPACA_PAPER_BASE_URL', 'https://paper-api.alpaca.markets')
        else:  # live
            self.api_key = os.getenv('ALPACA_LIVE_API_KEY')
            self.secret_key = os.getenv('ALPACA_LIVE_SECRET_KEY')
            self.base_url = os.getenv('ALPACA_LIVE_BASE_URL', 'https://api.alpaca.markets')

        if not self.api_key or not self.secret_key:
            raise AlpacaClientError(
                f"Missing API keys for {mode} mode. "
                f"Check .env file for ALPACA_{mode.upper()}_API_KEY and "
                f"ALPACA_{mode.upper()}_SECRET_KEY"
            )

        # Initialize clients
        self.trading_client = TradingClient(
            self.api_key,
            self.secret_key,
            paper=(mode == "paper")
        )

        # Market data clients (same keys work for both paper and live)
        self.stock_data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        self.crypto_data_client = CryptoHistoricalDataClient(self.api_key, self.secret_key)

    def process_order(self, order_type: str, payload: Dict[str, Any], client_order_id: str) -> Dict[str, Any]:
        """
        Route and process order based on order_type.

        Args:
            order_type: One of 13 supported order types
            payload: Order payload
            client_order_id: Unique client order ID

        Returns:
            Response data from Alpaca API

        Raises:
            AlpacaClientError: If API call fails
        """
        try:
            if order_type == "stockbuy":
                return self._stock_order(payload, "buy", client_order_id)
            elif order_type == "stocksell":
                return self._stock_order(payload, "sell", client_order_id)
            elif order_type == "optionsingle":
                return self._option_single(payload, client_order_id)
            elif order_type == "optionmulti":
                return self._option_multi(payload, client_order_id)
            elif order_type == "cryptobuy":
                return self._crypto_order(payload, "buy", client_order_id)
            elif order_type == "cryptosell":
                return self._crypto_order(payload, "sell", client_order_id)
            elif order_type == "marketdata":
                return self._market_data(payload)
            elif order_type == "orderstatus":
                return self._order_status(payload)
            elif order_type == "openorders":
                return self._open_orders(payload)
            elif order_type == "allorders":
                return self._all_orders(payload)
            elif order_type == "positions":
                return self._positions(payload)
            elif order_type == "accountinfo":
                return self._account_info()
            elif order_type == "cancelorder":
                return self._cancel_order(payload)
            else:
                raise AlpacaClientError(f"Unknown order type: {order_type}")
        except Exception as e:
            if "AlpacaClientError" in str(type(e)):
                raise
            raise AlpacaClientError(f"API call failed: {e}")

    def _stock_order(self, payload: Dict[str, Any], side: str, client_order_id: str) -> Dict[str, Any]:
        """Submit stock order."""
        order_class = payload['order_class']
        symbol = payload['symbol']
        qty = payload['qty']
        tif = TimeInForce[payload['time_in_force'].upper()]
        side_enum = OrderSide.BUY if side == "buy" else OrderSide.SELL

        if order_class == "market":
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                time_in_force=tif,
                client_order_id=client_order_id
            )
        elif order_class == "limit":
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                time_in_force=tif,
                limit_price=payload['limit_price'],
                client_order_id=client_order_id
            )
        elif order_class == "stop":
            order_data = StopOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                time_in_force=tif,
                stop_price=payload['stop_price'],
                client_order_id=client_order_id
            )
        elif order_class == "stop_limit":
            order_data = StopLimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                time_in_force=tif,
                limit_price=payload['limit_price'],
                stop_price=payload['stop_price'],
                client_order_id=client_order_id
            )
        else:
            raise AlpacaClientError(f"Unknown order class: {order_class}")

        order = self.trading_client.submit_order(order_data=order_data)
        return self._order_to_dict(order)

    def _option_single(self, payload: Dict[str, Any], client_order_id: str) -> Dict[str, Any]:
        """Submit single-leg option order."""
        symbol = payload['symbol']
        qty = payload['qty']
        side = OrderSide.BUY if payload['side'] == "buy" else OrderSide.SELL
        order_class = payload['order_class']
        tif = TimeInForce[payload['time_in_force'].upper()]

        if order_class == "market":
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=tif,
                client_order_id=client_order_id
            )
        else:  # limit
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=tif,
                limit_price=payload['limit_price'],
                client_order_id=client_order_id
            )

        order = self.trading_client.submit_order(order_data=order_data)
        return self._order_to_dict(order)

    def _option_multi(self, payload: Dict[str, Any], client_order_id: str) -> Dict[str, Any]:
        """Submit multi-leg option order."""
        # For multi-leg, we need to use raw API call as alpaca-py may not have full support
        # This is a simplified version - you may need to adjust based on alpaca-py version
        import requests

        legs = [
            {
                "symbol": leg['symbol'],
                "side": leg['side'],
                "ratio_qty": leg['ratio_qty']
            }
            for leg in payload['legs']
        ]

        order_payload = {
            "order_class": "mleg",
            "type": payload['type'],
            "limit_price": str(payload['limit_price']),
            "time_in_force": payload['time_in_force'],
            "legs": legs,
            "client_order_id": client_order_id
        }

        response = requests.post(
            f"{self.base_url}/v2/orders",
            json=order_payload,
            headers={
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.secret_key
            }
        )

        if response.status_code not in [200, 201]:
            raise AlpacaClientError(f"Multi-leg order failed: {response.text}")

        return response.json()

    def _crypto_order(self, payload: Dict[str, Any], side: str, client_order_id: str) -> Dict[str, Any]:
        """Submit crypto order."""
        # Crypto orders use the same endpoints as stocks
        return self._stock_order(payload, side, client_order_id)

    def _market_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get market data."""
        symbols = payload['symbols']
        data_type = payload['data_type']

        if data_type == "quote":
            results = {}
            for symbol in symbols:
                # Determine if crypto or stock based on symbol format
                if symbol.endswith('USD') and len(symbol) > 5:  # Likely crypto (BTCUSD)
                    request = CryptoLatestQuoteRequest(symbol_or_symbols=symbol)
                    quote = self.crypto_data_client.get_crypto_latest_quote(request)
                    results[symbol] = {
                        "bid_price": str(quote[symbol].bid_price),
                        "ask_price": str(quote[symbol].ask_price),
                        "timestamp": str(quote[symbol].timestamp)
                    }
                else:  # Stock
                    request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
                    quote = self.stock_data_client.get_stock_latest_quote(request)
                    results[symbol] = {
                        "bid_price": str(quote[symbol].bid_price),
                        "ask_price": str(quote[symbol].ask_price),
                        "timestamp": str(quote[symbol].timestamp)
                    }
            return {"quotes": results}
        else:
            # For bars and trades, similar logic applies
            return {"message": f"Market data type '{data_type}' not fully implemented yet"}

    def _order_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get order status."""
        if payload.get('alpaca_order_id'):
            order = self.trading_client.get_order_by_id(payload['alpaca_order_id'])
        elif payload.get('client_order_id'):
            order = self.trading_client.get_order_by_client_id(payload['client_order_id'])
        else:
            raise AlpacaClientError("Must provide either alpaca_order_id or client_order_id")

        return self._order_to_dict(order)

    def _open_orders(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get open orders."""
        request = GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            limit=payload.get('limit', 100)
        )

        if payload.get('symbols'):
            request.symbols = payload['symbols']

        orders = self.trading_client.get_orders(filter=request)
        return {"orders": [self._order_to_dict(o) for o in orders]}

    def _all_orders(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get all orders."""
        status_map = {
            "open": QueryOrderStatus.OPEN,
            "closed": QueryOrderStatus.CLOSED,
            "all": QueryOrderStatus.ALL
        }

        request = GetOrdersRequest(
            status=status_map[payload.get('status', 'all')],
            limit=payload.get('limit', 100)
        )

        if payload.get('after'):
            request.after = payload['after']
        if payload.get('until'):
            request.until = payload['until']

        orders = self.trading_client.get_orders(filter=request)
        return {"orders": [self._order_to_dict(o) for o in orders]}

    def _positions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get positions."""
        positions = self.trading_client.get_all_positions()

        # Filter by asset class if specified
        if payload.get('asset_class'):
            positions = [p for p in positions if p.asset_class == payload['asset_class']]

        return {
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": str(p.qty),
                    "avg_entry_price": str(p.avg_entry_price),
                    "current_price": str(p.current_price),
                    "market_value": str(p.market_value),
                    "unrealized_pl": str(p.unrealized_pl),
                    "unrealized_plpc": str(p.unrealized_plpc),
                    "side": str(p.side),
                    "asset_class": str(p.asset_class)
                }
                for p in positions
            ]
        }

    def _account_info(self) -> Dict[str, Any]:
        """Get account information."""
        account = self.trading_client.get_account()
        return {
            "status": str(account.status),
            "buying_power": str(account.buying_power),
            "cash": str(account.cash),
            "portfolio_value": str(account.portfolio_value),
            "equity": str(account.equity),
            "last_equity": str(account.last_equity),
            "long_market_value": str(account.long_market_value),
            "short_market_value": str(account.short_market_value)
        }

    def _cancel_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel an order."""
        if payload.get('alpaca_order_id'):
            self.trading_client.cancel_order_by_id(payload['alpaca_order_id'])
            return {"cancelled": True, "order_id": payload['alpaca_order_id']}
        elif payload.get('client_order_id'):
            # Cancel by client order ID requires getting order first
            order = self.trading_client.get_order_by_client_id(payload['client_order_id'])
            self.trading_client.cancel_order_by_id(order.id)
            return {"cancelled": True, "client_order_id": payload['client_order_id'], "order_id": order.id}
        else:
            raise AlpacaClientError("Must provide either alpaca_order_id or client_order_id")

    def _order_to_dict(self, order) -> Dict[str, Any]:
        """Convert order object to dictionary."""
        return {
            "id": str(order.id),
            "client_order_id": str(order.client_order_id),
            "created_at": str(order.created_at),
            "updated_at": str(order.updated_at),
            "submitted_at": str(order.submitted_at),
            "filled_at": str(order.filled_at) if order.filled_at else None,
            "canceled_at": str(order.canceled_at) if order.canceled_at else None,
            "failed_at": str(order.failed_at) if order.failed_at else None,
            "symbol": str(order.symbol),
            "asset_class": str(order.asset_class),
            "qty": str(order.qty) if order.qty else None,
            "filled_qty": str(order.filled_qty) if order.filled_qty else None,
            "filled_avg_price": str(order.filled_avg_price) if order.filled_avg_price else None,
            "order_type": str(order.order_type),
            "side": str(order.side),
            "time_in_force": str(order.time_in_force),
            "limit_price": str(order.limit_price) if order.limit_price else None,
            "stop_price": str(order.stop_price) if order.stop_price else None,
            "status": str(order.status),
            "extended_hours": order.extended_hours if hasattr(order, 'extended_hours') else False
        }
