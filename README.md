# Alpaca Exchange Tower

![Tests](https://img.shields.io/badge/tests-137%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-75.87%25-yellow)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

A file-based order processing system for [Alpaca Markets API](https://alpaca.markets/). Multiple AI agents can safely submit trades, query positions, and manage orders on a single Alpaca account by dropping JSON files into a watched folder.

---

## How It Works

```
  AI Agent                    Exchange Tower                  Alpaca API
  --------                    --------------                  ----------

1. Drop JSON file ──────>  orders/incoming/
                                  │
2.                         Validate filename + JSON
                                  │
3.                         Move to orders/processing/
                                  │
4.                         Send request ──────────────>  Execute trade / query
                                  │                              │
5.                         Receive response  <────────────────────
                                  │
6.                         Write response to:
                           responses/{agent}/{mode}/{date}/
                                  │
7.                         Move order file to:
                           orders/completed/  (success)
                           orders/failed/     (failure)
```

**The system monitors `orders/incoming/` for new `.json` files.** When a file appears, it is validated, processed against the Alpaca API, and the result is written back as a response file. The original order file is archived.

---

## Quick Start

### 1. Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and Setup

```bash
git clone https://github.com/vishnusurya11/alpaca_exchange_tower.git
cd alpaca_exchange_tower
```

### 3. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` and add your Alpaca API keys:

```bash
# Paper Trading (test mode - no real money)
ALPACA_PAPER_API_KEY=your_paper_key_here
ALPACA_PAPER_SECRET_KEY=your_paper_secret_here

# Live Trading (real money - use with caution)
ALPACA_LIVE_API_KEY=your_live_key_here
ALPACA_LIVE_SECRET_KEY=your_live_secret_here
```

Get your API keys from:
- **Paper Trading:** https://app.alpaca.markets/paper/dashboard/overview
- **Live Trading:** https://app.alpaca.markets/live/dashboard/overview

> **Never commit your `.env` file to git.** It is already in `.gitignore`.

### 4. Install Dependencies

```bash
uv sync
```

### 5. Start the Order Processor

```bash
uv run python order_processor.py
```

This starts watching `orders/incoming/` for new order files. Keep this running while agents submit orders. Directories are created automatically on startup.

---

## Folder Structure

```
alpaca_exchange_tower/
│
├── orders/
│   ├── incoming/        <── AI agents drop order files HERE (monitored folder)
│   ├── processing/      <── Temporary: file is here while being processed
│   ├── completed/       <── Archive of successfully processed orders
│   └── failed/          <── Archive of failed orders (for debugging)
│
├── responses/           <── Agents read their results HERE
│   └── {agent_id}/
│       └── {mode}/          (paper or live)
│           └── {YYYYMMDD}/  (date-based subfolders)
│               └── response_*.json
│
├── data/
│   └── processed_orders.txt  <── Ledger of processed orders (prevents duplicates)
│
└── logs/                <── System logs (daily rotation, 30-day retention)
```

---

## How to Place an Order

### Step 1: Create a JSON file with the correct filename

**Filename format:**

```
{mode}_{agentid}_{ordertype}_{timestamp}.json
```

| Part        | Rules                                                    | Examples                     |
|-------------|----------------------------------------------------------|------------------------------|
| `mode`      | `paper` or `live` (lowercase)                            | `paper`, `live`              |
| `agentid`   | Lowercase alphanumeric, 1-20 chars, no underscores       | `sentiment`, `bot1`, `alpha` |
| `ordertype` | One of the 13 supported types (see table below)          | `stockbuy`, `positions`      |
| `timestamp` | UTC, format `YYYYMMDDHHMMSSffffff` (exactly 20 digits)   | `20260213143022123456`       |

### Step 2: Write the JSON body

Every order file has this structure:

```json
{
  "agent_id": "youragentid",
  "client_order_id": "youragentid_20260213143022123456_ordertype",
  "order_type": "stockbuy",
  "mode": "paper",
  "payload": {
    // order-specific fields here
  }
}
```

> **Important:** The `mode`, `agent_id`, and `order_type` in the JSON **must match** the filename.

### Step 3: Drop the file into `orders/incoming/`

The processor picks it up automatically.

---

## Supported Order Types (13 Total)

### Trading Orders

| Order Type     | Description                              | Required Payload Fields                                        |
|----------------|------------------------------------------|----------------------------------------------------------------|
| `stockbuy`     | Buy equities                             | `symbol`, `qty`, `order_class`, `time_in_force`                |
| `stocksell`    | Sell equities                            | `symbol`, `qty`, `order_class`, `time_in_force`                |
| `cryptobuy`    | Buy cryptocurrency                       | `symbol`, `qty`, `order_class`, `time_in_force`                |
| `cryptosell`   | Sell cryptocurrency                      | `symbol`, `qty`, `order_class`, `time_in_force`                |
| `optionsingle` | Single-leg option trade                  | `symbol`, `qty`, `side`, `order_class`, `time_in_force`        |
| `optionmulti`  | Multi-leg option strategy                | `order_class`, `type`, `time_in_force`, `legs[]`               |

### Query & Management Orders

| Order Type    | Description                    | Required Payload Fields                |
|---------------|--------------------------------|----------------------------------------|
| `marketdata`  | Get quotes, bars, or trades    | `symbol` + data-specific fields        |
| `orderstatus` | Check a specific order's status| `client_order_id`                      |
| `openorders`  | List all open orders           | `status`, `limit`                      |
| `allorders`   | List all orders (with filters) | filter fields (optional)               |
| `positions`   | Get current positions with P&L | `asset_class` (optional)               |
| `accountinfo` | Get account details            | `{}` (empty payload)                   |
| `cancelorder` | Cancel an existing order       | `client_order_id`                      |

---

## Order Examples

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

### Sell Stock

**File:** `paper_sentiment_stocksell_20260213143024000000.json`

```json
{
  "agent_id": "sentiment",
  "client_order_id": "sentiment_20260213143024000000_stocksell",
  "order_type": "stocksell",
  "mode": "paper",
  "payload": {
    "symbol": "AAPL",
    "qty": 10,
    "order_class": "market",
    "time_in_force": "day"
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

---

## How to Query Orders, Positions & Account

Query orders work the same way as trading orders: drop a JSON file into `orders/incoming/` and read the response.

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

### Check a Specific Order's Status

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

### Get Current Positions

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

### Cancel an Order

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

---

## How to Read Status & Output

### Where to find responses

After an order is processed, the response file is written to:

```
responses/{agent_id}/{mode}/{YYYYMMDD}/response_{mode}_{agent_id}_{ordertype}_{timestamp}.json
```

**Example path:**

```
responses/sentiment/paper/20260213/response_paper_sentiment_stockbuy_20260213143022123456.json
```

Each agent only needs to watch its own folder: `responses/{agent_id}/`

### Success Response

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

### Error Response

```json
{
  "request_order_id": null,
  "agent_id": "sentiment",
  "client_order_id": "sentiment_20260213143022123456_stockbuy",
  "timestamp": "2026-02-13T14:30:25.789012Z",
  "status": "error",
  "data": null,
  "error": {
    "type": "validation_error",
    "message": "Invalid symbol",
    "details": {}
  }
}
```

### Response Fields

| Field              | Description                                              |
|--------------------|----------------------------------------------------------|
| `status`           | `"success"` or `"error"`                                 |
| `data`             | Alpaca API response data (null on error)                 |
| `error`            | Error details with `type`, `message`, `details` (null on success) |
| `client_order_id`  | Matches the original order for correlation               |
| `timestamp`        | When the order was processed (UTC)                       |

### Where the original order file ends up

| Outcome | Location             | Purpose                  |
|---------|----------------------|--------------------------|
| Success | `orders/completed/`  | Archive / audit trail    |
| Failure | `orders/failed/`     | Debugging failed orders  |

---

## CLI Helper Tool

Instead of writing JSON files by hand, use `create_order.py` to generate them:

```bash
# Buy 10 shares of AAPL (market order, paper mode)
uv run python create_order.py \
  --agent sentiment --mode paper --type stockbuy \
  --symbol AAPL --qty 10 --order-class market --tif day

# Sell 5 shares of TSLA (limit order)
uv run python create_order.py \
  --agent sentiment --mode paper --type stocksell \
  --symbol TSLA --qty 5 --order-class limit --limit-price 250.00 --tif gtc

# Buy crypto
uv run python create_order.py \
  --agent cryptobot --mode paper --type cryptobuy \
  --symbol BTCUSD --qty 0.01 --tif gtc

# Check positions
uv run python create_order.py \
  --agent portfolio --mode paper --type positions

# Check open orders
uv run python create_order.py \
  --agent monitor --mode paper --type openorders

# Get account info
uv run python create_order.py \
  --agent dashboard --mode paper --type accountinfo
```

By default, files are written to `orders/incoming/` (ready for processing). Use `--output-dir` to change the destination.

### Generate Sample Files

To generate example order files for all order types into the `examples/` folder:

```bash
uv run python generate_samples.py
```

---

## Multi-Agent Coordination

Each agent uses a unique `client_order_id` format:

```
{agentid}_{timestamp}_{ordertype}
```

**Example:** `sentiment_20260213143022123456_stockbuy`

This enables:
- **Agent attribution** - know which agent placed each order
- **Order tracking** - query all orders from a specific agent
- **Duplicate prevention** - the ledger (`data/processed_orders.txt`) prevents reprocessing
- **Performance analytics** - track P&L per agent

Multiple agents can safely operate on the same Alpaca account simultaneously.

---

## Rate Limits

- **200 requests/minute** across all agents on the same account
- **10 requests/second** burst limit
- The system handles queuing automatically

---

## Logs

System logs are written to `logs/` with:
- Daily rotation
- 30-day retention
- Logs are also printed to stdout when the processor runs

---

## Testing

### Run Tests

```bash
uv run pytest                    # All 137 tests
uv run pytest --cov              # With coverage report
uv run pytest -m unit            # Unit tests only (91 tests)
uv run pytest -m integration     # Integration tests only (10 tests)
uv run pytest -m e2e             # End-to-end tests only (12 tests)
```

### Test Structure

```
tests/
├── unit/                        # Fast, isolated component tests
│   ├── test_validators.py       # 38 tests
│   ├── test_ledger.py           # 26 tests
│   ├── test_response_writer.py  # 17 tests
│   └── test_alpaca_client.py    # 26 tests
├── integration/                 # Module interaction tests
│   └── test_order_pipeline.py   # 10 tests
└── e2e/                         # Complete workflow tests
    └── test_complete_workflow.py # 12 tests
```

See [TESTING.md](TESTING.md) for TDD guidelines and detailed testing docs.

---

## Development

```bash
# Install all dependencies
uv sync

# Format code
uv run black .
uv run ruff check --fix .

# Generate HTML coverage report
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

---

## Documentation

- [DESIGN.md](DESIGN.md) - Complete system architecture, all 13 order types with payload details, API endpoint mappings, error handling, and validation rules
- [TESTING.md](TESTING.md) - TDD workflow, testing guidelines, and fixture usage

---

## License

MIT

## Issues & Support

For bugs or questions, please open an issue on [GitHub](https://github.com/vishnusurya11/alpaca_exchange_tower/issues).

## Acknowledgments

Built with:
- [Alpaca Markets API](https://alpaca.markets/) - Commission-free trading API
- [alpaca-py](https://github.com/alpacahq/alpaca-py) - Official Python SDK
- [UV](https://github.com/astral-sh/uv) - Fast Python package manager
