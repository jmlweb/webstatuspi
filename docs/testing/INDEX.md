# Testing Documentation - WebStatusPi

Testing strategies and tools for developing WebStatusPi without requiring physical Raspberry Pi hardware.

## Quick Reference

| Topic | Document | Lines |
|-------|----------|-------|
| GPIO/I2C/OLED Mocks | [MOCKING.md](MOCKING.md) | ~200 |
| Unit Tests & Pytest | [UNIT-TESTS.md](UNIT-TESTS.md) | ~150 |
| Docker/QEMU Emulation | [DOCKER-QEMU.md](DOCKER-QEMU.md) | ~100 |

## Environment Variables

```bash
# Force mock mode (development without hardware)
export MOCK_GPIO=true
export MOCK_DISPLAY=true
export MOCK_I2C=true

# Enable debug logging
export DEBUG=true
```

## Quick Start Commands

```bash
# Run with mocks
MOCK_GPIO=true MOCK_DISPLAY=true python3 main.py

# Run unit tests
python3 -m pytest tests/ -v

# Run tests with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# Run specific test
python3 -m pytest tests/test_monitor.py::TestMonitor::test_url_check_success
```

## Testing Dependencies

```
pytest>=7.0.0
pytest-mock>=3.10.0
coverage>=7.0.0
```

## Recommended Workflow

### 1. Local Development (without hardware)

```bash
export MOCK_GPIO=true MOCK_DISPLAY=true DEBUG=true
python3 main.py
python3 -m pytest tests/ -v
```

### 2. Validation with Mocks

```bash
MOCK_GPIO=true MOCK_DISPLAY=true python3 main.py --verbose
curl http://localhost:8080/
curl http://localhost:8080/status/Google
```

### 3. Test on Real Raspberry Pi

```bash
scp -r . pi@raspberrypi.local:/home/pi/webstatuspi/
ssh pi@raspberrypi.local
cd webstatuspi && python3 main.py
```

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture and design decisions
- [HARDWARE.md](../HARDWARE.md) - Hardware specifications and GPIO pin assignments
- [AGENTS.md](../../AGENTS.md) - Development rules and code conventions
