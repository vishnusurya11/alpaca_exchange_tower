# Alpaca Exchange Tower - System Design

**Version:** 0.1.0
**Last Updated:** February 13, 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Filename Convention](#3-filename-convention)
4. [Order Types](#4-order-types)
5. [Validation Rules](#5-validation-rules)
6. [Folder Structure](#6-folder-structure)
7. [Request Format (JSON Schemas)](#7-request-format-json-schemas)
8. [Response Format](#8-response-format)
9. [Alpaca API Endpoints](#9-alpaca-api-endpoints)
10. [Multi-Agent Coordination](#10-multi-agent-coordination)
11. [Rate Limiting & Error Handling](#11-rate-limiting--error-handling)
12. [Complete Examples](#12-complete-examples)

---

## 1. Overview

**Alpaca Exchange Tower** is a file-based order processing system designed for multiple AI agents to submit trading orders to a single Alpaca Markets account.

### Key Features

- **File-based processing**: AI agents drop JSON order files, system processes automatically
- **Multi-agent safe**: Unique `client_order_id` per agent prevents conflicts
- **Asset support**: Stocks, options (single & multi-leg), and cryptocurrencies
- **Dual mode**: Paper trading for testing, live trading for production
- **13 order types**: Trading orders + market data queries + position management
- **Complete audit trail**: All orders archived with responses

### Design Philosophy

- **Simplicity**: File system as message queue (no database overhead)
- **Visibility**: Human-readable JSON files for easy debugging
- **Safety**: Strict validation, mode separation, double-checking
- **Scalability**: Rate limiting and queuing for high-volume scenarios

---

## 2. Architecture

### System Components

```
┌─────────────────┐
│   AI Agents     │
│  (sentiment,    │
│   momentum,     │
│   crypto, etc.) │
└────────┬────────┘
         │
         │ Drop order files
         ▼
┌─────────────────────────────┐
│  orders/incoming/           │
│  - Watched folder           │
└────────┬────────────────────┘
         │
         │ File detected
         ▼
┌─────────────────────────────┐
│  Order Processor            │
│  - Validates filename       │
│  - Validates JSON schema    │
│  - Routes to Alpaca API     │
│  - Handles rate limiting    │
└────────┬────────────────────┘
         │
         │ API call
         ▼
┌─────────────────────────────┐
│  Alpaca Markets API         │
│  - Paper: paper-api...      │
│  - Live: api.alpaca.markets │
└────────┬────────────────────┘
         │
         │ Response
         ▼
┌─────────────────────────────┐
│  Response Writer            │
│  - Creates response JSON    │
│  - Organizes by agent/mode  │
│  - Moves order to completed │
└─────────────────────────────┘
```

### Data Flow

1. **Agent creates order**: Generates JSON file with proper naming
2. **File monitoring**: Watchdog detects new file in `orders/incoming/`
3. **Validation**: Filename and JSON schema validated
4. **Processing**: File moved to `orders/processing/`
5. **API call**: Routed to appropriate Alpaca endpoint
6. **Response**: Result written to `responses/{agentid}/{mode}/{date}/`
7. **Archival**: Original order moved to `orders/completed/` or `orders/failed/`

---

## 3. Filename Convention

### Format

```
{mode}_{agentid}_{ordertype}_{timestamp}.json
```

**NO UUID** - The combination of `agentid` + `timestamp` (with microseconds) ensures uniqueness.

### Component Breakdown

| Component | Description | Format | Example |
|-----------|-------------|--------|---------|
| `mode` | Trading mode | `paper` or `live` (lowercase) | `paper` |
| `agentid` | Agent identifier | `[a-z0-9]{1,20}` (no underscores) | `sentiment` |
| `ordertype` | Type of order | One of 13 types (lowercase, no underscores) | `stockbuy` |
| `timestamp` | UTC timestamp | `YYYYMMDDHHMMSSffffff` (20 digits) | `20260213143022123456` |

### Filename Examples

```
paper_sentiment_stockbuy_20260213143022123456.json
live_momentum_cryptobuy_20260213143023456789.json
paper_optionbot_optionsingle_20260213143024789012.json
paper_riskbot_openorders_20260213143025012345.json
live_cryptobot_cryptosell_20260213143026345678.json
paper_monitor_positions_20260213143027678901.json
paper_dashboard_accountinfo_20260213143028901234.json
```

### Parsing Logic

```python
import re
from datetime import datetime

filename = "paper_sentiment_stockbuy_20260213143022123456.json"
parts = filename.replace('.json', '').split('_')

if len(parts) != 4:
    raise ValueError("Invalid filename format")

mode = parts[0]           # 'paper'
agent_id = parts[1]       # 'sentiment'
order_type = parts[2]     # 'stockbuy'
timestamp = parts[3]      # '20260213143022123456'

# Parse timestamp
dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S%f')
# 2026-02-13 14:30:22.123456
```

---

## 4. Order Types

### Complete List (13 Types)

#### Trading Orders (6 types)

| Order Type | Description | Assets |
|------------|-------------|--------|
| `stockbuy` | Buy stocks | US equities |
| `stocksell` | Sell stocks | US equities |
| `optionsingle` | Single-leg option trade | US options |
| `optionmulti` | Multi-leg option strategy | US options |
| `cryptobuy` | Buy cryptocurrency | BTC, ETH, etc. |
| `cryptosell` | Sell cryptocurrency | BTC, ETH, etc. |

#### Query/Management Orders (7 types)

| Order Type | Description | Returns |
|------------|-------------|---------|
| `marketdata` | Get quotes, bars, or trades | Market data |
| `orderstatus` | Check specific order status | Order details |
| `openorders` | Get all open orders | List of open orders |
| `allorders` | Get all orders (with filters) | List of orders |
| `positions` | Get current positions | List of positions |
| `accountinfo` | Get account details | Account info |
| `cancelorder` | Cancel an order | Cancellation status |

### Order Type Details

#### `stockbuy` / `stocksell`
- **Asset class**: US equities
- **Order classes**: market, limit, stop, stop_limit
- **Time in force**: day, gtc, ioc, fok
- **Supports**: Fractional shares

#### `optionsingle`
- **Asset class**: US options
- **Symbol format**: OCC format (e.g., `AAPL250321C00150000`)
- **Order classes**: market, limit
- **Sides**: buy, sell (to open or close)

#### `optionmulti`
- **Asset class**: US options (multi-leg)
- **Strategies**: Spreads, straddles, strangles, butterflies, condors
- **Order class**: mleg
- **Legs**: Array of option contracts with ratio quantities

#### `cryptobuy` / `cryptosell`
- **Asset class**: Cryptocurrencies
- **Symbols**: BTCUSD, ETHUSD, etc.
- **Order classes**: market, limit
- **Time in force**: Typically gtc

#### `marketdata`
- **Data types**: quote (bid/ask), bar (OHLCV), trade
- **Assets**: Stocks, crypto, options
- **Real-time**: Based on data subscription

#### `orderstatus`
- **Query by**: Alpaca order ID or client_order_id
- **Returns**: Full order details including fill status

#### `openorders`
- **Filter by**: Status (open), symbol, date range
- **Returns**: All open orders for the account

#### `allorders`
- **Filter by**: Status, symbol, date range, side
- **Returns**: Historical orders

#### `positions`
- **Filter by**: Asset class (us_equity, us_option, crypto)
- **Returns**: Current holdings with P&L

#### `accountinfo`
- **Returns**: Buying power, equity, cash, portfolio value

#### `cancelorder`
- **Cancel by**: Alpaca order ID or client_order_id
- **Returns**: Cancellation confirmation

---

## 5. Validation Rules

### Mode Validation

```python
ALLOWED_MODES = ['paper', 'live']
PATTERN = r'^(paper|live)$'

# Rules:
# - Must be lowercase
# - Exactly 'paper' or 'live'
# - No variations allowed
```

**Valid:** `paper`, `live`
**Invalid:** `PAPER`, `Live`, `paper_trading`, `test`

### Agent ID Validation

```python
PATTERN = r'^[a-z0-9]{1,20}$'

# Rules:
# - Lowercase letters (a-z) and digits (0-9) only
# - No underscores, hyphens, or special characters
# - Minimum length: 1 character
# - Maximum length: 20 characters
```

**Valid:** `sentiment`, `momentum1`, `rsi14`, `crypto`, `arb`
**Invalid:** `Sentiment`, `momentum_agent`, `rsi-14`, `long_short_equity`

### Order Type Validation

```python
ALLOWED_ORDER_TYPES = [
    'stockbuy', 'stocksell',
    'optionsingle', 'optionmulti',
    'cryptobuy', 'cryptosell',
    'marketdata', 'orderstatus', 'openorders', 'allorders',
    'positions', 'accountinfo', 'cancelorder'
]

PATTERN = r'^[a-z]+$'

# Rules:
# - Must be one of the 13 allowed types
# - Lowercase only
# - No underscores or special characters
```

**Valid:** `stockbuy`, `openorders`, `cryptosell`
**Invalid:** `stock_buy`, `StockBuy`, `buy_stock`

### Timestamp Validation

```python
PATTERN = r'^\d{20}$'
FORMAT = '%Y%m%d%H%M%S%f'

# Rules:
# - Exactly 20 digits
# - Format: YYYYMMDDHHMMSSffffff
# - Timezone: UTC
# - Includes microseconds (last 6 digits)

# Example: 20260213143022123456
# Year: 2026
# Month: 02
# Day: 13
# Hour: 14
# Minute: 30
# Second: 22
# Microseconds: 123456
```

**Generation:**
```python
from datetime import datetime

timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
# Returns: '20260213143022123456'
```

### Double Validation

The mode must match in **both** filename and JSON content:

```python
# Filename: paper_sentiment_stockbuy_20260213143022123456.json
# JSON content:
{
  "mode": "paper",  # MUST match filename prefix
  ...
}

# Validation:
filename_mode = filename.split('_')[0]  # 'paper'
json_mode = order_data['mode']          # 'paper'

if filename_mode != json_mode:
    raise ValidationError("Mode mismatch between filename and JSON")
```

---

## 6. Folder Structure

### Complete Directory Tree

```
alpaca_exchange_tower/
├── .git/
├── .gitignore
├── .env.example
├── .env                          # User creates, gitignored
├── pyproject.toml
├── README.md
├── DESIGN.md
│
├── orders/
│   ├── incoming/                 # AI agents drop files here
│   │   ├── paper_sentiment_stockbuy_20260213143022123456.json
│   │   ├── live_momentum_cryptobuy_20260213143023456789.json
│   │   └── paper_riskbot_openorders_20260213143024789012.json
│   │
│   ├── processing/               # Currently being processed
│   │   └── paper_sentiment_stockbuy_20260213143022123456.json
│   │
│   ├── completed/                # Successfully executed
│   │   ├── paper_sentiment_stockbuy_20260213143022123456.json
│   │   └── live_momentum_cryptobuy_20260213143023456789.json
│   │
│   └── failed/                   # Failed with errors
│       └── paper_badbot_stockbuy_20260213143025012345.json
│
├── responses/
│   ├── sentiment/                # Agent: sentiment
│   │   ├── paper/
│   │   │   ├── 20260213/
│   │   │   │   ├── response_paper_sentiment_stockbuy_20260213143022123456.json
│   │   │   │   └── response_paper_sentiment_openorders_20260213143030000000.json
│   │   │   └── 20260214/
│   │   │       └── response_paper_sentiment_stocksell_20260214090000000000.json
│   │   │
│   │   └── live/
│   │       └── 20260213/
│   │           └── response_live_sentiment_stockbuy_20260213144000000000.json
│   │
│   ├── momentum/                 # Agent: momentum
│   │   ├── paper/
│   │   │   └── 20260213/
│   │   └── live/
│   │       └── 20260213/
│   │           └── response_live_momentum_cryptobuy_20260213143023456789.json
│   │
│   └── riskbot/                  # Agent: riskbot
│       ├── paper/
│       │   └── 20260213/
│       │       └── response_paper_riskbot_positions_20260213143026000000.json
│       └── live/
│           └── 20260213/
│
├── logs/                         # System logs
│   ├── order_processor_20260213.log
│   ├── errors_20260213.log
│   └── archive/
│
└── config/                       # Configuration files
    ├── order_schemas.json        # JSON schemas for validation
    └── settings.json             # System settings
```

### Response Path Format

```
responses/{agentid}/{mode}/{YYYYMMDD}/response_{mode}_{agentid}_{ordertype}_{timestamp}.json
```

**Examples:**
- `responses/sentiment/paper/20260213/response_paper_sentiment_stockbuy_20260213143022123456.json`
- `responses/momentum/live/20260213/response_live_momentum_cryptobuy_20260213143023456789.json`
- `responses/riskbot/paper/20260213/response_paper_riskbot_openorders_20260213143024789012.json`

### Folder Purposes

| Folder | Purpose | Retention |
|--------|---------|-----------|
| `orders/incoming/` | Drop zone for new orders | Cleared immediately |
| `orders/processing/` | Currently being processed | Temporary (seconds) |
| `orders/completed/` | Successfully executed | Archive (configurable) |
| `orders/failed/` | Failed with errors | Archive for debugging |
| `responses/{agent}/{mode}/{date}/` | Execution results | Archive (configurable) |
| `logs/` | System logs | Rotate daily |
| `config/` | Configuration files | Permanent |

---

## 7. Request Format (JSON Schemas)

### Base Schema

All order files must include these fields:

```json
{
  "agent_id": "string (must match filename)",
  "client_order_id": "string (format: {agentid}_{timestamp}_{ordertype})",
  "order_type": "string (one of 13 types)",
  "mode": "string (paper|live, must match filename)",
  "payload": {}  // varies by order type
}
```

### 7.1 Stock Buy (`stockbuy`)

```json
{
  "agent_id": "sentiment",
  "client_order_id": "sentiment_20260213143022123456_stockbuy",
  "order_type": "stockbuy",
  "mode": "paper",
  "payload": {
    "symbol": "AAPL",
    "qty": 10,                    // Can be fractional (e.g., 0.5)
    "order_class": "market",      // market, limit, stop, stop_limit
    "limit_price": 150.00,        // Required if order_class = limit
    "stop_price": 145.00,         // Required if order_class = stop or stop_limit
    "time_in_force": "day"        // day, gtc, ioc, fok
  }
}
```

**Payload Fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `symbol` | Yes | string | Stock ticker (e.g., "AAPL", "TSLA") |
| `qty` | Yes | number | Quantity (supports fractional) |
| `order_class` | Yes | string | market, limit, stop, stop_limit |
| `limit_price` | Conditional | number | Required if limit or stop_limit |
| `stop_price` | Conditional | number | Required if stop or stop_limit |
| `time_in_force` | Yes | string | day, gtc, ioc, fok |

### 7.2 Stock Sell (`stocksell`)

```json
{
  "agent_id": "sentiment",
  "client_order_id": "sentiment_20260213143022123456_stocksell",
  "order_type": "stocksell",
  "mode": "paper",
  "payload": {
    "symbol": "AAPL",
    "qty": 10,
    "order_class": "limit",
    "limit_price": 155.00,
    "time_in_force": "gtc"
  }
}
```

**Same payload schema as `stockbuy`.**

### 7.3 Single-Leg Option (`optionsingle`)

```json
{
  "agent_id": "optionbot",
  "client_order_id": "optionbot_20260213143024789012_optionsingle",
  "order_type": "optionsingle",
  "mode": "paper",
  "payload": {
    "symbol": "AAPL250321C00150000",  // OCC format
    "qty": 1,
    "side": "buy",                     // buy or sell
    "order_class": "limit",            // market or limit
    "limit_price": 5.50,
    "time_in_force": "day"
  }
}
```

**OCC Symbol Format:**
- `AAPL` - Underlying symbol (padded to 6 chars with spaces if needed)
- `250321` - Expiration date (YYMMDD)
- `C` - Option type (C = Call, P = Put)
- `00150000` - Strike price (8 digits, 3 decimal places)

**Payload Fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `symbol` | Yes | string | OCC option symbol |
| `qty` | Yes | integer | Number of contracts |
| `side` | Yes | string | buy or sell |
| `order_class` | Yes | string | market or limit |
| `limit_price` | Conditional | number | Required if limit |
| `time_in_force` | Yes | string | day, gtc, ioc, fok |

### 7.4 Multi-Leg Option (`optionmulti`)

```json
{
  "agent_id": "spreadbot",
  "client_order_id": "spreadbot_20260213143025012345_optionmulti",
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

**Payload Fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `order_class` | Yes | string | Must be "mleg" |
| `type` | Yes | string | limit (stop not supported for multi-leg) |
| `limit_price` | Yes | number | Net debit/credit for strategy |
| `time_in_force` | Yes | string | day, gtc, ioc, fok |
| `legs` | Yes | array | Array of leg objects |

**Leg Object:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `symbol` | Yes | string | OCC option symbol |
| `side` | Yes | string | buy or sell |
| `ratio_qty` | Yes | integer | Quantity ratio (e.g., 1, 2) |

**Common Strategies:**
- **Vertical Spread**: Buy 1, sell 1 (different strikes, same expiry)
- **Straddle**: Buy call + buy put (same strike, same expiry)
- **Iron Condor**: 4 legs (2 credit spreads)

### 7.5 Crypto Buy (`cryptobuy`)

```json
{
  "agent_id": "cryptobot",
  "client_order_id": "cryptobot_20260213143023456789_cryptobuy",
  "order_type": "cryptobuy",
  "mode": "paper",
  "payload": {
    "symbol": "BTCUSD",               // BTCUSD, ETHUSD, etc.
    "qty": 0.01,
    "order_class": "market",
    "time_in_force": "gtc"            // Crypto typically uses gtc
  }
}
```

**Supported Crypto Symbols:**
- `BTCUSD` - Bitcoin
- `ETHUSD` - Ethereum
- `BCHUSD` - Bitcoin Cash
- `LTCUSD` - Litecoin
- `USDTUSD` - Tether
- And others supported by Alpaca

**Payload Fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `symbol` | Yes | string | Crypto pair (e.g., BTCUSD) |
| `qty` | Yes | number | Quantity (can be fractional) |
| `order_class` | Yes | string | market or limit |
| `limit_price` | Conditional | number | Required if limit |
| `time_in_force` | Yes | string | gtc recommended for crypto |

### 7.6 Crypto Sell (`cryptosell`)

```json
{
  "agent_id": "cryptobot",
  "client_order_id": "cryptobot_20260213143026345678_cryptosell",
  "order_type": "cryptosell",
  "mode": "paper",
  "payload": {
    "symbol": "BTCUSD",
    "qty": 0.01,
    "order_class": "limit",
    "limit_price": 45000.00,
    "time_in_force": "gtc"
  }
}
```

**Same payload schema as `cryptobuy`.**

### 7.7 Market Data (`marketdata`)

```json
{
  "agent_id": "databot",
  "client_order_id": "databot_20260213143026345678_marketdata",
  "order_type": "marketdata",
  "mode": "paper",
  "payload": {
    "symbols": ["AAPL", "TSLA", "BTCUSD"],
    "data_type": "quote"              // quote, bar, trade
  }
}
```

**Payload Fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `symbols` | Yes | array | List of symbols to query |
| `data_type` | Yes | string | quote, bar, or trade |

**Data Types:**
- `quote` - Latest bid/ask prices
- `bar` - Latest OHLCV bar
- `trade` - Latest trade price

### 7.8 Order Status (`orderstatus`)

```json
{
  "agent_id": "monitor",
  "client_order_id": "monitor_20260213143027678901_orderstatus",
  "order_type": "orderstatus",
  "mode": "paper",
  "payload": {
    "alpaca_order_id": "abc-123-def-456"
    // OR
    // "client_order_id": "sentiment_20260213143022123456_stockbuy"
  }
}
```

**Payload Fields (one required):**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `alpaca_order_id` | Either/or | string | Alpaca's order ID |
| `client_order_id` | Either/or | string | Your client order ID |

### 7.9 Open Orders (`openorders`)

```json
{
  "agent_id": "riskbot",
  "client_order_id": "riskbot_20260213143028901234_openorders",
  "order_type": "openorders",
  "mode": "paper",
  "payload": {
    "status": "open",                 // open, closed, all
    "limit": 100,                     // Max orders to return
    "symbols": ["AAPL", "TSLA"]       // Optional filter
  }
}
```

**Payload Fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `status` | No | string | open, closed, all (default: open) |
| `limit` | No | integer | Max results (default: 100) |
| `symbols` | No | array | Filter by symbols |

### 7.10 All Orders (`allorders`)

```json
{
  "agent_id": "monitor",
  "client_order_id": "monitor_20260213143029234567_allorders",
  "order_type": "allorders",
  "mode": "paper",
  "payload": {
    "status": "all",                  // open, closed, all
    "limit": 500,
    "after": "2026-02-01T00:00:00Z",  // Start date
    "until": "2026-02-13T23:59:59Z",  // End date
    "direction": "desc"               // asc or desc
  }
}
```

**Payload Fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `status` | No | string | open, closed, all |
| `limit` | No | integer | Max results (max: 500) |
| `after` | No | string | ISO 8601 timestamp |
| `until` | No | string | ISO 8601 timestamp |
| `direction` | No | string | asc or desc (default: desc) |

### 7.11 Positions (`positions`)

```json
{
  "agent_id": "portfolio",
  "client_order_id": "portfolio_20260213143029234567_positions",
  "order_type": "positions",
  "mode": "live",
  "payload": {
    "asset_class": "us_equity"        // Optional: us_equity, us_option, crypto
  }
}
```

**Payload Fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `asset_class` | No | string | us_equity, us_option, crypto |

### 7.12 Account Info (`accountinfo`)

```json
{
  "agent_id": "dashboard",
  "client_order_id": "dashboard_20260213143030567890_accountinfo",
  "order_type": "accountinfo",
  "mode": "paper",
  "payload": {}
}
```

**No payload fields required.**

### 7.13 Cancel Order (`cancelorder`)

```json
{
  "agent_id": "riskbot",
  "client_order_id": "riskbot_20260213143031890123_cancelorder",
  "order_type": "cancelorder",
  "mode": "paper",
  "payload": {
    "alpaca_order_id": "abc-123-def-456"
    // OR
    // "client_order_id": "sentiment_20260213143022123456_stockbuy"
  }
}
```

**Payload Fields (one required):**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `alpaca_order_id` | Either/or | string | Alpaca's order ID |
| `client_order_id` | Either/or | string | Your client order ID |

---

## 8. Response Format

### Response Filename

```
response_{mode}_{agentid}_{ordertype}_{timestamp}.json
```

**Examples:**
- `response_paper_sentiment_stockbuy_20260213143022123456.json`
- `response_live_momentum_cryptobuy_20260213143023456789.json`

### Response Location

```
responses/{agentid}/{mode}/{YYYYMMDD}/response_*.json
```

**Examples:**
- `responses/sentiment/paper/20260213/response_paper_sentiment_stockbuy_20260213143022123456.json`
- `responses/momentum/live/20260213/response_live_momentum_cryptobuy_20260213143023456789.json`

### Response Schema

```json
{
  "request_order_id": "string (from request)",
  "agent_id": "string",
  "client_order_id": "string",
  "timestamp": "ISO 8601 timestamp",
  "status": "success|error",
  "data": {},          // Full Alpaca API response (if success)
  "error": null        // Error details (if error)
}
```

### Success Response Example

```json
{
  "request_order_id": "abc123",
  "agent_id": "sentiment",
  "client_order_id": "sentiment_20260213143022123456_stockbuy",
  "timestamp": "2026-02-13T14:30:25.789012Z",
  "status": "success",
  "data": {
    "id": "61e69015-8549-4bfd-b9c3-01e75843f47d",
    "client_order_id": "sentiment_20260213143022123456_stockbuy",
    "created_at": "2026-02-13T14:30:22.500000Z",
    "updated_at": "2026-02-13T14:30:23.100000Z",
    "submitted_at": "2026-02-13T14:30:22.600000Z",
    "filled_at": "2026-02-13T14:30:23.000000Z",
    "expired_at": null,
    "canceled_at": null,
    "failed_at": null,
    "replaced_at": null,
    "replaced_by": null,
    "replaces": null,
    "asset_id": "904837e3-3b76-47ec-b432-046db621571b",
    "symbol": "AAPL",
    "asset_class": "us_equity",
    "notional": null,
    "qty": "10",
    "filled_qty": "10",
    "filled_avg_price": "149.75",
    "order_class": "simple",
    "order_type": "market",
    "type": "market",
    "side": "buy",
    "time_in_force": "day",
    "limit_price": null,
    "stop_price": null,
    "status": "filled",
    "extended_hours": false,
    "legs": null,
    "trail_percent": null,
    "trail_price": null,
    "hwm": null
  },
  "error": null
}
```

### Error Response Example

```json
{
  "request_order_id": "def456",
  "agent_id": "badbot",
  "client_order_id": "badbot_20260213143025012345_stockbuy",
  "timestamp": "2026-02-13T14:30:26.123456Z",
  "status": "error",
  "data": null,
  "error": {
    "code": "insufficient_funds",
    "message": "Insufficient buying power: required $1500.00, available $500.00"
  }
}
```

### Response Status Values

| Status | Description | Data Field | Error Field |
|--------|-------------|------------|-------------|
| `success` | Order executed successfully | Full Alpaca response | null |
| `error` | Order failed | null | Error details |

---

## 9. Alpaca API Endpoints

### Base URLs

| Mode | Base URL |
|------|----------|
| Paper Trading | `https://paper-api.alpaca.markets` |
| Live Trading | `https://api.alpaca.markets` |

### Authentication

**Headers:**
```
APCA-API-KEY-ID: {your_api_key}
APCA-API-SECRET-KEY: {your_secret_key}
```

### Endpoint Mapping

| Order Type | Alpaca Endpoint | HTTP Method | Notes |
|------------|----------------|-------------|-------|
| `stockbuy` | `/v2/orders` | POST | Set `side: buy` |
| `stocksell` | `/v2/orders` | POST | Set `side: sell` |
| `optionsingle` | `/v2/orders` | POST | Asset class: us_option |
| `optionmulti` | `/v2/orders` | POST | Set `order_class: mleg` |
| `cryptobuy` | `/v2/orders` | POST | Set `side: buy`, symbol: BTCUSD |
| `cryptosell` | `/v2/orders` | POST | Set `side: sell` |
| `orderstatus` (by ID) | `/v2/orders/{order_id}` | GET | Alpaca order ID |
| `orderstatus` (by client ID) | `/v2/orders:by_client_order_id` | GET | Query param: `client_order_id` |
| `openorders` | `/v2/orders` | GET | Query param: `status=open` |
| `allorders` | `/v2/orders` | GET | Optional filters |
| `positions` | `/v2/positions` | GET | Optional: `?asset_class=us_equity` |
| `accountinfo` | `/v2/account` | GET | No params |
| `cancelorder` (by ID) | `/v2/orders/{order_id}` | DELETE | Alpaca order ID |
| `cancelorder` (by client ID) | `/v2/orders:by_client_order_id` | DELETE | Query param: `client_order_id` |
| `marketdata` (stock quote) | `/v2/stocks/{symbol}/quotes/latest` | GET | Real-time quote |
| `marketdata` (crypto quote) | `/v2/crypto/us/latest/quotes` | GET | Query param: `symbols` |

### API Request Examples

#### Submit Stock Order
```http
POST /v2/orders HTTP/1.1
Host: paper-api.alpaca.markets
APCA-API-KEY-ID: your_key
APCA-API-SECRET-KEY: your_secret
Content-Type: application/json

{
  "symbol": "AAPL",
  "qty": 10,
  "side": "buy",
  "type": "market",
  "time_in_force": "day",
  "client_order_id": "sentiment_20260213143022123456_stockbuy"
}
```

#### Get Order by Client Order ID
```http
GET /v2/orders:by_client_order_id?client_order_id=sentiment_20260213143022123456_stockbuy HTTP/1.1
Host: paper-api.alpaca.markets
APCA-API-KEY-ID: your_key
APCA-API-SECRET-KEY: your_secret
```

#### Get Account Info
```http
GET /v2/account HTTP/1.1
Host: paper-api.alpaca.markets
APCA-API-KEY-ID: your_key
APCA-API-SECRET-KEY: your_secret
```

---

## 10. Multi-Agent Coordination

### client_order_id Format

```
{agentid}_{timestamp}_{ordertype}
```

**Examples:**
- `sentiment_20260213143022123456_stockbuy`
- `momentum_20260213143023456789_cryptobuy`
- `riskbot_20260213143024789012_openorders`

### Benefits

1. **Agent Attribution**: Know which agent placed each order
2. **Order Tracking**: Each agent can query their own orders
3. **Conflict Prevention**: Detect duplicate orders
4. **Performance Analytics**: Track P&L per agent
5. **Independent Operation**: Agents don't interfere with each other

### Querying Agent-Specific Orders

**Get all orders from sentiment agent:**
```python
# Filter by client_order_id prefix
all_orders = get_all_orders()
sentiment_orders = [
    o for o in all_orders
    if o['client_order_id'].startswith('sentiment_')
]
```

**Get all open orders from momentum agent:**
```python
open_orders = get_open_orders()
momentum_open = [
    o for o in open_orders
    if o['client_order_id'].startswith('momentum_')
]
```

### Agent Naming Best Practices

**Good Names:**
- `sentiment` - Strategy-based
- `momentum1` - Strategy with variant
- `rsi14` - Indicator-based with parameter
- `crypto` - Asset-based
- `arb` - Strategy abbreviation

**Avoid:**
- `sentiment_analyzer` - No underscores
- `Long-Short-Equity` - No hyphens, no capitals
- `ML_Model_V2` - No underscores, no capitals

### Shared Rate Limit

All agents share the same Alpaca account rate limit:
- **200 requests/minute**
- **10 requests/second** burst

The order processor will queue and throttle requests to stay within limits.

---

## 11. Rate Limiting & Error Handling

### Alpaca Rate Limits

| Limit Type | Value |
|------------|-------|
| Requests per minute | 200 |
| Requests per second (burst) | 10 |
| Applies to | Entire account (all agents) |

### Rate Limit Strategy

1. **Token Bucket Algorithm**
   - Bucket capacity: 200 tokens
   - Refill rate: 200 tokens/minute (~3.33/second)
   - Burst allowance: 10 tokens/second

2. **Queueing**
   - Orders queued if rate limit exceeded
   - FIFO processing
   - Priority for `cancelorder` requests

3. **Retry Logic**
   - 429 errors: Exponential backoff (1s, 2s, 4s, 8s)
   - Max retries: 5
   - Respect `Retry-After` header

### Error Categories

#### Validation Errors (Client-side)

| Error | Cause | Action |
|-------|-------|--------|
| Invalid filename | Doesn't match pattern | Move to `failed/`, create error response |
| Mode mismatch | Filename mode ≠ JSON mode | Move to `failed/`, create error response |
| Invalid agent_id | Contains underscores/capitals | Move to `failed/`, create error response |
| Unknown order_type | Not in allowed list | Move to `failed/`, create error response |
| Schema validation | Missing required fields | Move to `failed/`, create error response |

#### API Errors (Alpaca)

| HTTP Code | Error | Action |
|-----------|-------|--------|
| 400 | Bad Request | Return error to agent, move to `failed/` |
| 401 | Unauthorized | Check API keys, fail permanently |
| 403 | Forbidden | Check account permissions, fail permanently |
| 404 | Not Found | Order/symbol doesn't exist, return error |
| 422 | Unprocessable Entity | Invalid order parameters, return error |
| 429 | Too Many Requests | Retry with exponential backoff |
| 500 | Internal Server Error | Retry up to 3 times |
| 503 | Service Unavailable | Retry up to 3 times |

### Error Response Format

```json
{
  "request_order_id": "abc123",
  "agent_id": "badbot",
  "client_order_id": "badbot_20260213143025012345_stockbuy",
  "timestamp": "2026-02-13T14:30:26.123456Z",
  "status": "error",
  "data": null,
  "error": {
    "type": "validation_error|api_error|rate_limit_error",
    "code": "insufficient_funds",
    "message": "Insufficient buying power: required $1500.00, available $500.00",
    "details": {
      "required": 1500.00,
      "available": 500.00
    }
  }
}
```

### Logging

All errors logged to `logs/errors_{YYYYMMDD}.log`:

```
2026-02-13 14:30:26.123 [ERROR] [sentiment] Order validation failed: insufficient_funds
  File: paper_sentiment_stockbuy_20260213143022123456.json
  Error: Insufficient buying power: required $1500.00, available $500.00
  Action: Moved to failed/, created error response
```

---

## 12. Complete Examples

### Example 1: Buy 10 shares of AAPL at market price

**Order File:** `paper_sentiment_stockbuy_20260213143022123456.json`

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

**Response File:** `responses/sentiment/paper/20260213/response_paper_sentiment_stockbuy_20260213143022123456.json`

```json
{
  "request_order_id": "abc123",
  "agent_id": "sentiment",
  "client_order_id": "sentiment_20260213143022123456_stockbuy",
  "timestamp": "2026-02-13T14:30:25.789012Z",
  "status": "success",
  "data": {
    "id": "61e69015-8549-4bfd-b9c3-01e75843f47d",
    "client_order_id": "sentiment_20260213143022123456_stockbuy",
    "symbol": "AAPL",
    "qty": "10",
    "filled_qty": "10",
    "filled_avg_price": "149.75",
    "order_type": "market",
    "side": "buy",
    "status": "filled"
  },
  "error": null
}
```

### Example 2: Buy 0.01 BTC at market price

**Order File:** `paper_cryptobot_cryptobuy_20260213143023456789.json`

```json
{
  "agent_id": "cryptobot",
  "client_order_id": "cryptobot_20260213143023456789_cryptobuy",
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

**Response File:** `responses/cryptobot/paper/20260213/response_paper_cryptobot_cryptobuy_20260213143023456789.json`

```json
{
  "request_order_id": "xyz789",
  "agent_id": "cryptobot",
  "client_order_id": "cryptobot_20260213143023456789_cryptobuy",
  "timestamp": "2026-02-13T14:30:26.456789Z",
  "status": "success",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "client_order_id": "cryptobot_20260213143023456789_cryptobuy",
    "symbol": "BTCUSD",
    "qty": "0.01",
    "filled_qty": "0.01",
    "filled_avg_price": "44500.00",
    "order_type": "market",
    "side": "buy",
    "status": "filled"
  },
  "error": null
}
```

### Example 3: Buy call spread (multi-leg option)

**Order File:** `paper_spreadbot_optionmulti_20260213143025012345.json`

```json
{
  "agent_id": "spreadbot",
  "client_order_id": "spreadbot_20260213143025012345_optionmulti",
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

**Response File:** `responses/spreadbot/paper/20260213/response_paper_spreadbot_optionmulti_20260213143025012345.json`

```json
{
  "request_order_id": "mno456",
  "agent_id": "spreadbot",
  "client_order_id": "spreadbot_20260213143025012345_optionmulti",
  "timestamp": "2026-02-13T14:30:27.123456Z",
  "status": "success",
  "data": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "client_order_id": "spreadbot_20260213143025012345_optionmulti",
    "order_class": "mleg",
    "order_type": "limit",
    "limit_price": "2.00",
    "filled_avg_price": "1.95",
    "status": "filled",
    "legs": [
      {
        "symbol": "AAPL250321C00150000",
        "side": "buy",
        "qty": "1",
        "filled_qty": "1"
      },
      {
        "symbol": "AAPL250321C00155000",
        "side": "sell",
        "qty": "1",
        "filled_qty": "1"
      }
    ]
  },
  "error": null
}
```

### Example 4: Get all open orders

**Order File:** `paper_monitor_openorders_20260213143026345678.json`

```json
{
  "agent_id": "monitor",
  "client_order_id": "monitor_20260213143026345678_openorders",
  "order_type": "openorders",
  "mode": "paper",
  "payload": {
    "status": "open",
    "limit": 100
  }
}
```

**Response File:** `responses/monitor/paper/20260213/response_paper_monitor_openorders_20260213143026345678.json`

```json
{
  "request_order_id": "rst012",
  "agent_id": "monitor",
  "client_order_id": "monitor_20260213143026345678_openorders",
  "timestamp": "2026-02-13T14:30:28.456789Z",
  "status": "success",
  "data": [
    {
      "id": "order1",
      "client_order_id": "sentiment_20260213140000000000_stockbuy",
      "symbol": "TSLA",
      "qty": "5",
      "filled_qty": "0",
      "order_type": "limit",
      "limit_price": "200.00",
      "status": "new"
    },
    {
      "id": "order2",
      "client_order_id": "momentum_20260213141500000000_stockbuy",
      "symbol": "NVDA",
      "qty": "2",
      "filled_qty": "1",
      "order_type": "limit",
      "limit_price": "500.00",
      "status": "partially_filled"
    }
  ],
  "error": null
}
```

### Example 5: Get current positions

**Order File:** `paper_portfolio_positions_20260213143027678901.json`

```json
{
  "agent_id": "portfolio",
  "client_order_id": "portfolio_20260213143027678901_positions",
  "order_type": "positions",
  "mode": "paper",
  "payload": {
    "asset_class": "us_equity"
  }
}
```

**Response File:** `responses/portfolio/paper/20260213/response_paper_portfolio_positions_20260213143027678901.json`

```json
{
  "request_order_id": "uvw345",
  "agent_id": "portfolio",
  "client_order_id": "portfolio_20260213143027678901_positions",
  "timestamp": "2026-02-13T14:30:29.123456Z",
  "status": "success",
  "data": [
    {
      "asset_id": "904837e3-3b76-47ec-b432-046db621571b",
      "symbol": "AAPL",
      "exchange": "NASDAQ",
      "asset_class": "us_equity",
      "qty": "10",
      "avg_entry_price": "149.75",
      "side": "long",
      "market_value": "1500.00",
      "cost_basis": "1497.50",
      "unrealized_pl": "2.50",
      "unrealized_plpc": "0.0017",
      "current_price": "150.00",
      "lastday_price": "148.50",
      "change_today": "0.0101"
    }
  ],
  "error": null
}
```

---

## Appendix A: Quick Reference

### Filename Pattern
```
{mode}_{agentid}_{ordertype}_{timestamp}.json
```

### Response Path
```
responses/{agentid}/{mode}/{YYYYMMDD}/response_{mode}_{agentid}_{ordertype}_{timestamp}.json
```

### 13 Order Types
1. stockbuy
2. stocksell
3. optionsingle
4. optionmulti
5. cryptobuy
6. cryptosell
7. marketdata
8. orderstatus
9. openorders
10. allorders
11. positions
12. accountinfo
13. cancelorder

### Validation Regex
```python
MODE_PATTERN = r'^(paper|live)$'
AGENT_ID_PATTERN = r'^[a-z0-9]{1,20}$'
ORDER_TYPE_PATTERN = r'^[a-z]+$'
TIMESTAMP_PATTERN = r'^\d{20}$'
```

### Rate Limits
- 200 requests/minute
- 10 requests/second burst

---

**End of Design Document**
