"""Authenticated on-demand weekly plans for the bundled card."""
from datetime import date

try:
    import probatio as vol
except ImportError:
    import voluptuous as vol

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.config_entries import ConfigEntryState
from homeassistant.components import websocket_api
from homeassistant.helpers import entity_registry as er

from .api import ZenbiError
from .const import DOMAIN
from .models import SchemaError


@websocket_api.websocket_command({
    vol.Required("type"): "zenbi/weekly_plans",
    vol.Required("config_entry_id"): str,
    vol.Required("week"): str,
})
@websocket_api.async_response
async def ws_weekly_plans(hass, connection, msg):
    """Fetch exactly one Monday-to-Monday week, respecting entity read access."""
    entry = hass.config_entries.async_get_entry(msg["config_entry_id"])
    coordinator = getattr(entry, "runtime_data", None)
    if not entry or entry.domain != DOMAIN or entry.state != ConfigEntryState.LOADED or coordinator is None:
        connection.send_error(msg["id"], "not_found", "Zenbi-kontoen er ikke indlæst.")
        return
    try:
        week = date.fromisoformat(msg["week"])
        if week.isoformat() != msg["week"] or week.weekday() != 0 or not 2000 <= week.year <= 2100:
            raise ValueError
    except ValueError:
        connection.send_error(msg["id"], "invalid_week", "Vælg en gyldig uge (mandagens dato).")
        return
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    allowed = {uid for uid in coordinator.children if any(
        entity.platform == DOMAIN and entity.unique_id.endswith(f":weekly_plans:{uid}")
        and connection.user.permissions.check_entity(entity.entity_id, POLICY_READ)
        for entity in entities)}
    if not allowed:
        connection.send_error(msg["id"], "unauthorized", "Ingen adgang til ugeplansentiteterne.")
        return
    try:
        result = await coordinator.async_weekly_plans(week)
    except (ZenbiError, SchemaError, KeyError, TypeError, ValueError):
        connection.send_error(msg["id"], "fetch_failed", "Ugeplanen kunne ikke hentes fra Zenbi.")
        return
    items = [{**item, "children": [uid for uid in item["children"] if uid in allowed]}
             for item in result["items"] if allowed.intersection(item["children"])]
    connection.send_result(msg["id"], {**result, "items": items})
