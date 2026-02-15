#!/usr/bin/env python3
"""
Generate sample order files for all 13 order types.
Creates examples in the examples/ folder for reference.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def generate_timestamp():
    """Generate timestamp in required format."""
    return datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')


def create_sample_files():
    """Create all sample order files."""
    examples_dir = Path("examples")
    examples_dir.mkdir(exist_ok=True)

    samples = []

    # 1. Stock Buy - Market Order
    timestamp = generate_timestamp()
    samples.append({
        "filename": f"paper_testbot_stockbuy_{timestamp}.json",
        "order": {
            "agent_id": "testbot",
            "client_order_id": f"testbot_{timestamp}_stockbuy",
            "order_type": "stockbuy",
            "mode": "paper",
            "payload": {
                "symbol": "TSLA",
                "qty": 1,
                "order_class": "market",
                "time_in_force": "day"
            }
        }
    })

    # 2. Stock Buy - Limit Order
    timestamp = generate_timestamp()
    samples.append({
        "filename": f"paper_testbot_stockbuy_{timestamp}.json",
        "order": {
            "agent_id": "testbot",
            "client_order_id": f"testbot_{timestamp}_stockbuy",
            "order_type": "stockbuy",
            "mode": "paper",
            "payload": {
                "symbol": "AAPL",
                "qty": 10,
                "order_class": "limit",
                "limit_price": 150.00,
                "time_in_force": "gtc"
            }
        }
    })

    # 3. Stock Sell
    timestamp = generate_timestamp()
    samples.append({
        "filename": f"paper_testbot_stocksell_{timestamp}.json",
        "order": {
            "agent_id": "testbot",
            "client_order_id": f"testbot_{timestamp}_stocksell",
            "order_type": "stocksell",
            "mode": "paper",
            "payload": {
                "symbol": "NVDA",
                "qty": 5,
                "order_class": "limit",
                "limit_price": 500.00,
                "time_in_force": "day"
            }
        }
    })

    # 4. Crypto Buy
    timestamp = generate_timestamp()
    samples.append({
        "filename": f"paper_cryptobot_cryptobuy_{timestamp}.json",
        "order": {
            "agent_id": "cryptobot",
            "client_order_id": f"cryptobot_{timestamp}_cryptobuy",
            "order_type": "cryptobuy",
            "mode": "paper",
            "payload": {
                "symbol": "BTCUSD",
                "qty": 0.001,
                "order_class": "market",
                "time_in_force": "gtc"
            }
        }
    })

    # 5. Crypto Sell
    timestamp = generate_timestamp()
    samples.append({
        "filename": f"paper_cryptobot_cryptosell_{timestamp}.json",
        "order": {
            "agent_id": "cryptobot",
            "client_order_id": f"cryptobot_{timestamp}_cryptosell",
            "order_type": "cryptosell",
            "mode": "paper",
            "payload": {
                "symbol": "ETHUSD",
                "qty": 0.01,
                "order_class": "limit",
                "limit_price": 3000.00,
                "time_in_force": "gtc"
            }
        }
    })

    # 6. Open Orders Query
    timestamp = generate_timestamp()
    samples.append({
        "filename": f"paper_monitor_openorders_{timestamp}.json",
        "order": {
            "agent_id": "monitor",
            "client_order_id": f"monitor_{timestamp}_openorders",
            "order_type": "openorders",
            "mode": "paper",
            "payload": {
                "status": "open",
                "limit": 100
            }
        }
    })

    # 7. Positions Query
    timestamp = generate_timestamp()
    samples.append({
        "filename": f"paper_portfolio_positions_{timestamp}.json",
        "order": {
            "agent_id": "portfolio",
            "client_order_id": f"portfolio_{timestamp}_positions",
            "order_type": "positions",
            "mode": "paper",
            "payload": {
                "asset_class": "us_equity"
            }
        }
    })

    # 8. Account Info Query
    timestamp = generate_timestamp()
    samples.append({
        "filename": f"paper_dashboard_accountinfo_{timestamp}.json",
        "order": {
            "agent_id": "dashboard",
            "client_order_id": f"dashboard_{timestamp}_accountinfo",
            "order_type": "accountinfo",
            "mode": "paper",
            "payload": {}
        }
    })

    # Write all samples
    for sample in samples:
        file_path = examples_dir / sample["filename"]
        with open(file_path, 'w') as f:
            json.dump(sample["order"], f, indent=2)
        print(f"✅ Created: {file_path}")

    # Create README
    readme_path = examples_dir / "README.md"
    with open(readme_path, 'w') as f:
        f.write("# Example Order Files\n\n")
        f.write("This folder contains sample order files for all supported order types.\n\n")
        f.write("## Usage\n\n")
        f.write("Copy any example file to `orders/incoming/` to test the order processor.\n\n")
        f.write("```bash\n")
        f.write("cp examples/paper_testbot_stockbuy_*.json orders/incoming/\n")
        f.write("```\n\n")
        f.write("## Order Types Included\n\n")
        for i, sample in enumerate(samples, 1):
            f.write(f"{i}. **{sample['order']['order_type']}** - {sample['filename']}\n")

    print(f"\n✅ Created README: {readme_path}")
    print(f"\n📊 Total sample files created: {len(samples)}")
    print(f"\n💡 To use these examples:")
    print(f"   cp examples/*.json orders/incoming/")


if __name__ == "__main__":
    create_sample_files()
