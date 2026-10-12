"""Counts and bounded plain-text item attributes."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import ZenbiEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    entities = [ZenbiSensor(coordinator, "unread", "Ulæste beskeder"),
                ZenbiSensor(coordinator, "messages", "Beskeder"),
                ZenbiSensor(coordinator, "posts", "Opslag"),
                ZenbiSensor(coordinator, "homework", "Alle lektier"),
                ZenbiSensor(coordinator, "tasks", "Alle opgaver"),
                ZenbiSensor(coordinator, "status", "Datastatus")]
    for uid, child in coordinator.children.items():
        for kind, title in (("homework", "Lektier"), ("tasks", "Opgaver"), ("weekly_plans", "Ugeplaner")):
            entities.append(ZenbiSensor(coordinator, kind, f"{child['name']} {title}", uid))
    async_add_entities(entities)


class ZenbiSensor(ZenbiEntity, SensorEntity):
    _attr_icon = "mdi:school"

    def __init__(self, coordinator, kind, name, child_id=None):
        super().__init__(coordinator, f"{kind}:{child_id or 'all'}", name)
        self.kind = kind
        self.child_id = child_id
        if kind == "status":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if kind in ("messages", "unread"):
            self._attr_icon = "mdi:email-outline"

    @property
    def available(self):
        if not super().available:
            return False
        if self.kind == "status":
            return True
        data = self.coordinator.data
        if data["status"].get(self.kind) != "ok":
            return False
        # If relation mapping cannot be proven, never claim a child has zero.
        if self.child_id and data["unmapped"].get(self.kind, 0):
            return False
        if self.kind == "homework" and self.child_id:
            return data["status"].get("child_calendar") == "ok"
        return True

    def _items(self):
        if self.kind in ("homework", "tasks"):
            return self.coordinator.future_items(self.kind, self.child_id)
        return self.coordinator.items(self.kind, self.child_id)

    @property
    def native_value(self):
        if self.kind == "status":
            return "ok" if all(s == "ok" for s in self.coordinator.data["status"].values()) else "delvis"
        if self.kind == "unread":
            return self.coordinator.data.get("unread_count")
        return len(self._items())

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        attrs = {"senest_opdateret": data["updated"]}
        if self.child_id:
            child = self.coordinator.children.get(self.child_id, {})
            attrs.update({"barn_id": self.child_id, "barn_navn": child.get("name", ""),
                          "klasse": child.get("class", "")})
        if self.kind == "status":
            attrs.update({"datakilder": data["status"], "uden_barnetilknytning": data["unmapped"],
                          "periode_fra": data["range_start"], "periode_til": data["range_end"]})
        elif self.kind != "unread":
            source = self._items()
            attrs["items"] = [{**row, "text": row["text"][:4000]} for row in source[:50]]
            attrs["vist_antal"] = min(50, len(source))
            attrs["afkortet"] = len(source) > 50
            attrs["datakilde"] = self.kind
        return attrs
