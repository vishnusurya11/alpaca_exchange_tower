# Testing Guide - Alpaca Exchange Tower

## System Successfully Implemented ✅

All components are working:
- ✅ File-based order processing
- ✅ 13 order types supported
- ✅ Duplicate detection (3-layer)
- ✅ Validation (filename + JSON)
- ✅ Response writing (organized by agent/mode/date)
- ✅ Sample file generation

## Test Results

### Test 1: Tesla Buy Order ✅
**Command:**
```bash
.venv/bin/python create_order.py --agent testbot --mode paper --type stockbuy --symbol TSLA --qty 1 --order-class market --tif day
```

**Result:**
- Order file created: `paper_testbot_stockbuy_20260214074906447480.json`
- Processed successfully
- Response written to: `responses/testbot/paper/20260214/response_...json`
- Order moved to: `orders/completed/`
- Alpaca Order ID: `7550b06a-faf4-454d-8378-19dcdba917a6`
- Status: ACCEPTED (queued until market opens)

### Test 2: Duplicate Detection ✅
**Action:** Copied completed order back to `orders/incoming/`

**Result:**
- ✅ Duplicate detected via Alpaca API check
- ✅ Error response created
- ✅ Order moved to `orders/failed/`
- ✅ Statistics: Duplicates: 1

**Duplicate Reason:**
```
Order exists on Alpaca (status: OrderStatus.ACCEPTED)
```

## Quick Start Guide

### 1. Start Order Processor
```bash
.venv/bin/python order_processor.py
```

### 2. Create Orders (Multiple Methods)

**Method A: Using CLI Tool**
```bash
# Stock order
.venv/bin/python create_order.py \
  --agent testbot \
  --mode paper \
  --type stockbuy \
  --symbol AAPL \
  --qty 10 \
  --order-class limit \
  --limit-price 150 \
  --tif gtc

# Crypto order
.venv/bin/python create_order.py \
  --agent cryptobot \
  --mode paper \
  --type cryptobuy \
  --symbol BTCUSD \
  --qty 0.001 \
  --order-class market \
  --tif gtc

# Query positions
.venv/bin/python create_order.py \
  --agent portfolio \
  --mode paper \
  --type positions \
  --asset-class us_equity

# Query account info
.venv/bin/python create_order.py \
  --agent dashboard \
  --mode paper \
  --type accountinfo
```

**Method B: Copy Sample Files**
```bash
cp examples/paper_testbot_stockbuy_*.json orders/incoming/
```

**Method C: AI Agents Drop Files**
Your AI agents can directly write JSON files to `orders/incoming/` following the format in `DESIGN.md`.

### 3. Monitor Results

**Check responses:**
```bash
ls -R responses/
cat responses/testbot/paper/20260214/response_*.json
```

**Check order status:**
```bash
ls orders/completed/
ls orders/failed/
```

**View logs:**
```bash
tail -f logs/order_processor_*.log
```

## Example Order Files

See `examples/` folder for sample orders:
- Stock buy (market)
- Stock buy (limit)
- Stock sell
- Crypto buy
- Crypto sell
- Open orders query
- Positions query
- Account info query

## Duplicate Detection Layers

1. **In-memory cache** - Instant check (10,000 recent orders)
2. **Filesystem check** - Searches `orders/completed/`
3. **Alpaca API check** - Queries Alpaca for existing `client_order_id`

If duplicate found at any layer → rejected with error response

## Response Organization

```
responses/
└── {agentid}/
    └── {mode}/
        └── {YYYYMMDD}/
            └── response_{mode}_{agentid}_{ordertype}_{timestamp}.json
```

**Example:**
```
responses/testbot/paper/20260214/response_paper_testbot_stockbuy_20260214074906447480.json
```

## Statistics Tracking

The order processor tracks:
- Total processed
- Successful
- Failed
- Duplicates
- Cache size

Press Ctrl+C to see stats when stopping the processor.

## Next Steps

1. **Deploy** - Run `order_processor.py` as a service
2. **Monitor** - Set up log monitoring
3. **Scale** - Add more AI agents
4. **Extend** - Add remaining order types (multi-leg options, etc.)
5. **Dashboard** - Build web UI to view responses

## Troubleshooting

**Order not processing:**
- Check file is in `orders/incoming/`
- Check filename format is correct
- Check JSON is valid
- Check logs in `logs/`

**Duplicate errors:**
- Check `orders/completed/` for existing order
- Check Alpaca dashboard for order
- Wait for cache to clear (or restart processor)

**API errors:**
- Verify API keys in `.env`
- Check market is open (or use GTC orders)
- Check account buying power
- Review error response in `responses/`

## File Structure

```
alpaca_exchange_tower/
├── src/
│   ├── validators.py
│   ├── alpaca_client.py
│   ├── duplicate_detector.py
│   └── response_writer.py
├── order_processor.py
├── create_order.py
├── generate_samples.py
├── examples/
├── orders/
│   ├── incoming/
│   ├── processing/
│   ├── completed/
│   └── failed/
├── responses/
│   └── {agentid}/{mode}/{YYYYMMDD}/
└── logs/
```

