#!/usr/bin/env python3
"""
Quick test script to verify Alpaca API connection and place a Tesla order.
This tests that your API keys work before building the full order processor.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

def main():
    # Load environment variables
    load_dotenv()

    # Get paper trading API keys
    api_key = os.getenv('ALPACA_PAPER_API_KEY')
    secret_key = os.getenv('ALPACA_PAPER_SECRET_KEY')

    if not api_key or not secret_key:
        print("❌ Error: API keys not found in .env file")
        print("Please add ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY to .env")
        return

    print("=" * 60)
    print("🚀 Alpaca Exchange Tower - Connection Test")
    print("=" * 60)
    print(f"📅 Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"🔑 API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"📊 Mode: Paper Trading")
    print()

    try:
        # Initialize trading client (paper mode)
        print("🔌 Connecting to Alpaca API...")
        trading_client = TradingClient(api_key, secret_key, paper=True)

        # Get account info to verify connection
        print("✅ Connection successful!")
        print()
        print("📋 Fetching account information...")
        account = trading_client.get_account()

        print("=" * 60)
        print("💰 Account Summary")
        print("=" * 60)
        print(f"Account Status: {account.status}")
        print(f"Buying Power: ${float(account.buying_power):,.2f}")
        print(f"Cash: ${float(account.cash):,.2f}")
        print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
        print(f"Equity: ${float(account.equity):,.2f}")
        print()

        # Check if market is open
        clock = trading_client.get_clock()
        market_status = "🟢 OPEN" if clock.is_open else "🔴 CLOSED"
        print(f"Market Status: {market_status}")

        if not clock.is_open:
            print(f"⏰ Next market open: {clock.next_open}")
            print("⚠️  Note: Order will be queued until market opens")

        print()
        print("=" * 60)
        print("📈 Placing Tesla (TSLA) Market Order")
        print("=" * 60)

        # Create market order for 1 share of TSLA
        order_data = MarketOrderRequest(
            symbol="TSLA",
            qty=1,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            client_order_id=f"testbot_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_stockbuy"
        )

        print(f"Symbol: TSLA")
        print(f"Side: BUY")
        print(f"Quantity: 1 share")
        print(f"Order Type: Market")
        print(f"Time in Force: Day")
        print()

        # Submit order
        print("📤 Submitting order...")
        order = trading_client.submit_order(order_data=order_data)

        print("✅ Order submitted successfully!")
        print()
        print("=" * 60)
        print("📋 Order Details")
        print("=" * 60)
        print(f"Order ID: {order.id}")
        print(f"Client Order ID: {order.client_order_id}")
        print(f"Symbol: {order.symbol}")
        print(f"Quantity: {order.qty}")
        print(f"Side: {order.side}")
        print(f"Order Type: {order.order_type}")
        print(f"Status: {order.status}")
        print(f"Submitted At: {order.submitted_at}")

        if order.filled_at:
            print(f"Filled At: {order.filled_at}")
            print(f"Filled Qty: {order.filled_qty}")
            print(f"Filled Avg Price: ${order.filled_avg_price}")

        print()
        print("=" * 60)
        print("✅ Test Complete!")
        print("=" * 60)
        print()
        print("🎉 Your API keys are working correctly!")
        print("📊 You can view this order in your Alpaca dashboard:")
        print("   https://app.alpaca.markets/paper/dashboard/overview")
        print()
        print("Next steps:")
        print("  1. Check the order status in Alpaca dashboard")
        print("  2. Run 'uv run python create_order.py' to generate order files")
        print("  3. Build the order processor to handle file-based orders")
        print()

    except Exception as e:
        print("❌ Error occurred:")
        print(f"   {type(e).__name__}: {e}")
        print()
        print("Troubleshooting:")
        print("  - Verify API keys in .env file")
        print("  - Check https://app.alpaca.markets/paper/dashboard/overview")
        print("  - Ensure you're using paper trading keys (not live)")
        return

if __name__ == "__main__":
    main()
