"""Zenbi constants. Public web-app contracts inspected 2026-10-11."""
DOMAIN = "zenbi"
BASE_URL = "https://app.zenbi.dk"
VERSION = "1.0.2"
ZERO_GUID = "00000000-0000-0000-0000-000000000000"
CONF_DEVICE_ID = "device_id"
CONF_ORGANIZATION_ID = "organization_id"
CONF_CHILDREN = "children"
CONF_INTERVAL = "scan_interval"
CONF_DAYS = "days_ahead"
DEFAULT_INTERVAL = 15
DEFAULT_DAYS = 30
AUTH_PATH = "/api/authentication/api/v1/account/"
TFA_AUTHENTICATOR = "1af86361-4646-4776-9eb5-9054de448620"
ENDPOINTS = {
    "homework": "/api/calendar/api/v1/homeworks/relations",
    "tasks": "/api/homework/api/v1/homework/tasks/relations",
    "weekly_plans": "/api/homework/api/v1/weeklyschedules/relations",
    "calendar": "/api/calendar/api/v1/calendaritems/own/dates",
    "child_calendar": "/api/calendar/api/v1/calendaritems/own/relation/users",
    "messages": "/api/message/api/v1/messageitems",
    "unread": "/api/message/api/v1/messageitem/unread/ids",
    "posts": "/api/diary/api/v1/diary/relations",
}
NAME_FIELDS = {
    "full": "9689cfbf-868d-451d-af83-61502e188731",
    "first": "fc19c23b-6338-4338-9547-2ebfbaa1f7a3",
    "middle": "6c96f310-0a24-49b5-9403-0e460304f6a7",
    "last": "a117ca7c-e0a8-4d34-8034-d477ef045689",
    "class": "95cfa0c2-fa5c-4f29-85a5-ab490d8ace66",
    "picture": "c4c7bc12-045d-462e-8acb-af5533f670fb",
}
