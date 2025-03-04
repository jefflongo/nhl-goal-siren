from typing import Any, Callable, Optional

# detect if running on Raspberry Pi, otherwise use dummy siren implementation
_RASPBERRY_PI = False
try:
    with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
        if "Raspberry Pi" in f.read():
            _RASPBERRY_PI = True
except FileNotFoundError:
    pass

if _RASPBERRY_PI:
    import RPi.GPIO as GPIO

    _SIREN_PIN = 14
    _BUTTON_PIN = 13
    _LED0_PIN = 6
    _LED1_PIN = 5
    _LED2_PIN = 0


def hardware_init() -> None:
    if _RASPBERRY_PI:
        GPIO.setmode(GPIO.BCM)


def hardware_deinit() -> None:
    if _RASPBERRY_PI:
        GPIO.cleanup()


class Siren:
    """A simple siren that can be enabled or disabled."""

    def __init__(self):
        if _RASPBERRY_PI:
            GPIO.setup(_SIREN_PIN, GPIO.OUT, initial=GPIO.LOW)

    def enable(self) -> None:
        if _RASPBERRY_PI:
            GPIO.output(_SIREN_PIN, GPIO.HIGH)

    def disable(self) -> None:
        if _RASPBERRY_PI:
            GPIO.output(_SIREN_PIN, GPIO.LOW)


class CycleUI:
    """A user interface containing a button and 3 LEDs. Pressing the button cycles through the four
    given `items` and calls the `on_change` callback with the current item.

    The UI LEDs indicates the current item by progressively illuminating the LEDs.
    """

    def __init__(
        self,
        items: tuple[Any, Any, Any, Any],
        start_item: int = 0,
        on_change: Optional[Callable[[Any], None]] = None,
    ):
        assert start_item < len(items)
        if _RASPBERRY_PI:
            leds = _LED0_PIN, _LED1_PIN, _LED2_PIN
            self._current = start_item

            def update_ui() -> None:
                led_states = [
                    GPIO.LOW if i < self._current else GPIO.HIGH
                    for i in range(len(leds))
                ]
                GPIO.output(leds, led_states)

            def on_button_press(_) -> None:
                self._current = (self._current + 1) % len(items)
                update_ui()

                if on_change is not None:
                    on_change(items[self._current])

            # set initial LED states
            GPIO.setup(leds, GPIO.OUT, initial=GPIO.HIGH)
            update_ui()

            # setup button interrupt
            GPIO.setup(_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.add_event_detect(
                _BUTTON_PIN, GPIO.RISING, on_button_press, bouncetime=200
            )
