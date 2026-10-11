"""Share structural status only; omit tokens, names, ids and school content."""
from .const import VERSION


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    return {"version": VERSION, "status": data.get("status", {}),
            "selected_relation_count": len(coordinator.children),
            "unmapped_counts": data.get("unmapped", {}),
            "collection_counts": {key: len(rows) for key, rows in data.get("items", {}).items()},
            "last_update_success": coordinator.last_update_success,
            "options": dict(entry.options)}
