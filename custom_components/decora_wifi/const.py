"""Constants for the Decora WiFi integration."""

from typing import Final

DOMAIN: Final = "decora_wifi"

# Configuration keys
CONF_DEVICE_OVERRIDES: Final = "device_overrides"

# Device types
DEVICE_TYPE_LIGHT: Final = "light"
DEVICE_TYPE_FAN: Final = "fan"
DEVICE_TYPE_AUTO: Final = "auto"

# Known fan model numbers (tested and confirmed working)
# Users can override other models to be treated as fans via options flow
KNOWN_FAN_MODELS: Final = ["DW4SF"]

# Fan speed settings
FAN_MIN_SPEED: Final = 25
FAN_MAX_SPEED: Final = 100
FAN_SPEED_STEP: Final = 25
FAN_SPEED_COUNT: Final = 4

# Ordered list of fan speeds (high to low for UI dropdown)
ORDERED_FAN_SPEEDS: Final = ["High", "Medium High", "Medium", "Low"]

# Speed to percentage mapping
SPEED_TO_PERCENTAGE: Final = {
    "Low": 25,
    "Medium": 50,
    "Medium High": 75,
    "High": 100,
}

# Percentage ranges for determining preset mode
PERCENTAGE_TO_SPEED: Final = [
    (30, "Low"),
    (55, "Medium"),
    (85, "Medium High"),
    (100, "High"),
]

# Polling interval (seconds)
UPDATE_INTERVAL: Final = 30

# Platforms
PLATFORMS: Final = ["light", "fan", "sensor", "number"]
