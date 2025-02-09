_RASPBERRY_PI_SIREN_PIN = 14

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


class Siren:
    def __init__(self):
        if _RASPBERRY_PI:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(_RASPBERRY_PI_SIREN_PIN, GPIO.OUT, initial=GPIO.LOW)

    def enable(self) -> None:
        if _RASPBERRY_PI:
            GPIO.output(_RASPBERRY_PI_SIREN_PIN, GPIO.HIGH)

    def disable(self) -> None:
        if _RASPBERRY_PI:
            GPIO.output(_RASPBERRY_PI_SIREN_PIN, GPIO.LOW)

    def shutdown(self) -> None:
        if _RASPBERRY_PI:
            GPIO.cleanup()
