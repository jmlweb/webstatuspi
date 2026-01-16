# Unit Tests - WebStatusPi

Unit testing strategies using `pytest` and `unittest.mock` without requiring hardware.

## Test Structure

```
tests/
├── __init__.py
├── test_monitor.py    # URL checking tests
├── test_db.py         # Database operation tests
├── test_api.py        # API endpoint tests
└── test_config.py     # Configuration loading tests
```

## Monitor Tests

Testing URL monitoring logic by mocking HTTP requests.

```python
# test_monitor.py
import unittest
from unittest.mock import Mock, patch
from datetime import datetime
import monitor
import db

class TestMonitor(unittest.TestCase):
    def setUp(self):
        """Setup before each test"""
        self.test_url = "https://example.com"
        self.db_path = ":memory:"  # In-memory database
        db.init_db(self.db_path)

    def test_url_check_success(self):
        """Test successful URL check"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_response.ok = True
            mock_get.return_value = mock_response

            result = monitor.check_url(self.test_url, timeout=10)

            self.assertTrue(result.success)
            self.assertEqual(result.status_code, 200)
            self.assertAlmostEqual(result.response_time, 500, delta=10)
            self.assertIsNone(result.error_message)

    def test_url_check_timeout(self):
        """Test timeout handling"""
        from requests.exceptions import Timeout

        with patch('requests.get') as mock_get:
            mock_get.side_effect = Timeout("Connection timeout")

            result = monitor.check_url(self.test_url, timeout=5)

            self.assertFalse(result.success)
            self.assertIsNone(result.status_code)
            self.assertIn("timeout", result.error_message.lower())

    def test_url_check_connection_error(self):
        """Test connection error handling"""
        from requests.exceptions import ConnectionError

        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")

            result = monitor.check_url(self.test_url, timeout=10)

            self.assertFalse(result.success)
            self.assertIn("connection", result.error_message.lower())

    def tearDown(self):
        """Cleanup after each test"""
        pass

if __name__ == '__main__':
    unittest.main()
```

## Database Tests

Testing SQLite operations using in-memory database.

```python
# test_db.py
import unittest
import sqlite3
import db
from datetime import datetime

class TestDatabase(unittest.TestCase):
    def setUp(self):
        """Setup with in-memory database"""
        self.db_path = ":memory:"
        db.init_db(self.db_path)

    def test_insert_check(self):
        """Test check insertion"""
        # Insert URL
        url_id = db.insert_url("Test URL", "https://test.com")

        # Insert check
        check_id = db.insert_check(
            url_id=url_id,
            status_code=200,
            success=True,
            response_time=123.45
        )

        self.assertIsNotNone(check_id)

        # Verify insertion
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM checks WHERE id = ?", (check_id,))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[2], url_id)  # url_id
        self.assertEqual(row[3], 200)     # status_code
        self.assertEqual(row[4], 1)       # success (True = 1)

    def test_get_stats(self):
        """Test statistics retrieval"""
        # Insert URL and checks
        url_id = db.insert_url("Test URL", "https://test.com")

        # Insert successful checks
        for _ in range(10):
            db.insert_check(url_id, 200, True, 100)

        # Insert failed checks
        for _ in range(2):
            db.insert_check(url_id, 500, False, 50, "Server Error")

        stats = db.get_stats(url_id)

        self.assertEqual(stats['total_requests'], 12)
        self.assertEqual(stats['total_failures'], 2)
        self.assertEqual(stats['last_status'], 'failure')

if __name__ == '__main__':
    unittest.main()
```

## Running Tests

```bash
# Run all tests
python3 -m pytest tests/

# Run tests with verbose output
python3 -m pytest tests/ -v

# Run tests with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# Run specific test file
python3 -m pytest tests/test_monitor.py

# Run specific test method
python3 -m pytest tests/test_monitor.py::TestMonitor::test_url_check_success

# Run tests matching pattern
python3 -m pytest tests/ -k "timeout"
```

## Logging Configuration for Tests

```python
# logging_config.py
import logging
import sys
from typing import Optional

def setup_logging(debug: bool = False, log_file: Optional[str] = None):
    """Configures the logging system"""
    level = logging.DEBUG if debug else logging.INFO

    log_format = '[%(asctime)s] %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized (level: {logging.getLevelName(level)})")
    return logger
```

### Logging Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: Normal events (checks, API requests)
- **WARNING**: Unexpected but manageable situations
- **ERROR**: Errors that affect functionality
- **CRITICAL**: Critical errors that may stop the system

## Test Scripts

### Quick Test Script

```bash
#!/bin/bash
# quick_test.sh

echo "Running quick tests..."

export MOCK_GPIO=true
export MOCK_DISPLAY=true

python3 -m pytest tests/ -v --tb=short

timeout 5 python3 main.py &
PID=$!
sleep 2

if curl -s http://localhost:8080/ > /dev/null; then
    echo "API responds correctly"
else
    echo "API not responding"
fi

kill $PID 2>/dev/null
echo "Quick test completed"
```

### Full Test Script

```bash
#!/bin/bash
# full_test.sh

set -e

echo "Running full test suite..."

[ -d "venv" ] && source venv/bin/activate

export MOCK_GPIO=true
export MOCK_DISPLAY=true
export DEBUG=true

echo "Running unit tests..."
python3 -m pytest tests/ -v --cov=. --cov-report=term-missing

echo "Running linter..."
python3 -m flake8 . --max-line-length=100

echo "Running type checker..."
python3 -m mypy . --ignore-missing-imports || true

echo "All tests passed!"
```

## Useful Tools

### For Local Development

- **pytest**: Testing framework
- **unittest.mock**: Dependency mocking
- **coverage**: Code coverage
- **black**: Code formatter
- **mypy**: Type checking

### For Raspberry Pi

- **htop**: Resource monitoring
- **iostat**: Disk I/O monitoring
- **curl**: API testing
- **sqlite3**: Database inspection
