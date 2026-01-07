"""The Decora WiFi integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import DecoraWifiCoordinator

_LOGGER = logging.getLogger(__name__)

type DecoraWifiConfigEntry = ConfigEntry[DecoraWifiCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: DecoraWifiConfigEntry) -> bool:
    """Set up Decora WiFi from a config entry."""
    coordinator = DecoraWifiCoordinator(hass, entry)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator for platforms and options flow
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    # Register shutdown handler
    async def async_shutdown(event):
        """Handle shutdown."""
        await coordinator.async_shutdown()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_shutdown)
    )

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register listener for options updates
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    _LOGGER.info("Decora WiFi integration set up successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DecoraWifiConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Shutdown coordinator
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_shutdown()

        # Remove data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload the integration."""
    _LOGGER.debug("Options updated, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry - cleanup."""
    _LOGGER.debug("Removing Decora WiFi integration")
    # Any additional cleanup can go here
