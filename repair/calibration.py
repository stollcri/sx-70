""" Model S Camera Tester Calibration

The purpose of this software is to determine the correct pulse wave modulation
(PWM) settings for the particular LED which is installed in the camera tester.

This software is attempting to determine the PWM settings which would correlate
with luminance values (in candle/foot^2) specified in the comparalumen light
levels table of the SX-70 repair manual. It should be possible to create a rig
which performs this calibration without using an SX-70 camera - to determine
luminance we measure illumination at a fixed distance and calculate backwards -
here we are just using the SX-70 shutter assembly as the common fixture so that
it can be easily reproduced by others who have access to a SX-70 camera. This
calibration must be performed to account for the specific LED used to create
the Model S Camera Tester. The tester can be built by anyone with standard off-
the-shelf electronic components, but the selection of the LED and the specific
reflector construction would impact tester results without calibration.

This program assumes that the shutter assembly has been removed from the camera
and the electronic control module (ECM) has been removed from the shutter
assembly, the light sensor for the test rig is placed where the light sensor
for the camera would normally be located, the light emitter is installed in the
test location (over the external light sensor opening).
"""
import board
import math
import pwmio
import time
import adafruit_logging as logging
import adafruit_tsl2591


logger = logging.getLogger("test")
logger.setLevel(logging.INFO)

# luminance values from the SX-70 repair book
COMPARALUMEN_OFF = 6.25
COMPARALUMEN_LOW = 50
COMPARALUMEN_MED = 100
COMPARALUMEN_MAX = 800

# Use this value to get expected illumination from provided luminance
# see: http://www.ibiblio.org/pub/multimedia/3d/3d-photo/photometry
#
# 		 Eimage = (t pi B)/[4 N^2 (1+m)^2]
# where: Eimage is in foot-candles (divide by .0929 to get lux)
#           t   is the transmittance of the lens (usually .9 to .95 but lower
#                  for more surfaces in the lens or lack of anti-reflection
#                  coatings)
#           B   is the object luminance in candles/square foot
#           N   is the f-number of the lens
#           m   is the image magnification
TRANSMITTANCE = 0.95
LENS_F_NUMBER = 8.0
MAGNIFICATION = 0.0
TRANSMITTANCE_PI = TRANSMITTANCE * math.pi
CALC_DENOMINATOR = 4 * (LENS_F_NUMBER ** 2) * ((1 + MAGNIFICATION) ** 2)
EXPECTED_LUX_OFF = ((TRANSMITTANCE_PI * COMPARALUMEN_OFF) / CALC_DENOMINATOR) / 0.0929
EXPECTED_LUX_LOW = ((TRANSMITTANCE_PI * COMPARALUMEN_LOW) / CALC_DENOMINATOR) / 0.0929
EXPECTED_LUX_MED = ((TRANSMITTANCE_PI * COMPARALUMEN_MED) / CALC_DENOMINATOR) / 0.0929
EXPECTED_LUX_MAX = ((TRANSMITTANCE_PI * COMPARALUMEN_MAX) / CALC_DENOMINATOR) / 0.0929

# set tolerance limits for measurements
TEST_TOLERANCE = 0.08
EXPECTED_LUX_OFF_MIN = EXPECTED_LUX_OFF - (EXPECTED_LUX_OFF * TEST_TOLERANCE)
EXPECTED_LUX_OFF_MAX = EXPECTED_LUX_OFF + (EXPECTED_LUX_OFF * TEST_TOLERANCE)
EXPECTED_LUX_LOW_MIN = EXPECTED_LUX_LOW - (EXPECTED_LUX_LOW * TEST_TOLERANCE)
EXPECTED_LUX_LOW_MAX = EXPECTED_LUX_LOW + (EXPECTED_LUX_LOW * TEST_TOLERANCE)
EXPECTED_LUX_MED_MIN = EXPECTED_LUX_MED - (EXPECTED_LUX_MED * TEST_TOLERANCE)
EXPECTED_LUX_MED_MAX = EXPECTED_LUX_MED + (EXPECTED_LUX_MED * TEST_TOLERANCE)
EXPECTED_LUX_MAX_MIN = EXPECTED_LUX_MAX - (EXPECTED_LUX_MAX * TEST_TOLERANCE)
EXPECTED_LUX_MAX_MAX = EXPECTED_LUX_MAX + (EXPECTED_LUX_MAX * TEST_TOLERANCE)

logger.info(
    f"EXPECTED_LUX_OFF {EXPECTED_LUX_OFF} ({EXPECTED_LUX_OFF_MIN} - {EXPECTED_LUX_OFF_MAX})"
)
logger.info(
    f"EXPECTED_LUX_LOW {EXPECTED_LUX_LOW} ({EXPECTED_LUX_LOW_MIN} - {EXPECTED_LUX_LOW_MAX})"
)
logger.info(
    f"EXPECTED_LUX_MED {EXPECTED_LUX_MED} ({EXPECTED_LUX_MED_MIN} - {EXPECTED_LUX_MED_MAX})"
)
logger.info(
    f"EXPECTED_LUX_MAX {EXPECTED_LUX_MAX} ({EXPECTED_LUX_MAX_MIN} - {EXPECTED_LUX_MAX_MAX})"
)

LUX_LIMIT = EXPECTED_LUX_MAX_MAX * 2

led = pwmio.PWMOut(board.A0, frequency=5000, duty_cycle=0)

i2c = board.I2C()
sensor = adafruit_tsl2591.TSL2591(i2c)
sensor.gain = adafruit_tsl2591.GAIN_LOW
sensor.integration_time = adafruit_tsl2591.INTEGRATIONTIME_400MS


def scan(min_val, max_val, divisions):
    values_off = []
    values_low = []
    values_med = []
    values_max = []

    for i in range(divisions + 1):
        led.duty_cycle = int(min_val + ((i * (max_val - min_val)) / divisions))
        # sleep slightly longer than the sensor integration time
        time.sleep(0.5)
        current_lux = sensor.lux

        if i == 0:
            value_min = current_lux

        if EXPECTED_LUX_OFF_MIN < current_lux < EXPECTED_LUX_OFF_MAX:
            logger.debug(
                f"OFF {led.duty_cycle}: {current_lux}lux / {sensor.visible} / {sensor.infrared}"
            )
            values_off.append(led.duty_cycle)

        elif EXPECTED_LUX_LOW_MIN < current_lux < EXPECTED_LUX_LOW_MAX:
            logger.debug(
                f"LOW {led.duty_cycle}: {current_lux}lux / {sensor.visible} / {sensor.infrared}"
            )
            values_low.append(led.duty_cycle)

        elif EXPECTED_LUX_MED_MIN < current_lux < EXPECTED_LUX_MED_MAX:
            logger.debug(
                f"MED {led.duty_cycle}: {current_lux}lux / {sensor.visible} / {sensor.infrared}"
            )
            values_med.append(led.duty_cycle)

        elif EXPECTED_LUX_MAX_MIN < current_lux < EXPECTED_LUX_MAX_MAX:
            logger.debug(
                f"MAX {led.duty_cycle}: {current_lux}lux / {sensor.visible} / {sensor.infrared}"
            )
            values_max.append(led.duty_cycle)

        if current_lux > LUX_LIMIT:
            logger.info(
                f"Light level ({current_lux}) exceeds allowed limit ({LUX_LIMIT})"
            )
            break

    return (value_min, values_off, values_low, values_med, values_max)


def median(lst):
    n = len(lst)
    s = sorted(lst)
    return (sum(s[n // 2 - 1 : n // 2 + 1]) / 2.0, s[n // 2])[n % 2] if n else None


logger.info("Finding value ranges ...")
(value_min, values_off, values_low, values_med, values_max) = scan(0, 65535, 100)

if (
    value_min < EXPECTED_LUX_OFF_MAX
    and len(values_low) > 0
    and len(values_med) > 0
    and len(values_max) > 0
):
    if len(values_off) > 0:
        logger.info("Refining range for OFF ...")
        if max(values_off) - min(values_off) > 20:
            (_, _, values_off, _, _) = scan(min(values_off), max(values_off), 20)
        values_off = int(median(values_off))
    else:
        if len(values_off) <= 0:
            logger.warning(f"No light level range found for off ({COMPARALUMEN_OFF})")
        values_off = None

    logger.info("Refining range for LOW ...")
    if max(values_low) - min(values_low) > 20:
        (_, _, values_low, _, _) = scan(min(values_low), max(values_low), 20)
    values_low = int(median(values_low))
    
    logger.info("Refining range for MED ...")
    if max(values_med) - min(values_med) > 20:
        (_, _, _, values_med, _) = scan(min(values_med), max(values_med), 20)
    values_med = int(median(values_med))

    logger.info("Refining range for MAX ...")
    if max(values_max) - min(values_max) > 20:
        (_, _, _, _, values_max) = scan(min(values_max), max(values_max), 20)
    values_max = int(median(values_max))

    print(f"PWM setting for off ({COMPARALUMEN_OFF}) = {values_off}")
    print(f"PWM setting for low ({COMPARALUMEN_LOW}) = {values_low}")
    print(f"PWM setting for med ({COMPARALUMEN_MED}) = {values_med}")
    print(f"PWM setting for max ({COMPARALUMEN_MAX}) = {values_max}")

else:
    if value_min > EXPECTED_LUX_OFF_MAX:
        logger.error(
            f"Ambient light level exceeds allowed limit {EXPECTED_LUX_OFF_MAX}"
        )
    if len(values_low) <= 0:
        logger.error(f"No light level range found for low ({COMPARALUMEN_LOW})")
    if len(values_med) <= 0:
        logger.error(f"No light level range found for med ({COMPARALUMEN_MED})")
    if len(values_max) <= 0:
        logger.error(f"No light level range found for max ({COMPARALUMEN_MAX})")
