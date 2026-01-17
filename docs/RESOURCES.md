# Learning Resources and Examples

This section provides essential tutorials and examples for beginners to understand the hardware concepts used in WebStatusPi.

For hardware specifications and GPIO pin assignments, see [HARDWARE.md](HARDWARE.md).

## Pull-up Resistors

The button connection requires a pull-up resistor (10kΩ between GPIO17 and 3.3V). This ensures the GPIO pin has a defined voltage when the button is not pressed.

**Essential resources**:
- [Raspberry Pi Using Pull-Up and Pull-Down Resistors](https://grantwinney.com/raspberry-pi-using-pullup-and-pulldown-resistors/) - Tutorial with examples and Python code
- [GPIO Internal Pull-Up/Pull-Down (Software Alternative)](https://gpiozero.readthedocs.io/en/stable/recipes.html#button) - Use software pull-up to eliminate external resistor

## I2C Protocol and OLED Display

The OLED display uses I2C (Inter-Integrated Circuit) protocol for communication. I2C requires two wires: SDA (data) and SCL (clock).

**Essential resources**:
- [Understanding I2C Protocol (SparkFun Tutorial)](https://learn.sparkfun.com/tutorials/i2c/all) - Learn how I2C works
- [SSD1306 OLED Displays with Raspberry Pi (Adafruit Tutorial)](https://learn.adafruit.com/ssd1306-oled-displays-with-raspberry-pi-and-beaglebone-black/usage) - Complete guide with wiring and Python code

## GPIO Basics

GPIO (General Purpose Input/Output) pins allow the Raspberry Pi to interact with external components.

**Essential resources**:
- [Raspberry Pi GPIO Pinout Guide](https://pinout.xyz/) - Interactive GPIO pin reference
- [GPIO Zero Library Documentation](https://gpiozero.readthedocs.io/) - Beginner-friendly GPIO library with examples

## LEDs with Current-Limiting Resistors

LEDs require a current-limiting resistor (330Ω in this project) to prevent damage to both the LED and GPIO pin.

**Essential resources**:
- [LED Resistor Calculator](https://www.digikey.com/en/resources/conversion-calculators/conversion-calculator-led-series-resistor) - Calculate resistor value for LEDs
- [Why LEDs Need Resistors (Electronics Tutorial)](https://www.electronics-tutorials.ws/diode/led-circuit.html) - Understand LED circuits

## Passive Buzzers and PWM

This project uses a passive buzzer, which requires PWM (Pulse Width Modulation) signals to generate different tones.

**Essential resources**:
- [Passive vs Active Buzzer Explained](https://www.instructables.com/How-to-Use-a-Buzzer-Arduino-Tutorial/) - Understand the difference
- [Raspberry Pi PWM Tutorial](https://www.raspberrypi-spy.co.uk/2012/07/software-based-pwm-on-raspberry-pi/) - Learn how PWM works

## Breadboard Basics

When prototyping, you'll likely use a breadboard to connect components.

**Essential resource**:
- [How Breadboards Work (SparkFun Tutorial)](https://learn.sparkfun.com/tutorials/how-to-use-a-breadboard/all) - Complete breadboard guide

## General Resources

**Official documentation and comprehensive guides**:
- [Raspberry Pi Official GPIO Guide](https://www.raspberrypi.org/documentation/usage/gpio/) - Official documentation
- [Adafruit Learning System - Raspberry Pi](https://learn.adafruit.com/category/raspberry-pi) - Step-by-step projects and tutorials

## Essential Concepts

- **Ground (GND)**: Common reference point (0V) that all components share
- **3.3V vs 5V**: GPIO pins output 3.3V logic; using 5V can damage them
- **Current limiting**: Always use resistors to limit current through LEDs and other components
- **Short circuits**: Never connect VCC directly to GND without a load (this causes damage)

## Safety Tips

- Always double-check connections before powering on
- Use appropriate resistor values to protect components
- Don't exceed GPIO pin current limits (~16mA per pin, ~50mA total)
- Disconnect power before making wiring changes
