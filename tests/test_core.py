"""Synthetic contract tests; no real school data or credentials."""
import asyncio
import base64
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from uuid import UUID
from zoneinfo import ZoneInfo

# Import pure modules without invoking Home Assistant setup.
package = types.ModuleType("zenbi")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/zenbi")]
sys.modules["zenbi"] = package
models = importlib.import_module("zenbi.models")
api = importlib.import_module("zenbi.api")
const = importlib.import_module("zenbi.const")

CHILD = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
GROUP = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
OTHER = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def token(exp=None, marker="old"):
    value = {"exp": exp or datetime.now(timezone.utc).timestamp() + 7200, "usr": CHILD, "org": GROUP, "marker": marker}
    encoded = base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
    return "header." + encoded + ".signature"


class Response:
    def __init__(self, status, data):
        self.status = status
        self.data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def json(self):
        return self.data


class Session:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return Response(*self.replies.pop(0))


class ModelsTest(unittest.TestCase):
    def setUp(self):
        self.tz = ZoneInfo("Europe/Copenhagen")
        self.start = datetime(2026, 10, 19, tzinfo=self.tz)
        self.end = self.start + timedelta(days=14)

    def test_delta_html_and_embeds(self):
        self.assertEqual(models.text('{"ops":[{"insert":"Læs side 3"},{"insert":{"image":"ignored"}}]}'), "Læs side 3")
        self.assertEqual(models.text("<p>Læs &amp; lær</p>"), "Læs & lær")

    def test_packed_guids(self):
        alphabet = "!" + "".join(chr(i) for i in range(35, 127) if chr(i) != "\\")
        number = UUID(CHILD).int
        packed = ""
        while number:
            number, digit = divmod(number, len(alphabet))
            packed = alphabet[digit] + packed
        self.assertEqual(models.guid(packed), CHILD)
        self.assertEqual(models.guid_list(f"{CHILD},{GROUP}"), [CHILD, GROUP])

    def test_relation_mapping_does_not_leak_other_children(self):
        children = {CHILD: {}, OTHER: {}}
        groups = {CHILD: {GROUP}, OTHER: set()}
        self.assertEqual(models.children_for({"participantModels": [{"participantId": GROUP}]}, children, groups), [CHILD])
        self.assertEqual(models.children_for({"participantIds": []}, children, groups), [])

    def test_private_calendar_matches_frontend_masking(self):
        private = {"id": "event", "private": True, "title": "Private title", "description": "Private text",
                   "participantModels": [{"participantId": GROUP}]}
        hidden = models.visible_calendar([private], OTHER, {})
        self.assertEqual(hidden[0]["title"], "Privat begivenhed")
        self.assertEqual(hidden[0]["description"], "")
        visible = models.visible_calendar([private], CHILD, {CHILD: {GROUP}})
        self.assertEqual(visible[0]["title"], "Private title")

    def test_profile_filters_sensitive_metadata(self):
        data = {"groupModelTimeFrames": [{"users": [{"groupId": GROUP, "userIds": [CHILD]}]}],
                "userModelTimeFrames": [{"userModels": [{"userMetadata": [
                    {"userId": CHILD, "personFieldId": const.NAME_FIELDS["full"], "value": "Test Elev"},
                    {"userId": CHILD, "personFieldId": "private-field", "value": "sensitive"}]}]}]}
        children, groups = models.profile(data, {"rel": f"{GROUP},{CHILD}"})
        self.assertEqual(children[CHILD]["name"], "Test Elev")
        self.assertNotIn("sensitive", str(children))
        self.assertEqual(groups[CHILD], {GROUP})

    def test_school_class_reference_uses_group_name(self):
        data = {"groupModelTimeFrames": [{"users": [], "groupModels": [{"id": GROUP, "name": "1. klasse"}]}],
                "userModelTimeFrames": [{"userModels": [{"userMetadata": [
                    {"userId": CHILD, "personFieldId": const.NAME_FIELDS["full"], "value": "Test Elev"},
                    {"userId": CHILD, "personFieldId": const.NAME_FIELDS["class"], "value": GROUP}]}]}]}
        children, _ = models.profile(data, {"rel": f"{OTHER},{CHILD}"})
        self.assertEqual(children[CHILD]["class"], "1. klasse")
        data["groupModelTimeFrames"][0]["groupModels"] = []
        children, _ = models.profile(data, {"rel": f"{OTHER},{CHILD}"})
        self.assertEqual(children[CHILD]["class"], "")

    def event(self, rule):
        return {"id": "event", "title": "Dansk", "repetition": rule, "participantModels": []}

    def test_weekly_repeats_across_dst(self):
        rule = {"startDate": "2026-10-19T08:00:00+02:00", "frequency": 2, "step": 1,
                "dayFlags": 1, "minuteLength": 45, "repeatTimes": 0}
        result = models.expand_calendar([self.event(rule)], self.start, self.end, "Europe/Copenhagen")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["start"], "2026-10-19T08:00:00+02:00")
        self.assertEqual(result[1]["start"], "2026-10-26T08:00:00+01:00")

    def test_repeat_limit_and_step(self):
        rule = {"startDate": "2026-10-19T08:00:00", "frequency": 1, "step": 2,
                "minuteLength": 30, "repeatTimes": 3}
        result = models.expand_calendar([self.event(rule)], self.start, self.end, "Europe/Copenhagen")
        self.assertEqual([r["start"][:10] for r in result], ["2026-10-19", "2026-10-21", "2026-10-23"])

    def test_removed_and_moved_events(self):
        rule = {"startDate": "2026-10-19T08:00:00", "frequency": 2, "step": 1,
                "dayFlags": 1, "minuteLength": 45, "deviationDates": [
                    {"date": "2026-10-19", "type": 0},
                    {"date": "2026-10-26", "type": 1, "start": "2026-10-27T10:00:00", "end": "2026-10-27T11:00:00"}]}
        result = models.expand_calendar([self.event(rule)], self.start, self.end, "Europe/Copenhagen")
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["start"].startswith("2026-10-27T10:"))

    def test_all_day_exclusive_end(self):
        event = {"id": "all-day", "start": "2026-10-20", "end": "2026-10-21", "onlyDate": True}
        result = models.expand_calendar([event], self.start, self.end, "Europe/Copenhagen")
        self.assertEqual(result[0]["end"], "2026-10-21")

    def test_unknown_schema_and_rules_fail_closed(self):
        with self.assertRaises(models.SchemaError):
            models.rows({}, "homeworkTasks")
        with self.assertRaises(models.SchemaError):
            models.expand_calendar([self.event({"frequency": 99})], self.start, self.end, "Europe/Copenhagen")


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_once_for_concurrent_requests(self):
        refreshed = token(marker="new")
        session = Session([(200, {"token": refreshed, "refreshToken": "rotated"})])
        saved = []
        client = api.ZenbiClient(session, tokens={"token": token(exp=1), "refreshToken": "old"}, on_tokens=saved.append)
        await asyncio.gather(*(client.ensure_token() for _ in range(5)))
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(saved[0]["refreshToken"], "rotated")

    async def test_401_refresh_and_retry(self):
        session = Session([(401, {}), (200, {"token": token(marker="new"), "refreshToken": "rotated"}), (200, [])])
        client = api.ZenbiClient(session, tokens={"token": token(), "refreshToken": "old"})
        self.assertEqual(await client.get("/api/test"), [])
        self.assertEqual(len(session.calls), 3)

    async def test_http_errors_are_sanitized(self):
        for status, expected in [(403, api.PermissionError), (429, api.RateLimitError), (500, api.ZenbiError)]:
            client = api.ZenbiClient(Session([(status, {"private": "secret"})]))
            with self.assertRaises(expected) as cm:
                await client._request("/api/test")
            self.assertNotIn("secret", str(cm.exception))

    async def test_org_challenge_and_tokens(self):
        session = Session([(200, {"organizations": [{"tempToken": "temporary"}]}),
                           (200, {"token": token(), "refreshToken": "refresh"})])
        client = api.ZenbiClient(session)
        with self.assertRaises(api.LoginChallenge):
            await client.login("test", "dummy")
        await client.select_organization("temporary")
        self.assertIn("token", client.tokens)

    async def test_posts_query_names_and_read_only_calls(self):
        session = Session([(200, {"diaries": []})])
        client = api.ZenbiClient(session, tokens={"token": token(), "refreshToken": "old"})
        now = datetime.now(timezone.utc)
        await client.source("posts", now, now + timedelta(days=1))
        method, url, kwargs = session.calls[0]
        self.assertTrue(url.endswith("/api/diary/api/v1/diary/relations"))
        self.assertEqual(method, "GET")
        self.assertEqual({k for k, v in kwargs["params"]}, {"starttime", "endtime"})


if __name__ == "__main__":
    unittest.main()
