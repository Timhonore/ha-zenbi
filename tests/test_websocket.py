"""Exercise weekly-plan access checks with small HA interface doubles."""
import importlib
import types
import unittest
from unittest.mock import AsyncMock

from test_coordinator import module, CHILD, OTHER

module("probatio", Required=lambda key: key)
module("homeassistant.auth")
module("homeassistant.auth.permissions")
module("homeassistant.auth.permissions.const", POLICY_READ="read")
module("homeassistant.config_entries", ConfigEntryState=types.SimpleNamespace(LOADED="loaded"))
module("homeassistant.components.websocket_api", websocket_command=lambda schema: lambda fn: fn,
       async_response=lambda fn: fn)
module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry,
       async_entries_for_config_entry=lambda registry, entry_id: registry)
ws = importlib.import_module("zenbi.websocket")


class WebSocketTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.result = {"week":"2026-12-28", "items":[
            {"id":"shared", "children":[CHILD,OTHER], "title":"Fælles plan"},
            {"id":"private", "children":[OTHER], "title":"Andet barn"}], "unmapped":0, "clipped":False}
        self.coordinator = types.SimpleNamespace(children={CHILD:{},OTHER:{}},
            async_weekly_plans=AsyncMock(return_value=self.result))
        self.entry = types.SimpleNamespace(entry_id="entry",domain="zenbi",state="loaded",runtime_data=self.coordinator)
        self.hass = types.SimpleNamespace(config_entries=types.SimpleNamespace(async_get_entry=lambda key:self.entry if key=="entry" else None),
            registry=[types.SimpleNamespace(platform="zenbi",unique_id=f"account:weekly_plans:{uid}",entity_id=f"sensor.{uid}") for uid in (CHILD,OTHER)])
        self.sent = []
        self.errors = []
        self.connection = types.SimpleNamespace(user=types.SimpleNamespace(permissions=types.SimpleNamespace(
            check_entity=lambda entity_id, policy:entity_id==f"sensor.{CHILD}")),
            send_result=lambda key,value:self.sent.append(value),
            send_error=lambda key,code,message:self.errors.append(code))
        self.message = {"id":1,"type":"zenbi/weekly_plans","config_entry_id":"entry","week":"2026-12-28"}

    async def test_filters_unreadable_children_and_preserves_shared_cache(self):
        await ws.ws_weekly_plans(self.hass,self.connection,self.message)
        self.assertFalse(self.errors)
        self.assertEqual([row["id"] for row in self.sent[0]["items"]],["shared"])
        self.assertEqual(self.sent[0]["items"][0]["children"],[CHILD])
        self.assertEqual(self.result["items"][0]["children"],[CHILD,OTHER])

    async def test_denied_access_never_fetches_school_data(self):
        self.connection.user.permissions.check_entity = lambda entity,policy:False
        await ws.ws_weekly_plans(self.hass,self.connection,self.message)
        self.assertEqual(self.errors,["unauthorized"])
        self.coordinator.async_weekly_plans.assert_not_awaited()

    async def test_timetable_uses_calendar_read_permissions(self):
        self.coordinator.async_timetable = AsyncMock(return_value=self.result)
        for entity in self.hass.registry:
            entity.unique_id = entity.unique_id.replace(":weekly_plans:",":calendar:child_calendar:")
        await ws.ws_timetable(self.hass,self.connection,{**self.message,"type":"zenbi/timetable"})
        self.assertFalse(self.errors)
        self.assertEqual([row["id"] for row in self.sent[0]["items"]],["shared"])
        self.coordinator.async_timetable.assert_awaited_once()
        self.coordinator.async_weekly_plans.assert_not_awaited()

    async def test_weekly_sensor_permission_cannot_unlock_timetable(self):
        self.coordinator.async_timetable = AsyncMock(return_value=self.result)
        await ws.ws_timetable(self.hass,self.connection,{**self.message,"type":"zenbi/timetable"})
        self.assertEqual(self.errors,["unauthorized"])
        self.coordinator.async_timetable.assert_not_awaited()

    async def test_rejects_invalid_week(self):
        await ws.ws_weekly_plans(self.hass,self.connection,{**self.message,"week":"2026-12-29"})
        self.assertEqual(self.errors,["invalid_week"])
        self.coordinator.async_weekly_plans.assert_not_awaited()

    async def test_unloaded_entry_cannot_query(self):
        self.entry.state = "not_loaded"
        await ws.ws_weekly_plans(self.hass,self.connection,self.message)
        self.assertEqual(self.errors,["not_found"])
        self.coordinator.async_weekly_plans.assert_not_awaited()
