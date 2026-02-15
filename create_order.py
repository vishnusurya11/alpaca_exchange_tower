#!/usr/bin/env python3
"""
CLI tool to create order JSON files.
Simplifies order file generation with validation.
"""

import json
import argparse
from datetime import datetime, timezone
from pathlib import Path


def generate_filename(mode: str, agent_id: str, order_type: str) -> str:
    """
    Generate filename with current timestamp.

    Returns:
        Filename in format: {mode}_{agentid}_{ordertype}_{timestamp}.json
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
    return f"{mode}_{agent_id}_{order_type}_{timestamp}.json"


def generate_client_order_id(agent_id: str, order_type: str) -> str:
    """Generate client_order_id."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
    return f"{agent_id}_{timestamp}_{order_type}"


def create_stock_order(args) -> dict:
    """Create stock buy/sell order."""
    payload = {
        "symbol": args.symbol.upper(),
        "qty": args.qty,
        "order_class": args.order_class,
        "time_in_force": args.tif
    }

    if args.order_class in ["limit", "stop_limit"]:
        payload["limit_price"] = args.limit_price

    if args.order_class in ["stop", "stop_limit"]:
        payload["stop_price"] = args.stop_price

    return payload


def create_crypto_order(args) -> dict:
    """Create crypto buy/sell order."""
    return {
        "symbol": args.symbol.upper(),
        "qty": args.qty,
        "order_class": args.order_class or "market",
        "limit_price": args.limit_price if args.limit_price else None,
        "time_in_force": args.tif or "gtc"
    }


def create_option_single(args) -> dict:
    """Create single-leg option order."""
    return {
        "symbol": args.symbol,
        "qty": args.qty,
        "side": args.side,
        "order_class": args.order_class or "market",
        "limit_price": args.limit_price if args.limit_price else None,
        "time_in_force": args.tif or "day"
    }


def create_positions_order(args) -> dict:
    """Create positions query."""
    payload = {}
    if args.asset_class:
        payload["asset_class"] = args.asset_class
    return payload


def create_open_orders(args) -> dict:
    """Create open orders query."""
    return {
        "status": "open",
        "limit": args.limit or 100
    }


def create_account_info(args) -> dict:
    """Create account info query."""
    return {}


def main():
    parser = argparse.ArgumentParser(description="Create Alpaca order JSON files")
    parser.add_argument("--agent", required=True, help="Agent ID (lowercase alphanumeric, no underscores)")
    parser.add_argument("--mode", required=True, choices=["paper", "live"], help="Trading mode")
    parser.add_argument("--type", required=True, dest="order_type",
                        choices=["stockbuy", "stocksell", "cryptobuy", "cryptosell",
                                 "optionsingle", "positions", "openorders", "accountinfo"],
                        help="Order type")

    # Common arguments
    parser.add_argument("--symbol", help="Symbol (e.g., AAPL, BTCUSD)")
    parser.add_argument("--qty", type=float, help="Quantity")
    parser.add_argument("--order-class", choices=["market", "limit", "stop", "stop_limit"], help="Order class")
    parser.add_argument("--limit-price", type=float, help="Limit price")
    parser.add_argument("--stop-price", type=float, help="Stop price")
    parser.add_argument("--tif", choices=["day", "gtc", "ioc", "fok"], help="Time in force")

    # Option-specific
    parser.add_argument("--side", choices=["buy", "sell"], help="Buy or sell (for options)")

    # Query-specific
    parser.add_argument("--asset-class", choices=["us_equity", "us_option", "crypto"], help="Asset class filter")
    parser.add_argument("--limit", type=int, help="Result limit")

    # Output
    parser.add_argument("--output-dir", default="orders/incoming", help="Output directory")

    args = parser.parse_args()

    # Generate filename and client_order_id
    filename = generate_filename(args.mode, args.agent, args.order_type)
    client_order_id = generate_client_order_id(args.agent, args.order_type)

    # Create payload based on order type
    if args.order_type in ["stockbuy", "stocksell"]:
        if not args.symbol or args.qty is None:
            print("Error: --symbol and --qty are required for stock orders")
            return 1
        payload = create_stock_order(args)
    elif args.order_type in ["cryptobuy", "cryptosell"]:
        if not args.symbol or args.qty is None:
            print("Error: --symbol and --qty are required for crypto orders")
            return 1
        payload = create_crypto_order(args)
    elif args.order_type == "optionsingle":
        if not args.symbol or args.qty is None or not args.side:
            print("Error: --symbol, --qty, and --side are required for option orders")
            return 1
        payload = create_option_single(args)
    elif args.order_type == "positions":
        payload = create_positions_order(args)
    elif args.order_type == "openorders":
        payload = create_open_orders(args)
    elif args.order_type == "accountinfo":
        payload = create_account_info(args)
    else:
        print(f"Error: Order type '{args.order_type}' not implemented yet")
        return 1

    # Create order JSON
    order = {
        "agent_id": args.agent,
        "client_order_id": client_order_id,
        "order_type": args.order_type,
        "mode": args.mode,
        "payload": {k: v for k, v in payload.items() if v is not None}
    }

    # Write to file
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    with open(output_path, 'w') as f:
        json.dump(order, f, indent=2)

    print(f"✅ Order file created: {output_path}")
    print(f"📋 Client Order ID: {client_order_id}")
    print()
    print("File contents:")
    print(json.dumps(order, indent=2))

    return 0


if __name__ == "__main__":
    exit(main())
