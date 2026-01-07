"""Base entity for Decora WiFi integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DecoraWifiCoordinator


class DecoraWifiEntity(CoordinatorEntity[DecoraWifiCoordinator]):
    """Base class for Decora WiFi entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DecoraWifiCoordinator,
        device_info: dict,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_info = device_info
        self._serial = device_info["id"]
        self._switch = device_info["switch"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        # Get MAC address and format it properly (API returns "00-07-A6-18-36-7E")
        mac = self._switch.data.get("mac", "")
        if mac:
            mac = mac.replace("-", ":").lower()

        info = DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            name=self._device_info["name"],
            manufacturer="Leviton",
            model=self._device_info["model"] or "Decora WiFi",
            sw_version=self._switch.data.get("version"),
        )

        # Add MAC address as connection identifier if available
        if mac:
            info["connections"] = {(CONNECTION_NETWORK_MAC, mac)}

        return info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.last_update_success or self._switch is None:
            return False
        # Also check if device reports as connected
        return self._switch.data.get("connected", True)

    def _get_switch(self):
        """Get the current switch object from coordinator."""
        # Get fresh switch reference from coordinator data
        if self.coordinator.data:
            switches = self.coordinator.data.get("switches", {})
            if self._serial in switches:
                self._switch = switches[self._serial]
        return self._switch
