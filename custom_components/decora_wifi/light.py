"""Light platform for Decora WiFi integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DecoraWifiCoordinator
from .entity import DecoraWifiEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Decora WiFi lights from a config entry."""
    coordinator: DecoraWifiCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Get light devices from coordinator
    lights = coordinator.data.get("lights", [])

    entities = [DecoraWifiLight(coordinator, device) for device in lights]

    _LOGGER.info("Setting up %d Decora WiFi light entities", len(entities))
    async_add_entities(entities)


class DecoraWifiLight(DecoraWifiEntity, LightEntity):
    """Representation of a Decora WiFi light switch."""

    def __init__(
        self,
        coordinator: DecoraWifiCoordinator,
        device_info: dict,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator, device_info)
        self._attr_unique_id = self._serial
        self._attr_name = None  # Use device name

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        switch = self._get_switch()
        if switch and switch.canSetLevel:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {self.color_mode}

    @property
    def supported_features(self) -> LightEntityFeature:
        """Return supported features."""
        switch = self._get_switch()
        if switch and switch.canSetLevel:
            return LightEntityFeature.TRANSITION
        return LightEntityFeature(0)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        switch = self._get_switch()
        if switch:
            return int(switch.brightness * 255 / 100)
        return None

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        switch = self._get_switch()
        return switch.power == "ON" if switch else False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        switch = self._get_switch()
        if not switch:
            return

        attribs: dict[str, Any] = {"power": "ON"}

        if ATTR_BRIGHTNESS in kwargs:
            min_level = switch.data.get("minLevel", 0)
            max_level = switch.data.get("maxLevel", 100)
            brightness = int(kwargs[ATTR_BRIGHTNESS] * max_level / 255)
            brightness = max(brightness, min_level)
            attribs["brightness"] = brightness

        if ATTR_TRANSITION in kwargs:
            transition = int(kwargs[ATTR_TRANSITION])
            attribs["fadeOnTime"] = attribs["fadeOffTime"] = transition

        await self.hass.async_add_executor_job(switch.update_attributes, attribs)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        switch = self._get_switch()
        if switch:
            await self.hass.async_add_executor_job(
                switch.update_attributes, {"power": "OFF"}
            )
            await self.coordinator.async_request_refresh()
