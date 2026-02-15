# Alpaca Exchange Tower

![Tests](https://img.shields.io/badge/tests-137%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-75.87%25-yellow)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

Multi-agent order processing system for Alpaca Markets API supporting stocks, options, and cryptocurrency trading.

## 🚀 Features

- 📁 **File-based order processing** - AI agents drop JSON files, system processes automatically
- 🤖 **Multi-agent coordination** - Unique `client_order_id` per agent for safe tracking
- 📊 **Stocks, Options, Crypto** - Trade equities, single/multi-leg options, and cryptocurrencies
- 🧪 **Paper & Live Trading** - Separate modes with different API keys
- ⚡ **13 Order Types** - Trading + market data queries + position management
- 🔒 **Strict Validation** - Filename and JSON schema validation
- 📝 **Complete Audit Trail** - All orders archived with responses
- ✅ **Test Coverage 75%+** - Comprehensive unit, integration, and E2E tests

## 📋 Order Types

### Trading Orders
- `stockbuy` / `stocksell` - Equity trading (market, limit, stop, stop_limit)
- `optionsingle` - Single-leg options
- `optionmulti` - Multi-leg strategies (spreads, straddles, butterflies, condors)
- `cryptobuy` / `cryptosell` - Cryptocurrency trading (BTC, ETH, etc.)

### Query Orders
- `marketdata` - Get quotes/bars/trades
- `orderstatus` - Check specific order status
- `openorders` - Get all open orders
- `allorders` - Get all orders (with filters)
- `positions` - Current positions with P&L
- `accountinfo` - Account details (buying power, equity, etc.)
- `cancelorder` - Cancel an order

## 🏗️ Folder Structure

```
alpaca_exchange_tower/
├── orders/
│   ├── incoming/       # AI agents drop order files here
│   ├── processing/     # Currently processing (temporary)
│   ├── completed/      # Successfully executed
│   └── failed/         # Failed with error details
├── responses/
│   └── {agentid}/      # Organized by agent ID
│       └── {mode}/     # paper or live
│           └── {YYYYMMDD}/  # Date-based folders
└── logs/               # System logs
```

## 🚦 Quick Start

### 1. Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone Repository

```bash
git clone https://github.com/vishnusurya11/alpaca_exchange_tower.git
cd alpaca_exchange_tower
```

### 3. Setup Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Alpaca API keys
# Get keys from: https://app.alpaca.markets/paper/dashboard/overview
```

### 4. Install Dependencies

```bash
uv sync
```

### 5. Create Folder Structure

```bash
mkdir -p orders/{incoming,processing,completed,failed}
mkdir -p responses logs config
```

### 6. Run Order Processor (Coming Soon)

```bash
uv run python order_processor.py
```

## 📝 Filename Convention

```
{mode}_{agentid}_{ordertype}_{timestamp}.json
```

### Rules

- **mode**: `paper` or `live` (lowercase)
- **agentid**: `[a-z0-9]{1,20}` - no underscores (e.g., `sentiment`, `momentum1`)
- **ordertype**: one of 13 types (e.g., `stockbuy`, `openorders`)
- **timestamp**: `YYYYMMDDHHMMSSffffff` - 20 digits with microseconds (UTC)

### Examples

```
paper_sentiment_stockbuy_20260213143022123456.json
live_cryptobot_cryptobuy_20260213143023456789.json
paper_monitor_openorders_20260213143024789012.json
```

## 📚 Example Orders

### Buy Stock (Market Order)

**File:** `paper_sentiment_stockbuy_20260213143022123456.json`

```json
{
  "agent_id": "sentiment",
  "client_order_id": "sentiment_20260213143022123456_stockbuy",
  "order_type": "stockbuy",
  "mode": "paper",
  "payload": {
    "symbol": "AAPL",
    "qty": 10,
    "order_class": "market",
    "time_in_force": "day"
  }
}
```

### Buy Stock (Limit Order)

**File:** `paper_sentiment_stockbuy_20260213143023456789.json`

```json
{
  "agent_id": "sentiment",
  "client_order_id": "sentiment_20260213143023456789_stockbuy",
  "order_type": "stockbuy",
  "mode": "paper",
  "payload": {
    "symbol": "TSLA",
    "qty": 5,
    "order_class": "limit",
    "limit_price": 200.00,
    "time_in_force": "gtc"
  }
}
```

### Buy Crypto

**File:** `paper_cryptobot_cryptobuy_20260213143024789012.json`

```json
{
  "agent_id": "cryptobot",
  "client_order_id": "cryptobot_20260213143024789012_cryptobuy",
  "order_type": "cryptobuy",
  "mode": "paper",
  "payload": {
    "symbol": "BTCUSD",
    "qty": 0.01,
    "order_class": "market",
    "time_in_force": "gtc"
  }
}
```

### Single-Leg Option

**File:** `paper_optionbot_optionsingle_20260213143025012345.json`

```json
{
  "agent_id": "optionbot",
  "client_order_id": "optionbot_20260213143025012345_optionsingle",
  "order_type": "optionsingle",
  "mode": "paper",
  "payload": {
    "symbol": "AAPL250321C00150000",
    "qty": 1,
    "side": "buy",
    "order_class": "limit",
    "limit_price": 5.50,
    "time_in_force": "day"
  }
}
```

### Multi-Leg Option (Call Spread)

**File:** `paper_spreadbot_optionmulti_20260213143026345678.json`

```json
{
  "agent_id": "spreadbot",
  "client_order_id": "spreadbot_20260213143026345678_optionmulti",
  "order_type": "optionmulti",
  "mode": "paper",
  "payload": {
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
}
```

### Check Open Orders

**File:** `paper_monitor_openorders_20260213143027678901.json`

```json
{
  "agent_id": "monitor",
  "client_order_id": "monitor_20260213143027678901_openorders",
  "order_type": "openorders",
  "mode": "paper",
  "payload": {
    "status": "open",
    "limit": 100
  }
}
```

### Get Positions

**File:** `paper_portfolio_positions_20260213143028901234.json`

```json
{
  "agent_id": "portfolio",
  "client_order_id": "portfolio_20260213143028901234_positions",
  "order_type": "positions",
  "mode": "paper",
  "payload": {
    "asset_class": "us_equity"
  }
}
```

### Get Account Info

**File:** `paper_dashboard_accountinfo_20260213143029234567.json`

```json
{
  "agent_id": "dashboard",
  "client_order_id": "dashboard_20260213143029234567_accountinfo",
  "order_type": "accountinfo",
  "mode": "paper",
  "payload": {}
}
```

### Check Order Status

**File:** `paper_monitor_orderstatus_20260213143030567890.json`

```json
{
  "agent_id": "monitor",
  "client_order_id": "monitor_20260213143030567890_orderstatus",
  "order_type": "orderstatus",
  "mode": "paper",
  "payload": {
    "client_order_id": "sentiment_20260213143022123456_stockbuy"
  }
}
```

### Cancel Order

**File:** `paper_riskbot_cancelorder_20260213143031890123.json`

```json
{
  "agent_id": "riskbot",
  "client_order_id": "riskbot_20260213143031890123_cancelorder",
  "order_type": "cancelorder",
  "mode": "paper",
  "payload": {
    "client_order_id": "sentiment_20260213143022123456_stockbuy"
  }
}
```

## 📤 Response Files

Responses are written to: `responses/{agentid}/{mode}/{YYYYMMDD}/`

**Example Path:**
```
responses/sentiment/paper/20260213/response_paper_sentiment_stockbuy_20260213143022123456.json
```

**Response Format:**

```json
{
  "request_order_id": "abc123",
  "agent_id": "sentiment",
  "client_order_id": "sentiment_20260213143022123456_stockbuy",
  "timestamp": "2026-02-13T14:30:25.789012Z",
  "status": "success",
  "data": {
    "id": "alpaca-order-abc-123",
    "symbol": "AAPL",
    "qty": "10",
    "filled_qty": "10",
    "filled_avg_price": "149.75",
    "status": "filled"
  },
  "error": null
}
```

## 🔑 API Keys

Get your Alpaca API keys:
- **Paper Trading:** https://app.alpaca.markets/paper/dashboard/overview
- **Live Trading:** https://app.alpaca.markets/live/dashboard/overview

⚠️ **Important:** Never commit your `.env` file to git. Use `.env.example` as a template.

## ⚡ Rate Limits

- **200 requests/minute**
- **10 requests/second** burst
- Shared across all agents on the same account
- System handles queuing and rate limiting automatically

## 🤖 Multi-Agent Coordination

Each agent uses a unique `client_order_id` format:

```
{agentid}_{timestamp}_{ordertype}
```

**Example:** `sentiment_20260213143022123456_stockbuy`

This allows:
- ✅ Agent attribution (know which agent placed each order)
- ✅ Order tracking (query all orders from a specific agent)
- ✅ Conflict prevention (detect duplicate orders)
- ✅ Performance analytics (track P&L per agent)

## 📖 Documentation

See [DESIGN.md](DESIGN.md) for:
- Complete system architecture
- Detailed validation rules
- All 13 order types with examples
- Alpaca API endpoint mappings
- Error handling strategies
- Multi-agent coordination details

## 🧪 Testing

This project follows **Test-Driven Development (TDD)** practices with comprehensive test coverage.

### Test Coverage

**Current Coverage: 75.87%** (Target: 80%+)

- ✅ 137 total tests
- ✅ 91 unit tests
- ✅ 10 integration tests
- ✅ 12 end-to-end tests

### Test Structure

```
tests/
├── unit/                    # Fast, isolated component tests
│   ├── test_validators.py   # 38 tests - validation logic
│   ├── test_ledger.py       # 26 tests - duplicate detection
│   ├── test_response_writer.py # 17 tests - file operations
│   └── test_alpaca_client.py # 26 tests - API integration
├── integration/             # Module interaction tests
│   └── test_order_pipeline.py # 10 tests
└── e2e/                     # Complete workflow tests
    └── test_complete_workflow.py # 12 tests
```

### Running Tests

```bash
# Install test dependencies (first time only)
uv pip install pytest pytest-cov pytest-mock freezegun

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific tests
uv run pytest tests/unit/test_validators.py
uv run pytest -m unit
uv run pytest -m integration
```

### TDD Workflow

All new features must follow the TDD cycle:

1. **RED** - Write a failing test first
2. **GREEN** - Write minimal code to pass the test
3. **REFACTOR** - Improve code while keeping tests green

### Testing Guidelines

See [TESTING.md](TESTING.md) for complete guidelines including:
- TDD philosophy and rules
- How to write tests
- Fixture usage
- Mocking strategies
- Pre-commit checklist

## 🛠️ Development

### Install Dev Dependencies

```bash
# Install all dependencies including test tools
uv sync

# Install test-specific dependencies
uv pip install pytest pytest-cov pytest-mock freezegun
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov

# Run specific test category
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m e2e           # End-to-end tests only

# Generate HTML coverage report
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

### Format Code

```bash
uv run black .
uv run ruff check --fix .
```

## 📄 License

MIT

## 🐛 Issues & Support

For bugs or questions, please open an issue on [GitHub](https://github.com/vishnusurya11/alpaca_exchange_tower/issues).

## 🙏 Acknowledgments

Built with:
- [Alpaca Markets API](https://alpaca.markets/) - Commission-free trading API
- [alpaca-py](https://github.com/alpacahq/alpaca-py) - Official Python SDK
- [UV](https://github.com/astral-sh/uv) - Fast Python package manager
