"""Number platform for Decora WiFi integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DecoraWifiConfigEntry
from .const import DOMAIN
from .entity import DecoraWifiEntity

_LOGGER = logging.getLogger(__name__)

NUMBER_DESCRIPTIONS: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key="presetLevel",
        name="Preset level",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key="dimLED",
        name="LED brightness",
        native_min_value=0,
        native_max_value=7,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key="fadeOnTime",
        name="Fade on time",
        native_min_value=0,
        native_max_value=255,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    NumberEntityDescription(
        key="fadeOffTime",
        name="Fade off time",
        native_min_value=0,
        native_max_value=255,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecoraWifiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Decora WiFi number entities based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[DecoraWifiNumber] = []

    # Add number entities for all devices
    for device in coordinator.data.get("devices", []):
        for description in NUMBER_DESCRIPTIONS:
            # Only add if the device has this data field
            if device["switch"].data.get(description.key) is not None:
                entities.append(
                    DecoraWifiNumber(coordinator, device, description)
                )

    async_add_entities(entities)


class DecoraWifiNumber(DecoraWifiEntity, NumberEntity):
    """Representation of a Decora WiFi configurable number."""

    entity_description: NumberEntityDescription

    def __init__(
        self,
        coordinator,
        device_info: dict[str, Any],
        description: NumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, device_info)
        self.entity_description = description
        self._attr_unique_id = f"{self._serial}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        switch = self._get_switch()
        if switch is None:
            return None
        return switch.data.get(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        switch = self._get_switch()
        if switch is None:
            return

        key = self.entity_description.key
        int_value = int(value)

        _LOGGER.debug(
            "Setting %s to %s for %s",
            key,
            int_value,
            self._device_info["name"],
        )

        def set_value():
            switch.update_attributes({key: int_value})

        await self.hass.async_add_executor_job(set_value)
        await self.coordinator.async_request_refresh()
