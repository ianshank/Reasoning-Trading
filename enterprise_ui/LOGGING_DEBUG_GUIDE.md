# Logging and Debugging Utilities Guide

This guide explains how to use the comprehensive logging and debugging utilities for the enterprise UI.

## Backend (Python/FastAPI)

### 1. Structured Logging (`core/logging.py`)

#### Basic Usage

```python
from enterprise_ui.backend.core.logging import get_logger

logger = get_logger(__name__)

# Basic logging
logger.info("User logged in", user_id="123", session_id="abc")
logger.debug("Processing data", item_count=100)
logger.warning("Slow query detected", duration_ms=1500)
logger.error("Database connection failed", error=str(e))
```

#### Configuration

```python
from enterprise_ui.backend.core.logging import configure_logging
import logging

# Configure with custom settings
configure_logging(
    json_logs=True,  # Use JSON format (default in production)
    log_level=logging.DEBUG,  # Set log level
)
```

Environment-based configuration:
- `ENVIRONMENT=production` → JSON logs, WARNING level
- `ENVIRONMENT=development` → Console logs, DEBUG level
- `LOG_LEVEL=DEBUG` → Override log level explicitly

#### Request ID Tracking

```python
from enterprise_ui.backend.core.logging import set_request_id, clear_request_id

# In middleware or route handler
set_request_id(request_id)
try:
    # All logs will include this request_id
    logger.info("Processing request")
finally:
    clear_request_id()
```

#### Decorators

```python
from enterprise_ui.backend.core.logging import with_timing, with_logging

# Measure execution time
@with_timing
def process_data(data):
    # Function execution time will be logged
    return transform(data)

# Log function calls with args and results
@with_logging(log_args=True, log_result=True)
def calculate(x, y):
    return x + y
```

#### Log Context

```python
from enterprise_ui.backend.core.logging import LogContext

with LogContext(user_id="123", action="checkout"):
    logger.info("Starting checkout")
    process_payment()
    logger.info("Checkout complete")
    # All logs include user_id and action
```

### 2. Debugging Utilities (`core/debug.py`)

#### Debug Context

```python
from enterprise_ui.backend.core.debug import DebugContext

with DebugContext("database_query", query_type="SELECT", table="users"):
    result = db.execute(query)
    # Logs entry, exit, duration, and errors automatically
```

#### Performance Profiling

```python
from enterprise_ui.backend.core.debug import profile_function
from pstats import SortKey

@profile_function(sort_by=SortKey.CUMULATIVE, top_n=10)
def expensive_operation():
    # Function will be profiled with cProfile
    complex_calculation()
```

#### Memory Tracking

```python
from enterprise_ui.backend.core.debug import MemoryTracker

with MemoryTracker("data_processing") as tracker:
    large_data = load_large_dataset()
    process_data(large_data)

print(f"Peak memory: {tracker.peak_memory_mb}MB")
```

#### Request/Response Dumping

```python
from enterprise_ui.backend.core.debug import dump_request_response

with dump_request_response(
    request_data={"user_id": 123},
    operation="create_order"
) as dumper:
    response = create_order(user_id=123)
    dumper.set_response(response)
```

#### Trace Calls (Debug Mode Only)

```python
from enterprise_ui.backend.core.debug import trace_calls

@trace_calls
def complex_calculation(x, y):
    # In debug mode: logs entry with args, exit with result, and any exceptions
    return x * y + x / y
```

### 3. FastAPI Middleware (`middleware/logging_middleware.py`)

#### Setup

```python
from fastapi import FastAPI
from enterprise_ui.backend.middleware.logging_middleware import setup_middleware

app = FastAPI()

# Setup all logging middleware
setup_middleware(app, config={
    "exclude_paths": ["/health", "/metrics"],
    "log_request_body": False,  # Be careful with sensitive data
    "slow_request_threshold_ms": 1000.0,
    "very_slow_threshold_ms": 5000.0,
})
```

#### Manual Setup

```python
from enterprise_ui.backend.middleware.logging_middleware import (
    LoggingMiddleware,
    PerformanceLoggingMiddleware,
    RequestContextMiddleware,
)

# Add middleware manually
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    PerformanceLoggingMiddleware,
    slow_request_threshold_ms=1000.0,
)
app.add_middleware(
    LoggingMiddleware,
    exclude_paths=["/health"],
)
```

#### Features

- **Automatic request/response logging** with timing
- **Request ID generation** and propagation via `X-Request-ID` header
- **Performance monitoring** with slow request warnings
- **Error tracking** with full stack traces
- **Context binding** for all logs within a request

## Frontend (TypeScript/React)

### 1. Structured Logger (`lib/logger.ts`)

#### Basic Usage

```typescript
import { logger, createLogger, LogLevel } from '@/lib/logger';

// Basic logging
logger.info('User logged in', { userId: '123', timestamp: Date.now() });
logger.debug('Component rendered', { component: 'Dashboard' });
logger.warn('API slow response', { duration: 1500 });
logger.error('API request failed', new Error('Network error'));

// Create component-specific logger
const componentLogger = createLogger('Dashboard', { page: 'home' });
componentLogger.info('Dashboard loaded');
```

#### Configuration

```typescript
import { logger } from '@/lib/logger';

// Update configuration
logger.updateConfig({
  minLevel: LogLevel.DEBUG,
  enableConsole: true,
  enableRemote: true,
  remoteEndpoint: 'https://api.example.com/logs',
  maxBatchSize: 50,
  batchInterval: 5000,
});

// Set global context
logger.setGlobalContext({
  userId: currentUser.id,
  sessionId: sessionId,
  environment: 'production',
});
```

#### Performance Timing

```typescript
import { startTimer } from '@/lib/logger';

// Manual timing
const timer = startTimer('data_fetch', { endpoint: '/api/users' });
await fetchData();
timer.end(); // Logs duration automatically

// Method decorator
class DataService {
  @logTiming
  async fetchUsers() {
    // Method execution time will be logged
    return await api.get('/users');
  }
}
```

#### Child Loggers

```typescript
import { logger } from '@/lib/logger';

// Create logger with additional context
const authLogger = logger.child({ module: 'auth' });
authLogger.info('Login attempt'); // Includes module: 'auth'
```

### 2. Debug Utilities (`lib/debug.ts`)

#### Enable Debug Mode

```typescript
import { enableDebug, disableDebug, isDebugMode } from '@/lib/debug';

// Enable debug mode (persists in localStorage)
enableDebug();

// Check if debug mode is active
if (isDebugMode()) {
  console.log('Debug mode is active');
}

// Or via URL: ?debug=true
```

#### Performance Profiler

```typescript
import { debugUtils } from '@/lib/debug';

// Start performance measurement
debugUtils.performance.start('render-list');
renderComplexList();
debugUtils.performance.end('render-list');

// Get all measurements
const measurements = debugUtils.performance.getMeasurements();

// Print summary
debugUtils.performance.printSummary();
```

#### State Debugger

```typescript
import { debugUtils } from '@/lib/debug';

// Create state debugger
const stateDebugger = debugUtils.createStateDebugger('AppState');

// Capture state snapshots
stateDebugger.capture(currentState, 'after_user_action');

// Get state history
const snapshots = stateDebugger.getSnapshots();

// Compare states
const diff = stateDebugger.getDiff(0, 1);

// Export for analysis
const stateHistory = stateDebugger.export();
```

#### Network Debugger

```typescript
import { debugUtils } from '@/lib/debug';

// Log request
const requestId = debugUtils.network.logRequest(
  '/api/users',
  'GET',
  { params: { limit: 10 } }
);

// Log response
debugUtils.network.logResponse(
  '/api/users',
  200,
  responseData,
  duration
);

// Get failed requests
const failedRequests = debugUtils.network.getFailedRequests();

// Get slow requests
const slowRequests = debugUtils.network.getSlowRequests(1000);
```

#### Error Logging

```typescript
import { logComponentError } from '@/lib/debug';

// In error boundary
componentDidCatch(error: Error, errorInfo: ErrorInfo) {
  logComponentError(error, errorInfo, 'MyComponent');
}
```

#### Memory Tracking

```typescript
import { debugUtils } from '@/lib/debug';

// Capture memory snapshot
debugUtils.memory.capture('before_load');
await loadLargeData();
debugUtils.memory.capture('after_load');

// Print summary
debugUtils.memory.printSummary();
```

#### Global Debug Utilities

In development mode, debug utilities are available globally:

```javascript
// In browser console:
window.__debug.performance.printSummary();
window.__debug.network.getFailedRequests();
window.__debug.memory.printSummary();
window.__debug.logPagePerformance();
```

### 3. React Debugging Hook (`hooks/useDebug.ts`)

#### Basic Usage

```tsx
import { useDebug } from '@/hooks/useDebug';

function MyComponent({ userId, data }) {
  const debug = useDebug({
    component: 'MyComponent',
    logRenders: true,
    trackProps: true,
    measurePerformance: true,
  });

  useEffect(() => {
    debug.logRender('Component mounted with data', { dataSize: data.length });
  }, []);

  const handleAction = () => {
    debug.startMeasure('action-processing');
    processAction();
    debug.endMeasure('action-processing');
  };

  return <div onClick={handleAction}>...</div>;
}
```

#### State Tracking

```tsx
import { useStateWithDebug } from '@/hooks/useDebug';

function Counter() {
  // State changes are automatically logged
  const [count, setCount] = useStateWithDebug(0, 'count', 'Counter');

  return (
    <button onClick={() => setCount(c => c + 1)}>
      Count: {count}
    </button>
  );
}
```

#### Effect Debugging

```tsx
import { useEffectDebug } from '@/hooks/useDebug';

function DataComponent({ userId, filters }) {
  useEffectDebug(
    () => {
      fetchData(userId, filters);
    },
    [userId, filters],
    'fetch-data-effect',
    'DataComponent'
  );
  // Logs which dependencies changed and triggered the effect

  return <div>...</div>;
}
```

#### Performance Monitoring

```tsx
import { usePerformance } from '@/hooks/useDebug';

function ExpensiveComponent() {
  const perf = usePerformance('ExpensiveComponent');

  useEffect(() => {
    perf.mark('data-fetch-start');
    fetchData().then(() => {
      perf.mark('data-fetch-end');
      perf.measure('data-fetch', 'data-fetch-start', 'data-fetch-end');
    });
  }, []);

  return <div>...</div>;
}
```

#### Why Did You Update

```tsx
import { useWhyDidYouUpdate } from '@/hooks/useDebug';

function OptimizedComponent(props) {
  useWhyDidYouUpdate('OptimizedComponent', props);
  // Logs which props changed causing re-render

  return <div>...</div>;
}
```

## Best Practices

### Backend

1. **Use structured logging** - Always log with context:
   ```python
   logger.info("event_name", key1=value1, key2=value2)
   ```

2. **Set request IDs** - Use middleware for automatic request ID tracking

3. **Use decorators** - Apply `@with_timing` to performance-critical functions

4. **Environment-aware** - Let environment variables control log levels

5. **Don't log sensitive data** - Be careful with request/response bodies

### Frontend

1. **Use component loggers** - Create scoped loggers for better context:
   ```typescript
   const logger = createLogger('ComponentName');
   ```

2. **Debug mode only** - Expensive debugging only runs when enabled:
   ```typescript
   if (isDebugMode()) { /* expensive debug code */ }
   ```

3. **Clean up** - Destroy loggers when needed:
   ```typescript
   componentWillUnmount() {
     this.logger.destroy();
   }
   ```

4. **Batch remote logs** - Configure appropriate batch sizes for production

5. **Use hooks wisely** - Enable debugging hooks only during development

## Environment Variables

### Backend

- `ENVIRONMENT` - Environment name (production, staging, development, test)
- `LOG_LEVEL` - Explicit log level (DEBUG, INFO, WARNING, ERROR)
- `DEBUG` - Enable debug mode (true/false)

### Frontend

- `NODE_ENV` - Node environment (production, development)
- URL parameter `?debug=true` - Enable debug mode
- localStorage `debug=true` - Persist debug mode

## Integration Example

### Backend FastAPI Application

```python
from fastapi import FastAPI
from enterprise_ui.backend.core.logging import configure_logging
from enterprise_ui.backend.middleware.logging_middleware import setup_middleware

# Initialize logging
configure_logging()

# Create app
app = FastAPI()

# Setup middleware
setup_middleware(app)

# Your routes...
```

### Frontend React Application

```tsx
// app/layout.tsx
import { logger } from '@/lib/logger';

export default function RootLayout({ children }) {
  useEffect(() => {
    // Initialize logging
    logger.setGlobalContext({
      environment: process.env.NODE_ENV,
      version: process.env.APP_VERSION,
    });
  }, []);

  return <html>{children}</html>;
}

// components/Dashboard.tsx
import { useDebug } from '@/hooks/useDebug';

export function Dashboard(props) {
  const debug = useDebug({
    component: 'Dashboard',
    logRenders: true,
  });

  return <div>...</div>;
}
```

## Testing

Run the backend tests:

```bash
pytest enterprise_ui/backend/tests/unit/test_logging.py -v
```

## Dependencies

### Backend

- `structlog` - Structured logging
- `pytest` - Testing framework

### Frontend

No external dependencies required - uses standard browser APIs.
