"""Synthetic contract tests; no real school data or credentials."""
import asyncio
import base64
from datetime import datetime, timedelta, timezone
import importlib
import json
from http.cookies import SimpleCookie
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
    def __init__(self, status, data, cookie_header=""):
        self.status = status
        self.data = data
        self.cookies = SimpleCookie()
        for header in cookie_header if isinstance(cookie_header, list) else [cookie_header]:
            for name, morsel in SimpleCookie(header).items():
                self.cookies[name] = morsel

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
    def test_localized_missing_item_title(self):
        for kind, label in [("homework", "Lektie"), ("tasks", "Opgave"),
                            ("weekly_plans", "Ugeplan"), ("messages", "Besked"), ("posts", "Opslag")]:
            self.assertEqual(models.item({"id": "demo"}, kind, [])["title"], label)
        self.assertEqual(models.item({"id": "demo", "title": "Ugens emne"}, "weekly_plans", [])["title"], "Ugens emne")

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

    def test_profile_picture_metadata(self):
        data = {"groupModelTimeFrames": [], "userModelTimeFrames": [{"userModels": [{"userMetadata": [
            {"userId": CHILD, "personFieldId": const.NAME_FIELDS["picture"], "value": "child photo.png"},
            {"userId": OTHER, "personFieldId": const.NAME_FIELDS["picture"], "value": "other.png"}]}]}]}
        children, _ = models.profile(data, {"rel": f"{GROUP},{CHILD}", "org": GROUP})
        self.assertEqual(children[CHILD]["picture"], f"https://zenbistore.blob.core.windows.net/profile-photos/{GROUP}/child%20photo.png/small")
        self.assertNotIn(OTHER, children)
        field = data["userModelTimeFrames"][0]["userModels"][0]["userMetadata"][0]
        field["value"] = "https://example.test/other.png"
        children, _ = models.profile(data, {"rel": f"{GROUP},{CHILD}", "org": GROUP})
        self.assertNotIn("picture", children[CHILD])
        field.update(value="child.png", couplingId=OTHER)
        children, _ = models.profile(data, {"rel": f"{GROUP},{CHILD}", "org": GROUP})
        self.assertNotIn("picture", children[CHILD])

    def test_school_class_reference_uses_select_option_name(self):
        data = {"groupModelTimeFrames": [], "userModelTimeFrames": [{"userModels": [{"userMetadata": [
            {"userId": CHILD, "personFieldId": const.NAME_FIELDS["class"], "value": OTHER}]}]}]}
        fields = {"userDefinedPersonFields": [{"id": const.NAME_FIELDS["class"],
                  "personFieldModelItems": [{"id": OTHER, "name": "2. klasse"}]}]}
        children, _ = models.profile(data, {"rel": f"{GROUP},{CHILD}"}, fields)
        self.assertEqual(children[CHILD]["class"], "2. klasse")

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


def session_cookies(value):
    return {api.SESSION_COOKIE: "1", "token": value + "-access", "refreshToken": value + "-refresh"}


def cookie_headers(value):
    return ["__Host-zenbi-session=1; Path=/; Secure; SameSite=Strict",
            f"token={value}-access; Domain=app.zenbi.dk; Path=/api/; Secure; HttpOnly; SameSite=Strict",
            f"refreshToken={value}-refresh; Domain=app.zenbi.dk; Path=/api/; Secure; HttpOnly; SameSite=Strict"]


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_current_cookie_login_without_refresh_token(self):
        session = Session([(200, {"token": token(), "maxAge": 86400000}, cookie_headers("synthetic")), (200, [])])
        client = api.ZenbiClient(session)
        await client.login("synthetic@example.invalid", "dummy")
        self.assertIsNone(client.tokens["refreshToken"])
        self.assertEqual(client.tokens["cookies"], session_cookies("synthetic"))
        await client.get("/api/test")
        self.assertNotIn("Authorization", session.calls[-1][2]["headers"])
        self.assertEqual(session.calls[-1][2]["cookies"], session_cookies("synthetic"))

    async def test_current_cookie_refresh_restart_and_account_isolation(self):
        initial = {"token": token(exp=1), "refreshToken": None, "maxAge": 86400000,
                   "expires_at": 1, "cookies": session_cookies("old")}
        saved = []
        session = Session([(200, {"token": token(marker="current"), "maxAge": 86400000}, cookie_headers("new"))])
        client = api.ZenbiClient(session, tokens=initial, on_tokens=saved.append)
        await asyncio.gather(*(client.ensure_token() for _ in range(5)))
        self.assertEqual(len(session.calls), 1)
        self.assertIsNone(session.calls[0][2]["json"])
        self.assertNotIn("Authorization", session.calls[0][2]["headers"])
        self.assertEqual(session.calls[0][2]["headers"]["Origin"], const.BASE_URL)
        restarted = api.ZenbiClient(Session([(200, [])]), tokens=api.stored_auth(saved[-1]))
        await restarted.get("/api/test")
        self.assertEqual(restarted.session.calls[0][2]["cookies"], session_cookies("new"))
        other = api.ZenbiClient(session, tokens={**initial, "cookies": session_cookies("other")})
        self.assertEqual(other.cookies, session_cookies("other"))
        self.assertEqual(client.cookies, session_cookies("new"))
        self.assertEqual(initial["cookies"], session_cookies("old"))

    async def test_current_cookie_short_maxage_not_jwt_expiry(self):
        session = Session([(200, {"token": token(exp=1), "maxAge": 60000}, cookie_headers("synthetic")), (200, [])])
        client = api.ZenbiClient(session)
        await client.login("synthetic@example.invalid", "dummy")
        await client.get("/api/test")
        self.assertEqual(len(session.calls), 2)

    async def test_cookie_rejected_session_is_not_retried_or_logged(self):
        stored = {"token": token(), "maxAge": 86400000, "expires_at": 1, "cookies": session_cookies("private")}
        deleted = [h.split('=', 1)[0] + '=; Max-Age=0; ' + h.split('; ', 1)[1] for h in cookie_headers("private")]
        session = Session([(401, {}, deleted)])
        saved = []
        client = api.ZenbiClient(session, tokens=stored, on_tokens=saved.append)
        with self.assertRaises(api.AuthenticationError) as cm:
            await client.ensure_token()
        self.assertNotIn("private", str(cm.exception))
        self.assertEqual(cm.exception.reason, "session_rejected")
        self.assertEqual(saved[-1]["cookies"], {})
        with self.assertRaises(api.AuthenticationError):
            await client.ensure_token()
        self.assertEqual(len(session.calls), 1)

    async def test_cookie_401_refresh_and_retry(self):
        stored = {"token": token(), "maxAge": 86400000,
                  "expires_at": datetime.now(timezone.utc).timestamp() + 86400, "cookies": session_cookies("old")}
        session = Session([(401, {}), (200, {"token": token(marker="new"), "maxAge": 86400000},
                           cookie_headers("rotated")), (200, [])])
        client = api.ZenbiClient(session, tokens=stored)
        self.assertEqual(await client.get("/api/test"), [])
        self.assertEqual(len(session.calls), 3)
        self.assertIsNone(session.calls[1][2]["json"])
        self.assertEqual(session.calls[2][2]["cookies"], session_cookies("rotated"))
        self.assertTrue(all("Authorization" not in call[2]["headers"] for call in session.calls))

    async def test_stale_response_cannot_clear_a_new_cookie(self):
        session = Session([])
        client = api.ZenbiClient(session, tokens={"token": token(), "cookies": session_cookies("old")})
        class StaleResponse(Response):
            async def __aenter__(self):
                client.cookies = session_cookies("new")
                return self
        session.request = lambda *args, **kwargs: StaleResponse(
            401, {}, "token=; Domain=app.zenbi.dk; Max-Age=0; Path=/api/; Secure; HttpOnly")
        with self.assertRaises(api.AuthenticationError):
            await client._request("/api/test")
        self.assertEqual(client.cookies, session_cookies("new"))

    async def test_marker_alone_cannot_authenticate(self):
        client = api.ZenbiClient(Session([(200, {"token": token(), "maxAge": 86400000},
                                         "__Host-zenbi-session=1; Path=/; Secure")]))
        with self.assertRaises(models.SchemaError):
            await client.login("synthetic@example.invalid", "dummy")
        restored = api.ZenbiClient(Session([]), tokens={"token": token(), "maxAge": 86400000,
                                    "cookies": {api.SESSION_COOKIE: "1"}})
        with self.assertRaises(api.AuthenticationError):
            await restored.ensure_token()

    async def test_auth_cookie_scope_is_restricted(self):
        headers = cookie_headers("real") + [
            "tracking=private; Domain=app.zenbi.dk; Path=/api/; Secure",
            "token=other; Domain=other.invalid; Path=/api/; Secure; HttpOnly",
            "refreshToken=insecure; Domain=app.zenbi.dk; Path=/api/; HttpOnly"]
        client = api.ZenbiClient(Session([(200, {}, headers)]))
        await client._request("/api/test")
        self.assertEqual(client.cookies, {api.SESSION_COOKIE: "1"})

    async def test_cookie_login_requires_cookie_and_routing(self):
        for response in ({"token": token(), "maxAge": 86400000},
                         {"token": token(), "maxAge": True}):
            client = api.ZenbiClient(Session([(200, response)]))
            with self.assertRaises(models.SchemaError):
                await client.login("synthetic@example.invalid", "dummy")

    async def test_refresh_once_for_concurrent_requests(self):
        refreshed = token(marker="new")
        session = Session([(200, {"token": refreshed, "refreshToken": "rotated"})])
        saved = []
        client = api.ZenbiClient(session, tokens={"token": token(exp=1), "refreshToken": "old"}, on_tokens=saved.append)
        await asyncio.gather(*(client.ensure_token() for _ in range(5)))
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(saved[0]["refreshToken"], "rotated")

    async def test_refresh_before_expiry_with_authenticated_request(self):
        old = token(exp=datetime.now(timezone.utc).timestamp() + 1800)
        session = Session([(200, {"token": token(marker="new"), "refreshToken": "rotated"}), (200, [])])
        saved = []
        client = api.ZenbiClient(session, tokens={"token": old, "refreshToken": "old-refresh"}, on_tokens=saved.append)
        self.assertEqual(await client.get("/api/test"), [])
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/account/refresh-token"))
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {old}")
        self.assertEqual(kwargs["json"], {"token": old, "refreshToken": "old-refresh"})
        restarted = api.ZenbiClient(Session([(200, [])]), tokens=saved[0])
        await restarted.get("/api/test")
        self.assertEqual(len(restarted.session.calls), 1)

    async def test_long_poll_interval_refreshes_before_next_poll(self):
        session = Session([(200, {"token": token(exp=datetime.now(timezone.utc).timestamp() + 86400), "refreshToken": "rotated"})])
        client = api.ZenbiClient(session, tokens={"token": token(), "refreshToken": "old"}, refresh_before=7500)
        await client.ensure_token()
        self.assertEqual(len(session.calls), 1)

    async def test_transient_refresh_error_keeps_saved_tokens(self):
        original = {"token": token(exp=1), "refreshToken": "old"}
        session = Session([(503, {}), (200, {"token": token(), "refreshToken": "new"})])
        saved = []
        client = api.ZenbiClient(session, tokens=dict(original), on_tokens=saved.append)
        with self.assertRaises(api.ZenbiError):
            await client.ensure_token()
        self.assertEqual(client.tokens, original)
        self.assertEqual(saved, [])
        await client.ensure_token()
        self.assertEqual(saved[0]["refreshToken"], "new")

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

    async def test_discover_optional_class_definitions(self):
        global_data = {"groupModelTimeFrames": [], "userModelTimeFrames": []}
        for status in (200, 403):
            session = Session([(200, global_data), (200, {"organisationModel": {"id": GROUP, "name": "Testskole"}}),
                               (status, {"userDefinedPersonFields": []})])
            client = api.ZenbiClient(session, tokens={"token": token(), "refreshToken": "old"})
            children, groups, school = await client.discover()
            self.assertEqual(school, "Testskole")
            self.assertTrue(session.calls[-1][1].endswith("/api/authentication/api/v1/globaldata/personfields"))

    async def test_posts_query_names_and_read_only_calls(self):
        session = Session([(200, {"boards": []})])
        client = api.ZenbiClient(session, tokens={"token": token(), "refreshToken": "old"})
        now = datetime.now(timezone.utc)
        await client.source("posts", now, now + timedelta(days=1))
        method, url, kwargs = session.calls[0]
        self.assertTrue(url.endswith("/api/message/api/v1/boards/date"))
        self.assertEqual(method, "GET")
        self.assertEqual({k for k, v in kwargs["params"]}, {"start", "end", "skip", "take"})
        self.assertEqual(dict(kwargs["params"])["take"], "100")

    async def test_posts_board_response_and_schema_errors(self):
        board = {"id": "synthetic-board", "title": "Skolekor",
                 "description": '{"ops":[{"insert":"Tilmelding fredag"}]}',
                 "start": "2026-10-10T10:32:00+02:00", "end": "2026-11-01T00:00:00+01:00"}
        client = api.ZenbiClient(Session([(200, {"boards": [board], "boardComments": []})]),
                                 tokens={"token": token(), "refreshToken": "old"})
        now = datetime.now(timezone.utc)
        result = await client.source("posts", now - timedelta(days=1), now)
        normalized = models.item(result[0], "posts", [])
        self.assertEqual(normalized["title"], "Skolekor")
        self.assertEqual(normalized["text"], "Tilmelding fredag")
        self.assertEqual(normalized["date"], board["start"])
        client = api.ZenbiClient(Session([(200, {"diaries": []})]),
                                 tokens={"token": token(), "refreshToken": "old"})
        with self.assertRaises(models.SchemaError):
            await client.source("posts", now, now)


if __name__ == "__main__":
    unittest.main()
