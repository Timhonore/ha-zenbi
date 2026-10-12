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
    await _ws_week_data(hass, connection, msg, "weekly_plans")


@websocket_api.websocket_command({
    vol.Required("type"): "zenbi/timetable",
    vol.Required("config_entry_id"): str,
    vol.Required("week"): str,
})
@websocket_api.async_response
async def ws_timetable(hass, connection, msg):
    """Fetch school calendar points for the selected week."""
    await _ws_week_data(hass, connection, msg, "timetable")


async def _ws_week_data(hass, connection, msg, kind):
    """Only return rows belonging to children with readable source entities."""
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
    suffix = "calendar:child_calendar" if kind == "timetable" else "weekly_plans"
    allowed = {uid for uid in coordinator.children if any(
        entity.platform == DOMAIN and entity.unique_id.endswith(f":{suffix}:{uid}")
        and connection.user.permissions.check_entity(entity.entity_id, POLICY_READ)
        for entity in entities)}
    if not allowed:
        connection.send_error(msg["id"], "unauthorized", "Ingen adgang til børnenes kildeentiteter.")
        return
    try:
        result = await (coordinator.async_timetable(week) if kind == "timetable" else coordinator.async_weekly_plans(week))
    except (ZenbiError, SchemaError, KeyError, TypeError, ValueError):
        connection.send_error(msg["id"], "fetch_failed", "Ugens data kunne ikke hentes fra Zenbi.")
        return
    items = [{**item, "children": [uid for uid in item["children"] if uid in allowed]}
             for item in result["items"] if allowed.intersection(item["children"])]
    connection.send_result(msg["id"], {**result, "items": items})
