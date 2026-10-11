"""Read-only HA calendars with expanded recurring events."""
from datetime import date, datetime, time, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.util import dt as dt_util

from .entity import ZenbiEntity
from .models import parse_dt


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    entities = [ZenbiCalendar(coordinator, "calendar", "Kalender")]
    for uid, child in coordinator.children.items():
        entities.append(ZenbiCalendar(coordinator, "child_calendar", f"{child['name']} Kalender", uid))
        entities.append(ZenbiCalendar(coordinator, "homework", f"{child['name']} Lektiefrister", uid))
    async_add_entities(entities)


class ZenbiCalendar(ZenbiEntity, CalendarEntity):
    def __init__(self, coordinator, kind, name, child_id=None):
        super().__init__(coordinator, f"calendar:{kind}:{child_id or 'all'}", name)
        self.kind = kind
        self.child_id = child_id

    @property
    def available(self):
        data = self.coordinator.data
        if not super().available or data["status"].get(self.kind) != "ok":
            return False
        if self.kind == "homework":
            return (data["status"].get("child_calendar") == "ok" and data["status"].get("tasks") == "ok"
                    and not data["unmapped"].get("homework") and not data["unmapped"].get("tasks"))
        if self.child_id and data["unmapped"].get("child_calendar"):
            return False
        return True

    def _events(self):
        data = self.coordinator.data
        zone = self.hass.config.time_zone
        if self.kind == "homework":
            result = []
            for kind in ("homework", "tasks"):
                for row in self.coordinator.items(kind, self.child_id):
                    if not row.get("date"):
                        continue
                    start = parse_dt(row["date"], zone)
                    if kind == "homework":
                        start = start.date()
                        end = start + timedelta(days=1)
                    else:
                        end = start + timedelta(minutes=1)
                    result.append(CalendarEvent(start=start, end=end, summary=row["title"],
                                                description=row["text"], uid=f"{kind}:{row['id']}"))
            return sorted(result, key=lambda event: self._as_dt(event.start))
        raw = data["child_events"].get(self.child_id, []) if self.child_id else data["events"].get(self.kind, [])
        return [CalendarEvent(start=date.fromisoformat(row["start"]) if row["all_day"] else parse_dt(row["start"], zone),
                              end=date.fromisoformat(row["end"]) if row["all_day"] else parse_dt(row["end"], zone),
                              summary=row["title"], description=row["text"], uid=row["id"]) for row in raw]

    def _as_dt(self, value):
        return value if isinstance(value, datetime) else datetime.combine(value, time.min, tzinfo=dt_util.DEFAULT_TIME_ZONE)

    @property
    def event(self):
        now = dt_util.now()
        return next((event for event in self._events() if self._as_dt(event.end) > now), None)

    async def async_get_events(self, hass, start_date, end_date):
        # HA can browse dates outside the coordinator's rolling cache.
        zone = hass.config.time_zone
        if self.kind != "homework":
            from .models import children_for, expand_calendar, guid, visible_calendar
            source = await self.coordinator.client.source(self.kind, start_date, end_date)
            source = visible_calendar(source, guid(self.coordinator.client.token_claims["usr"]), self.coordinator.groups)
            if self.child_id:
                source = [row for row in source if self.child_id in children_for(row, self.coordinator.children, self.coordinator.groups)]
            rows = expand_calendar(source, start_date, end_date, zone)
            return [CalendarEvent(start=date.fromisoformat(row["start"]) if row["all_day"] else parse_dt(row["start"], zone),
                                  end=date.fromisoformat(row["end"]) if row["all_day"] else parse_dt(row["end"], zone),
                                  summary=row["title"], description=row["text"], uid=row["id"]) for row in rows]
        cache_start = parse_dt(self.coordinator.data["range_start"], zone)
        cache_end = parse_dt(self.coordinator.data["range_end"], zone)
        if start_date < cache_start or end_date > cache_end:
            # Explicit error avoids falsely showing empty months outside the cache.
            from homeassistant.exceptions import HomeAssistantError
            raise HomeAssistantError("Lektiefrister er kun hentet i den valgte periode. Udvid 'Dage frem' i integrationens indstillinger.")
        return [event for event in self._events() if self._as_dt(event.start) < end_date and self._as_dt(event.end) > start_date]
