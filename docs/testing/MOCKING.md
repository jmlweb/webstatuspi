# Mocking GPIO, I2C, and OLED - WebStatusπ

Mock implementations for running WebStatusπ code without physical hardware.

## Environment Detection

Automatically detect whether code is running on Raspberry Pi or development machine.

```python
# hardware.py
import os
import sys
from typing import Tuple, Any

def detect_raspberry_pi() -> bool:
    """Detects if the code is running on Raspberry Pi"""
    # Method 1: Check /proc/cpuinfo
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo:
                return True
    except (FileNotFoundError, IOError):
        pass

    # Method 2: Check environment variable
    if os.getenv('RASPBERRY_PI', '').lower() == 'true':
        return True

    # Method 3: Try to import Pi-specific module
    try:
        import RPi
        return True
    except ImportError:
        pass

    return False

def get_platform_info() -> dict:
    """Gets information about the current platform"""
    return {
        'is_raspberry_pi': detect_raspberry_pi(),
        'platform': sys.platform,
        'python_version': sys.version
    }
```

## MockGPIO Class

Simulates RPi.GPIO behavior for development without hardware.

```python
# mock_gpio.py
"""Mock for RPi.GPIO for local testing"""

class MockGPIO:
    BCM = 'BCM'
    OUT = 'OUT'
    IN = 'IN'
    LOW = 0
    HIGH = 1

    def __init__(self):
        self.pins = {}
        self.mode = None

    def setmode(self, mode):
        self.mode = mode
        print(f"[MOCK] GPIO mode set to {mode}")

    def setup(self, pin, mode):
        self.pins[pin] = {'mode': mode, 'value': 0}
        print(f"[MOCK] GPIO pin {pin} set to {mode}")

    def output(self, pin, value):
        if pin in self.pins:
            self.pins[pin]['value'] = value
            print(f"[MOCK] GPIO pin {pin} set to {value}")

    def input(self, pin):
        return self.pins.get(pin, {}).get('value', 0)

    def cleanup(self):
        print("[MOCK] GPIO cleanup")
        self.pins.clear()
```

### Using MockGPIO

```python
# hardware.py
def get_gpio():
    """Returns real GPIO or mock depending on the environment"""
    if detect_raspberry_pi():
        import RPi.GPIO as GPIO
        return GPIO, True
    else:
        from mock_gpio import MockGPIO
        return MockGPIO(), False

# Usage
GPIO, is_real = get_gpio()
if not is_real:
    print("Running in mock mode - no real hardware connected")
```

## MockSSD1306 Class (OLED Display)

Simulates Adafruit SSD1306 OLED display.

```python
# mock_display.py
"""Mock for Adafruit SSD1306 OLED display"""

class MockSSD1306:
    def __init__(self, width, height, i2c):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.buffer = [[' ' for _ in range(width)] for _ in range(height)]
        print(f"[MOCK] OLED display initialized: {width}x{height}")

    def fill(self, color):
        """Fills the buffer with a color"""
        char = '#' if color else ' '
        self.buffer = [[char for _ in range(self.width)]
                       for _ in range(self.height)]
        print("[MOCK] Display filled")

    def text(self, text, x, y, color=1):
        """Writes text to the buffer"""
        if 0 <= y < self.height:
            for i, char in enumerate(text):
                if 0 <= x + i < self.width:
                    self.buffer[y][x + i] = char if color else ' '
        print(f"[MOCK] Text '{text}' at ({x}, {y})")

    def show(self):
        """Displays the buffer on console"""
        print("\n" + "=" * (self.width + 2))
        for row in self.buffer:
            print('|' + ''.join(row) + '|')
        print("=" * (self.width + 2) + "\n")

    def clear(self):
        """Clears the display"""
        self.fill(0)

    def display(self):
        """Alias for show() (compatibility)"""
        self.show()
```

## MockI2C Class

Simulates I2C bus for hardware communication.

```python
# mock_i2c.py
"""Mock for I2C bus"""

class MockI2C:
    def __init__(self):
        self.devices = {}
        print("[MOCK] I2C bus initialized")

    def scan(self):
        """Returns list of detected I2C addresses"""
        return list(self.devices.keys())

    def writeto(self, address, data):
        """Write data to I2C device"""
        self.devices[address] = data
        print(f"[MOCK] I2C write to 0x{address:02x}: {data}")

    def readfrom(self, address, nbytes):
        """Read data from I2C device"""
        data = self.devices.get(address, bytes(nbytes))
        print(f"[MOCK] I2C read from 0x{address:02x}: {nbytes} bytes")
        return data
```

## Display Manager

Factory function to get real or mock display.

```python
# display_manager.py
from typing import Optional

def get_display(width: int = 128, height: int = 64):
    """Gets the real display or mock depending on the environment"""
    try:
        # Try to import real modules
        import busio
        from board import SCL, SDA
        from adafruit_ssd1306 import SSD1306_I2C

        i2c = busio.I2C(SCL, SDA)
        display = SSD1306_I2C(width, height, i2c)
        return display, True
    except (ImportError, RuntimeError, OSError):
        # Use mock if hardware is not available
        from mock_display import MockSSD1306
        from mock_i2c import MockI2C

        i2c = MockI2C()
        display = MockSSD1306(width, height, i2c)
        return display, False
```

## HardwareConfig Dataclass

Configuration to control use of real hardware or mocks.

```python
# config.py
import os
from dataclasses import dataclass

@dataclass
class HardwareConfig:
    """Configuration to control use of real hardware or mocks"""
    mock_gpio: bool = False
    mock_display: bool = False
    mock_i2c: bool = False
    debug_mode: bool = False

    @classmethod
    def from_env(cls) -> 'HardwareConfig':
        """Creates configuration from environment variables"""
        return cls(
            mock_gpio=os.getenv('MOCK_GPIO', 'false').lower() == 'true',
            mock_display=os.getenv('MOCK_DISPLAY', 'false').lower() == 'true',
            mock_i2c=os.getenv('MOCK_I2C', 'false').lower() == 'true',
            debug_mode=os.getenv('DEBUG', 'false').lower() == 'true'
        )

# Usage
config = HardwareConfig.from_env()
if config.mock_gpio:
    from mock_gpio import MockGPIO
    GPIO = MockGPIO()
else:
    import RPi.GPIO as GPIO
```

## Best Practices

### 1. Separation of Concerns

- Keep business logic separate from hardware code
- Use interfaces/abstractions for hardware
- Facilitates replacing real implementations with mocks

### 2. Automatic Detection

- Automatically detect the environment (Pi vs. development)
- Use fallbacks to mocks when hardware is not available
- Avoid errors when running outside of Pi

### 3. Environment Variables

- Use environment variables for configuration
- Allows changing behavior without modifying code
- Facilitates different environments (dev, test, prod)
