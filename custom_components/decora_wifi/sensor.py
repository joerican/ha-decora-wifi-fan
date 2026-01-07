"""Sensor platform for Decora WiFi integration."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DecoraWifiConfigEntry
from .const import DOMAIN
from .entity import DecoraWifiEntity

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="rssi",
        name="WiFi signal",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="localIP",
        name="IP address",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="lastUpdated",
        name="Last updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecoraWifiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Decora WiFi sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[DecoraWifiSensor] = []

    # Add sensors for all devices
    for device in coordinator.data.get("devices", []):
        for description in SENSOR_DESCRIPTIONS:
            # Only add sensor if the device has this data
            if device["switch"].data.get(description.key) is not None:
                entities.append(
                    DecoraWifiSensor(coordinator, device, description)
                )

    async_add_entities(entities)


class DecoraWifiSensor(DecoraWifiEntity, SensorEntity):
    """Representation of a Decora WiFi sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator,
        device_info: dict[str, Any],
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_info)
        self.entity_description = description
        self._attr_unique_id = f"{self._serial}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        switch = self._get_switch()
        if switch is None:
            return None

        value = switch.data.get(self.entity_description.key)

        # Handle timestamp conversion for lastUpdated
        if self.entity_description.key == "lastUpdated" and value:
            try:
                # Parse ISO format: "2026-01-07T20:02:27.000Z"
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None

        return value
