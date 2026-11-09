# Presence light: turns the LED strip on when the radar sees someone
# and the room is dark, and fades it off when they leave.
#
# Wiring (from the schematic):
#   GPIO5  -> level shifter -> 330 ohm -> LED strip DIN
#   GPIO17 -> radar RX   (ESP32 sends)
#   GPIO16 <- radar TX   (ESP32 receives)
#   GPIO7  -> light sensor SCL
#   GPIO15 -> light sensor SDA

import time
import board
import busio
import neopixel
import adafruit_bh1750
import mmwave_presence as mmwave

# ---------------- settings: change these ----------------
NUM_LEDS = 120          # 2 m x 60 LEDs per metre
COLOR = (255, 180, 100) # warm white
MAX_BRIGHTNESS = 0.35    # 0 to 1. Keep at 0.4 or below: 120 warm-white LEDs at
                        # full brightness would pull about 5 A, more than the 3 A charger
DARK_LUX = 20           # room counts as dark below this many lux
HOLD_SECONDS = 30       # radar keeps reporting "someone here" this long after you vanish
FADE_SECONDS = 2.0      # time to fade fully on or off

pixels = neopixel.NeoPixel(board.IO5, NUM_LEDS, brightness=0, auto_write=False, pixel_order=neopixel.GRB)
pixels.fill(COLOR)
pixels.show()

i2c = busio.I2C(board.IO7, board.IO15)
light_sensor = adafruit_bh1750.BH1750(i2c)

uart = busio.UART(board.IO17, board.IO16, baudrate=mmwave.DEFAULT_BAUD, timeout=0.1)
radar = mmwave.MMWave(uart, engineering_always=False)

radar.set_basic_config(8, 8, HOLD_SECONDS)
print("Radar ready, presence timeout:", radar.presence_timeout, "s")

lights_on = False
brightness = 0.0
last_time = time.monotonic()

while True:
    radar.read()                 
    someone_here = radar.detected
    lux = light_sensor.lux

    if not lights_on and someone_here and lux < DARK_LUX:
        lights_on = True
    elif lights_on and not someone_here:
        lights_on = False

    now = time.monotonic()
    step = (now - last_time) / FADE_SECONDS * MAX_BRIGHTNESS
    last_time = now
    target = MAX_BRIGHTNESS if lights_on else 0.0
    if brightness < target:
        brightness = min(target, brightness + step)
    elif brightness > target:
        brightness = max(target, brightness - step)

    pixels.brightness = brightness
    pixels.show()

    print("someone:", someone_here, "distance:", radar.detection_cm, "cm",
          "lux:", round(lux), "lights:", lights_on, "brightness:", round(brightness, 2))