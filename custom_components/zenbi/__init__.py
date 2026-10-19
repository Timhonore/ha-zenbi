"""Zenbi Home Assistant integration."""
from pathlib import Path

import aiohttp

from homeassistant.const import Platform
from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import AuthenticationError, ZenbiClient, stored_auth
from .const import CONF_DEVICE_ID, DOMAIN
from .coordinator import ZenbiCoordinator
from .websocket import ws_timetable, ws_weekly_plans

PLATFORMS = [Platform.SENSOR, Platform.CALENDAR, Platform.BUTTON]


async def async_setup(hass, config):
    """Serve the bundled card once, also across entry reloads."""
    root = Path(__file__).parent
    await hass.http.async_register_static_paths([
        StaticPathConfig("/zenbi-card/zenbi-card.js", str(root / "frontend" / "zenbi-card.js"), False),
        StaticPathConfig("/zenbi-card/icon.png", str(root / "brand" / "icon.png"), True),
    ])
    websocket_api.async_register_command(hass, ws_weekly_plans)
    websocket_api.async_register_command(hass, ws_timetable)
    return True


async def async_setup_entry(hass, entry):
    def save_tokens(tokens):
        hass.config_entries.async_update_entry(entry, data={**entry.data, **tokens})

    client = ZenbiClient(async_create_clientsession(hass, cookie_jar=aiohttp.DummyCookieJar()), entry.data[CONF_DEVICE_ID],
                         stored_auth(entry.data), save_tokens)
    coordinator = ZenbiCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except AuthenticationError as err:
        raise ConfigEntryAuthFailed("Log ind på Zenbi igen") from err
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass, entry):
    # Rotating tokens updates entry.data too. Only options need a reload.
    coordinator = entry.runtime_data
    if dict(entry.options) != coordinator.options_snapshot:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
