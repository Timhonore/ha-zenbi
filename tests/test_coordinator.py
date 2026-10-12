"""Exercise coordinator/entity behavior with lightweight HA interface doubles.

These are not full Home Assistant runtime tests.
"""
import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
import importlib
import sys
import types
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from test_core import api, CHILD, GROUP, OTHER


def module(name, **attrs):
    value = types.ModuleType(name)
    value.__dict__.update(attrs)
    sys.modules[name] = value
    return value


class UpdateFailed(Exception):
    pass


class AuthFailed(Exception):
    pass


class Coordinator:
    def __init__(self, hass, logger, **kwargs):
        self.hass = hass
        self.last_update_success = True
        self.update_interval = kwargs.get("update_interval")
        self.data = None


class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.hass = coordinator.hass

    @property
    def available(self):
        return self.coordinator.last_update_success


@dataclass
class CalendarEvent:
    start: object
    end: object
    summary: str
    description: str = ""
    uid: str = ""


module("homeassistant")
module("homeassistant.helpers")
module("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=Coordinator,
       UpdateFailed=UpdateFailed, CoordinatorEntity=CoordinatorEntity)
module("homeassistant.helpers.entity", DeviceInfo=lambda **kwargs: kwargs,
       EntityCategory=types.SimpleNamespace(DIAGNOSTIC="diagnostic"))
module("homeassistant.exceptions", ConfigEntryAuthFailed=AuthFailed, HomeAssistantError=UpdateFailed)
module("homeassistant.util")
dt = module("homeassistant.util.dt", now=lambda: datetime(2026, 10, 11, 19, tzinfo=ZoneInfo("Europe/Copenhagen")),
            DEFAULT_TIME_ZONE=ZoneInfo("Europe/Copenhagen"))
module("homeassistant.components")
module("homeassistant.components.calendar", CalendarEntity=type("CalendarEntity", (), {}), CalendarEvent=CalendarEvent)
module("homeassistant.components.sensor", SensorEntity=type("SensorEntity", (), {}))

coordinator_mod = importlib.import_module("zenbi.coordinator")
sensor_mod = importlib.import_module("zenbi.sensor")
calendar_mod = importlib.import_module("zenbi.calendar")


class Client:
    def __init__(self):
        self.token_claims = {"usr": OTHER}
        self.failures = {}
        self.sources = {k: [] for k in coordinator_mod.ENDPOINTS}
        self.sources["tasks"] = {"homeworkTasks": [], "recipients": []}

    async def ensure_token(self):
        pass

    async def discover(self):
        return {CHILD: {"name": "Test Elev", "class": "2A"}}, {CHILD: {GROUP}}, "Testskole"

    async def source(self, name, start, end):
        if name in self.failures:
            raise self.failures[name]
        return self.sources[name]


class CoordinatorTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = types.SimpleNamespace(config=types.SimpleNamespace(time_zone="Europe/Copenhagen"))
        self.entry = types.SimpleNamespace(data={"children": [CHILD]}, options={}, unique_id="test")
        self.client = Client()
        self.coordinator = coordinator_mod.ZenbiCoordinator(self.hass, self.entry, self.client)
        await self.coordinator._async_setup()

    async def update(self):
        self.coordinator.data = await self.coordinator._async_update_data()

    async def test_board_posts_show_only_active_not_expired_or_future(self):
        self.client.sources["posts"] = [
            {"id": "active", "title": "Kor", "description": "Tilmelding",
             "start": "2026-10-10T10:32:00+02:00", "end": "2026-11-01T00:00:00+01:00"},
            {"id": "expired", "start": "2026-09-01", "end": "2026-10-10"},
            {"id": "future", "start": "2026-10-12", "end": "2026-11-01"}]
        calls = []
        original = self.client.source
        async def source(kind, start, end):
            if kind == "posts":
                calls.append((start, end))
            return await original(kind, start, end)
        self.client.source = source
        await self.update()
        self.assertEqual(self.coordinator.data["status"]["posts"], "ok")
        self.assertEqual([row["id"] for row in self.coordinator.data["items"]["posts"]], ["active"])
        self.assertEqual(calls[0][1], dt.now())
        self.assertEqual((calls[0][1] - calls[0][0]).days, 1)
        self.client.sources["posts"] = [{"id": "invalid", "start": "bad", "end": "bad"}]
        await self.update()
        self.assertEqual(self.coordinator.data["status"]["posts"], "SchemaError")

    async def test_on_demand_week_range_cache_and_sensor_isolation(self):
        await self.update()
        previous = self.coordinator.data
        self.client.sources["weekly_plans"] = [
            {"id":"selected","title":"Nytår", "start":"2026-12-28", "end":"2027-01-04", "participantIds":[GROUP]},
            {"id":"previous","start":"2026-12-21", "end":"2026-12-28", "participantIds":[GROUP]},
            {"id":"other","start":"2026-12-28", "participantIds":[OTHER]}]
        calls = []
        original = self.client.source
        async def source(kind, start, end):
            calls.append((kind,start,end))
            return await original(kind,start,end)
        self.client.source = source
        result = await self.coordinator.async_weekly_plans(date(2026,12,28))
        self.assertEqual([row["id"] for row in result["items"]], ["selected"])
        self.assertEqual(result["unmapped"], 1)
        self.assertIs(previous, self.coordinator.data)
        self.assertEqual(calls[0][1].isoformat(), "2026-12-28T00:00:00+01:00")
        self.assertEqual(calls[0][2].isoformat(), "2027-01-04T00:00:00+01:00")
        await self.coordinator.async_weekly_plans(date(2026,12,28))
        self.assertEqual(len(calls), 1)
        with self.assertRaises(ValueError):
            await self.coordinator.async_weekly_plans(date(2026,12,29))

    async def test_on_demand_week_failure_is_not_an_empty_plan(self):
        self.client.failures["weekly_plans"] = api.PermissionError("denied")
        with self.assertRaises(api.PermissionError):
            await self.coordinator.async_weekly_plans(date(2026,12,28))
        self.assertFalse(self.coordinator._weekly_cache)

    async def test_timetable_recurrence_privacy_and_child_mapping(self):
        self.client.sources["child_calendar"] = [
            {"id":"lesson","title":"Dansk", "description":"Læs sammen", "participantModels":[{"participantId":GROUP}],
             "repetition":{"frequency":2,"dayFlags":5,"startDate":"2026-10-12T08:00:00+02:00", "minuteLength":45}},
            {"id":"private","title":"Private title","description":"Secret", "private":True,
             "start":"2026-10-13T09:00:00+02:00","end":"2026-10-13T10:00:00+02:00", "participantModels":[{"participantId":CHILD}]},
            {"id":"other","title":"Other child","start":"2026-10-12T09:00:00+02:00","end":"2026-10-12T10:00:00+02:00", "participantModels":[{"participantId":OTHER}]}]
        result = await self.coordinator.async_timetable(date(2026,10,12))
        self.assertEqual(len(result["items"]),3)
        self.assertEqual([row["date"][:10] for row in result["items"] if row["title"]=="Dansk"],["2026-10-12","2026-10-14"])
        self.assertTrue(all(row["children"]==[CHILD] for row in result["items"]))
        private = next(row for row in result["items"] if row["title"]=="Privat begivenhed")
        self.assertEqual(private["text"], "")
        self.assertNotIn("Secret",str(result))
        self.assertEqual(result["unmapped"],1)

    async def test_timetable_errors_are_not_empty_weeks(self):
        self.client.failures["child_calendar"] = api.PermissionError("denied")
        with self.assertRaises(api.PermissionError):
            await self.coordinator.async_timetable(date(2026,10,12))
        self.assertFalse(self.coordinator._timetable_cache)

    async def test_permission_failure_does_not_become_zero(self):
        self.client.failures["homework"] = api.PermissionError("denied")
        await self.update()
        failed = sensor_mod.ZenbiSensor(self.coordinator, "homework", "Lektier", CHILD)
        unaffected = sensor_mod.ZenbiSensor(self.coordinator, "unread", "Beskeder")
        self.assertFalse(failed.available)
        self.assertTrue(unaffected.available)
        self.assertEqual(unaffected.native_value, 0)

    async def test_mapping_calendar_homework_and_task_group(self):
        self.client.sources["child_calendar"] = [{"id": "calendar", "title": "Dansk", "start": "2026-10-12T08:00:00",
                                                  "end": "2026-10-12T09:00:00", "participantModels": [{"participantId": GROUP}]}]
        self.client.sources["homework"] = [{"id": "homework", "calendarItemId": "calendar", "date": "2026-10-12", "description": "Læs side 3"}]
        self.client.sources["tasks"] = {"homeworkTasks": [{"id": "task", "closes": "2026-10-13T12:00:00", "title": "Aflevering"}],
                                        "recipients": [{"homeworkTaskId": "task", "recipientIds": [GROUP]}]}
        await self.update()
        self.assertEqual(self.coordinator.data["items"]["homework"][0]["children"], [CHILD])
        self.assertEqual(self.coordinator.data["items"]["tasks"][0]["children"], [CHILD])
        entity = calendar_mod.ZenbiCalendar(self.coordinator, "homework", "Frister", CHILD)
        self.assertTrue(entity.available)
        self.assertEqual(len(entity._events()), 2)
        self.assertEqual(entity._events()[0].summary, "Dansk")

    async def test_unmapped_data_is_visible_and_child_sensor_unavailable(self):
        self.client.sources["homework"] = [{"id": "h", "calendarItemId": "unknown", "date": "2026-10-12"}]
        await self.update()
        self.assertEqual(self.coordinator.data["unmapped"]["homework"], 1)
        self.assertFalse(sensor_mod.ZenbiSensor(self.coordinator, "homework", "Lektier", CHILD).available)
        self.assertTrue(sensor_mod.ZenbiSensor(self.coordinator, "homework", "Alle lektier").available)

    async def test_unknown_date_schema_is_not_empty_success(self):
        self.client.sources["homework"] = [{"id": "h", "calendarItemId": "unknown"}]
        await self.update()
        self.assertEqual(self.coordinator.data["status"]["homework"], "SchemaError")

    async def test_unauthorized_triggers_reauth(self):
        self.client.failures["unread"] = api.AuthenticationError("expired")
        with self.assertRaises(AuthFailed):
            await self.update()

    async def test_calendar_outside_cache_has_explicit_error(self):
        await self.update()
        entity = calendar_mod.ZenbiCalendar(self.coordinator, "homework", "Frister", CHILD)
        with self.assertRaises(UpdateFailed):
            await entity.async_get_events(self.hass, datetime(2026, 1, 1, tzinfo=timezone.utc),
                                          datetime(2026, 2, 1, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
