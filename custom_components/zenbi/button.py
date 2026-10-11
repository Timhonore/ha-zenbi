"""Manual refresh using the same rate-limited coordinator."""
from homeassistant.components.button import ButtonEntity
from .entity import ZenbiEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ZenbiRefresh(entry.runtime_data, "refresh", "Opdater")])


class ZenbiRefresh(ZenbiEntity, ButtonEntity):
    _attr_icon = "mdi:refresh"

    async def async_press(self):
        await self.coordinator.async_request_refresh()
