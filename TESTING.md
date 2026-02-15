# Testing Guidelines - Alpaca Exchange Tower

**Effective Date:** All new code starting February 14, 2026
**Coverage Target:** 80%+ minimum

---

## Test-Driven Development (TDD) Philosophy

This project follows strict TDD practices:

```
1. RED    → Write a failing test
2. GREEN  → Write minimal code to pass
3. REFACTOR → Improve while keeping tests green
```

---

## Project Testing Rules

### **RULE #1: Write Tests Before Code**

All new features and bug fixes MUST have tests written first.

**Workflow:**
1. Write failing test
2. Implement feature
3. Verify test passes
4. Refactor if needed

### **RULE #2: All Code Must Have Tests**

Every function and class needs:
- **Unit tests** - Isolated component testing
- **Integration tests** - Module interaction testing
- **E2E tests** - Complete workflow testing

### **RULE #3: 80%+ Code Coverage Required**

Run before every commit:
```bash
uv run pytest --cov
```

Target coverage by module:
- `src/validators.py` → 95%+
- `src/ledger.py` → 90%+
- `src/alpaca_client.py` → 85%+
- `src/response_writer.py` → 85%+
- `order_processor.py` → 80%+

### **RULE #4: No Commits Without Passing Tests**

```bash
# Must pass before commit
uv run pytest
```

---

## Running Tests

### Quick Commands

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Generate HTML coverage report
uv run pytest --cov --cov-report=html
open htmlcov/index.html

# Run specific test file
uv run pytest tests/unit/test_validators.py

# Run by marker
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m e2e

# Verbose output
uv run pytest -v

# Show slowest tests
uv run pytest --durations=10
```

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
│   ├── test_validators.py   (38 tests)
│   ├── test_ledger.py       (18 tests)
│   ├── test_response_writer.py (15 tests)
│   └── test_alpaca_client.py (20+ tests)
├── integration/             # Module interaction tests
│   └── test_order_pipeline.py
└── e2e/                     # Complete workflows
    └── test_complete_workflow.py
```

### Test Markers

```python
@pytest.mark.unit           # Fast unit tests
@pytest.mark.integration    # Integration tests
@pytest.mark.e2e            # End-to-end tests
@pytest.mark.slow           # Tests taking >1 second
```

---

## Writing Tests

### AAA Pattern (Arrange-Act-Assert)

```python
def test_ledger_records_order(temp_dir):
    # ARRANGE
    ledger = SimpleLedger(temp_dir / "ledger.txt")
    order_id = "testbot_20260214120000000000_stockbuy"

    # ACT
    ledger.record(order_id)

    # ASSERT
    assert ledger.contains(order_id) is True
```

### Using Fixtures

```python
def test_with_fixtures(temp_dir, valid_order_request, mock_trading_client):
    """Fixtures auto-injected from conftest.py"""
    ...
```

### Mocking External APIs

```python
from unittest.mock import patch

def test_alpaca_call(mock_env_vars, mock_trading_client):
    with patch('src.alpaca_client.TradingClient', return_value=mock_trading_client):
        client = AlpacaClient(mode="paper")
        result = client.process_order(...)
        mock_trading_client.submit_order.assert_called_once()
```

### Testing Exceptions

```python
def test_invalid_filename_raises_error():
    with pytest.raises(ValidationError, match="Invalid mode"):
        validate_filename("INVALID_file.json")
```

---

## TDD Workflow Example

```bash
# 1. Write failing test
# Edit tests/unit/test_validators.py

# 2. Verify it fails (RED)
uv run pytest tests/unit/test_validators.py::test_new_feature -v

# 3. Implement feature
# Edit src/validators.py

# 4. Verify it passes (GREEN)
uv run pytest tests/unit/test_validators.py::test_new_feature -v

# 5. Refactor if needed

# 6. Run all tests
uv run pytest

# 7. Check coverage
uv run pytest --cov

# 8. Commit
git add .
git commit -m "Add new validation feature"
```

---

## Available Fixtures (from conftest.py)

### Directory Fixtures
- `temp_dir` - Temporary directory
- `test_orders_dir` - Order directory structure
- `test_responses_dir` - Response directory
- `test_data_dir` - Data directory

### Data Fixtures
- `fixed_timestamp` - `"20260214120000000000"`
- `valid_stock_buy_payload`
- `valid_stock_sell_payload`
- `valid_crypto_buy_payload`
- `valid_option_single_payload`
- `valid_option_multi_payload`
- `valid_order_request` - Complete order

### Mock Fixtures
- `mock_env_vars` - Mock environment variables
- `mock_trading_client` - Mock Alpaca TradingClient
- `mock_alpaca_order_response`
- `mock_alpaca_account_response`

---

## Best Practices

### ✅ DO

- Write descriptive test names
- Test one thing per test
- Use fixtures to reduce duplication
- Mock external dependencies
- Keep tests fast (unit < 100ms)
- Run tests before every commit

### ❌ DON'T

- Skip writing tests
- Test implementation details
- Have tests depend on each other
- Use real API calls
- Commit failing tests
- Ignore coverage gaps

---

## Checking Coverage

```bash
# Terminal report
uv run pytest --cov --cov-report=term-missing

# HTML report (recommended)
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

Coverage shows:
- Lines executed
- Lines missed
- Branch coverage
- Per-file breakdown

---

## Pre-Commit Checklist

Before every commit:

- [ ] All tests pass (`uv run pytest`)
- [ ] Coverage ≥ 80% (`uv run pytest --cov`)
- [ ] No lint errors (`uv run ruff check .`)
- [ ] Code formatted (`uv run black .`)

---

## Common Patterns

### Parametrized Tests

```python
@pytest.mark.parametrize("mode,expected", [
    ("paper", True),
    ("live", True),
    ("invalid", False),
])
def test_mode_validation(mode, expected):
    result = is_valid_mode(mode)
    assert result == expected
```

### Time Mocking

```python
from freezegun import freeze_time

@freeze_time("2026-02-14 12:00:00")
def test_timestamp():
    ts = generate_timestamp()
    assert ts == "20260214120000000000"
```

---

## Troubleshooting

**Tests fail locally:**
- Clear cache: `rm -rf .pytest_cache`
- Check Python version
- Reinstall dependencies: `uv pip install -e .`

**Coverage not updating:**
- Delete `.coverage` and `htmlcov/`
- Run `uv run pytest --cov` again

**Tests are slow:**
- Use `pytest --durations=10`
- Mock external calls
- Mark slow tests with `@pytest.mark.slow`

---

**Remember: Tests are production code. Maintain them with the same rigor.**
