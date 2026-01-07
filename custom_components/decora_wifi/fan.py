"""Fan platform for Decora WiFi integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    FAN_SPEED_COUNT,
    ORDERED_FAN_SPEEDS,
    PERCENTAGE_TO_SPEED,
    SPEED_TO_PERCENTAGE,
)
from .coordinator import DecoraWifiCoordinator
from .entity import DecoraWifiEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Decora WiFi fans from a config entry."""
    coordinator: DecoraWifiCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Get fan devices from coordinator
    fans = coordinator.data.get("fans", [])

    entities = [DecoraWifiFan(coordinator, device) for device in fans]

    _LOGGER.info("Setting up %d Decora WiFi fan entities", len(entities))
    async_add_entities(entities)


class DecoraWifiFan(DecoraWifiEntity, FanEntity):
    """Representation of a Decora WiFi fan controller."""

    _attr_preset_modes = ORDERED_FAN_SPEEDS
    _attr_speed_count = FAN_SPEED_COUNT
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        coordinator: DecoraWifiCoordinator,
        device_info: dict,
    ) -> None:
        """Initialize the fan."""
        super().__init__(coordinator, device_info)
        self._attr_unique_id = f"{self._serial}_fan"
        self._attr_name = None  # Use device name

    @property
    def is_on(self) -> bool:
        """Return true if fan is on."""
        switch = self._get_switch()
        return switch.power == "ON" if switch else False

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if not self.is_on:
            return 0
        switch = self._get_switch()
        return switch.brightness if switch else 0

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        if not self.is_on:
            return None

        switch = self._get_switch()
        if not switch:
            return None

        brightness = switch.brightness
        for threshold, mode in PERCENTAGE_TO_SPEED:
            if brightness <= threshold:
                return mode
        return "High"

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self._async_set_speed(50)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        switch = self._get_switch()
        if switch:
            await self.hass.async_add_executor_job(
                switch.update_attributes, {"power": "OFF"}
            )
            await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return

        # Map percentage to nearest valid fan speed (25, 50, 75, 100)
        if percentage <= 25:
            speed = 25
        elif percentage <= 50:
            speed = 50
        elif percentage <= 75:
            speed = 75
        else:
            speed = 100

        await self._async_set_speed(speed)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the fan preset mode."""
        speed = SPEED_TO_PERCENTAGE.get(preset_mode, 50)
        await self._async_set_speed(speed)

    async def _async_set_speed(self, speed: int) -> None:
        """Set the fan speed (25, 50, 75, or 100)."""
        switch = self._get_switch()
        if switch:
            _LOGGER.debug("Setting fan %s speed to %d", self._device_info["name"], speed)
            await self.hass.async_add_executor_job(
                switch.update_attributes, {"power": "ON", "brightness": speed}
            )
            await self.coordinator.async_request_refresh()
