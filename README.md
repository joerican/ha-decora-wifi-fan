# Leviton Decora Wi-Fi Fan Support

Custom Home Assistant integration for Leviton Decora Wi-Fi devices with **proper fan speed control**.

## Why This Exists

The core Home Assistant `decora_wifi` integration treats fan controllers as lights, sending brightness values (0-255) instead of actual fan speed percentages (0-100). This causes issues like 75% speed not working correctly.

This integration fixes that by:
- Detecting fan devices via `customType` field from myLeviton API or model number
- Sending proper speed percentages (25, 50, 75, 100) for fan control
- Using modern config entry pattern with UI setup
- Adding diagnostic sensors and configuration options

## Supported Devices

| Model | Type | Status |
|-------|------|--------|
| DW4SF | Fan Controller | Tested, working |
| D24SF | Fan Controller | Should work (untested) |
| DW6HD | Dimmer | Should work as light |
| Other | Various | Configurable via options |

## Features

- **UI-based setup** - No YAML configuration needed
- **Automatic fan detection** - Uses `customType` from myLeviton app or model number
- **Device type override** - Force any device to be treated as fan or light
- **Diagnostic sensors** (disabled by default):
  - WiFi signal strength
  - IP address
  - Last updated timestamp
- **Configuration entities**:
  - Preset level (default brightness/speed on turn-on)
  - LED brightness
  - Fade on/off time

## Installation

### Manual Installation

1. Copy `custom_components/decora_wifi` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "Decora WiFi"
5. Enter your myLeviton credentials

### HACS Installation (Coming Soon)

Add this repository as a custom repository in HACS.

## Configuration

### Device Type Override

If your fan isn't auto-detected:
1. In myLeviton app, set the device's "Custom Type" to "ceiling-fan"
2. Or use the integration's options flow to override device type

### Fan Speed Mapping

| Speed | Percentage | API Value |
|-------|------------|-----------|
| Low | 25% | 25 |
| Medium | 50% | 50 |
| Medium High | 75% | 75 |
| High | 100% | 100 |

## Comparison with Core Integration

| Feature | Core | This Integration |
|---------|------|------------------|
| Setup | YAML | UI Config Flow |
| Fan Support | Broken (uses brightness) | Fixed (uses speed %) |
| Fan Detection | None | Auto + Manual Override |
| Diagnostic Sensors | No | Yes |
| Config Options | No | Yes (LED, preset level) |

## Contributing

This is intended as a replacement/improvement for the core `decora_wifi` integration.
Feedback and testing with other Decora WiFi devices is welcome!

## Credits

- Based on [python-decora_wifi](https://github.com/tlyakhov/python-decora_wifi) library
- Inspired by [schmittx/home-assistant-leviton-decora-smart-wifi](https://github.com/schmittx/home-assistant-leviton-decora-smart-wifi)
