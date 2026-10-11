"""Common entity naming and account device."""
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, DOMAIN, VERSION


class ZenbiEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}:{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.unique_id)},
            name=f"Zenbi {coordinator.school}", manufacturer="Zenbi",
            model="Skole/hjem", sw_version=VERSION, configuration_url=BASE_URL + "/home")
