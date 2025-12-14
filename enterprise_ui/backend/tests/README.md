# Backend Test Suite

Comprehensive test suite for the FastAPI backend of the Reasoning Trading Enterprise UI.

## Overview

This test suite provides thorough coverage of all backend components:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test API endpoints and service integration
- **Contract Tests**: Verify API contracts and backward compatibility
- **E2E Tests**: Test complete workflows from end to end
- **WebSocket Tests**: Test real-time communication

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures and configuration
├── pytest.ini                           # Pytest configuration
├── unit/
│   ├── test_models.py                  # Pydantic model tests
│   ├── test_services.py                # Service layer tests
│   └── test_logging.py                 # Logging tests
├── integration/
│   ├── test_trading_endpoints.py       # Trading API tests
│   ├── test_mcts_endpoints.py          # MCTS API tests
│   ├── test_portfolio_endpoints.py     # Portfolio API tests
│   └── test_websockets.py              # WebSocket tests
├── contract/
│   └── test_api_contracts.py           # API contract tests
└── e2e/
    └── test_trading_workflows.py       # End-to-end workflow tests
```

## Running Tests

### All Tests

```bash
pytest
```

### By Test Type

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Contract tests only
pytest -m contract

# E2E tests only
pytest -m e2e

# WebSocket tests only
pytest -m websocket
```

### Excluding Slow Tests

```bash
pytest -m "not slow"
```

### Specific Test File

```bash
pytest tests/unit/test_models.py
pytest tests/integration/test_trading_endpoints.py
```

### Specific Test

```bash
pytest tests/unit/test_models.py::TestTradingAnalysisRequest::test_valid_request
```

### With Coverage

```bash
# Generate coverage report
pytest --cov=enterprise_ui.backend --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.contract` - Contract tests
- `@pytest.mark.websocket` - WebSocket tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.asyncio` - Async tests

## Fixtures

### Application Fixtures

- `app` - FastAPI application instance
- `client` - Async HTTP test client
- `test_settings` - Test configuration

### Service Fixtures

- `trading_service` - TradingService with mocks
- `mcts_service` - MCTSService instance
- `portfolio_service` - PortfolioService instance
- `cache_service` - CacheService with fake Redis
- `mock_trading_adapter` - Mock trading adapter
- `mock_market_data` - Mock market data service

### Data Fixtures

- `sample_trading_analysis_request` - Sample analysis request
- `sample_trading_decision_request` - Sample decision request
- `sample_trade_execution_request` - Sample execution request
- `sample_portfolio_state` - Sample portfolio state
- `sample_trading_state` - Sample trading state
- `sample_mcts_result` - Sample MCTS result

## Writing New Tests

### Unit Test Example

```python
import pytest
from enterprise_ui.backend.models.requests import TradingAnalysisRequest

@pytest.mark.unit
def test_trading_analysis_request_validation():
    """Test request validation."""
    request = TradingAnalysisRequest(
        symbol="AAPL",
        include_news=True,
    )

    assert request.symbol == "AAPL"
    assert request.include_news is True
```

### Integration Test Example

```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyze_endpoint(client: AsyncClient):
    """Test analyze endpoint."""
    response = await client.post(
        "/api/v1/trading/analyze",
        json={
            "symbol": "AAPL",
            "current_price": 150.25,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
```

### E2E Test Example

```python
import pytest
from httpx import AsyncClient

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_trading_workflow(client: AsyncClient):
    """Test complete trading workflow."""
    # Step 1: Analyze
    analyze_response = await client.post(
        "/api/v1/trading/analyze",
        json={"symbol": "AAPL", "current_price": 150.25},
    )

    # Step 2: Decide
    decide_response = await client.post(
        "/api/v1/trading/decide",
        json={"symbol": "AAPL", "current_price": 150.25},
    )

    # Step 3: Execute
    execute_response = await client.post(
        "/api/v1/trading/execute",
        json={
            "symbol": "AAPL",
            "direction": "buy",
            "quantity": 10.0,
            "dry_run": True,
        },
    )

    assert execute_response.status_code in [200, 201]
```

## Best Practices

### 1. Use Fixtures

Don't create test data inline. Use fixtures for reusable test data:

```python
# Good
async def test_with_fixture(sample_portfolio_state):
    service = PortfolioService()
    await service.update_state(sample_portfolio_state)

# Avoid
async def test_without_fixture():
    state = PortfolioState(cash_balance=50000.0, ...)
    service = PortfolioService()
    await service.update_state(state)
```

### 2. Test Both Success and Failure Cases

```python
async def test_execute_trade_success(trading_service):
    """Test successful execution."""
    result = await trading_service.execute_trade(
        symbol="AAPL", side="buy", quantity=10.0
    )
    assert result.status == "filled"

async def test_execute_trade_invalid_quantity(trading_service):
    """Test execution with invalid quantity."""
    with pytest.raises(ValidationException):
        await trading_service.execute_trade(
            symbol="AAPL", side="buy", quantity=0.0
        )
```

### 3. Use Descriptive Test Names

```python
# Good
async def test_risk_check_rejects_oversized_position(portfolio_service):
    ...

# Avoid
async def test_risk_check(portfolio_service):
    ...
```

### 4. Keep Tests Independent

Each test should be able to run independently:

```python
# Good - test creates its own data
async def test_portfolio_state(portfolio_service):
    state = PortfolioState(cash_balance=100000.0, ...)
    await portfolio_service.update_state(state)
    ...

# Avoid - test depends on previous test
async def test_portfolio_state():
    # Assumes state from previous test
    ...
```

### 5. Use Appropriate Assertions

```python
# Good
assert response.status_code == 200
assert "symbol" in data
assert isinstance(data["symbol"], str)

# Avoid
assert response.status_code  # Too vague
assert data["symbol"]  # Doesn't verify type
```

## Continuous Integration

Tests run automatically on:

- Pull requests
- Commits to main branch
- Nightly builds

CI configuration:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Troubleshooting

### Tests Hanging

- Check for missing `await` on async functions
- Verify timeout settings in pytest.ini
- Use `pytest -vv` for more verbose output

### Import Errors

- Ensure backend package is installed: `pip install -e .`
- Check PYTHONPATH includes project root

### Async Test Failures

- Verify `@pytest.mark.asyncio` decorator is present
- Check `asyncio_mode = auto` in pytest.ini
- Ensure all async fixtures use `@pytest_asyncio.fixture`

### Mock Not Working

- Verify patch path is correct
- Use `autospec=True` for better mocking
- Check mock is applied before function call

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [HTTPX Async Client](https://www.python-httpx.org/async/)

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure all tests pass
3. Add appropriate markers
4. Update this README if needed
5. Maintain >80% code coverage
