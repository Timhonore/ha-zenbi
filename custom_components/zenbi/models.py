"""Pure data parsing; never expose raw authentication/global-data payloads."""
from __future__ import annotations

import base64
from datetime import date, datetime, timedelta
from html import unescape
from html.parser import HTMLParser
import json
import re
from uuid import UUID
from zoneinfo import ZoneInfo

from .const import NAME_FIELDS, ZERO_GUID


class SchemaError(Exception):
    """An API response no longer matches the inspected web app."""


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "br", "li", "div"}:
            self.parts.append("\n")


def text(value) -> str:
    """Convert Quill delta (also JSON-encoded) or HTML to plain text."""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, (dict, list)):
            return text(parsed)
        parser = _Text()
        parser.feed(value)
        return unescape("".join(parser.parts)).strip()
    if isinstance(value, dict):
        return text(value.get("ops", []))
    if isinstance(value, list):
        return "".join(op.get("insert", "") for op in value
                       if isinstance(op, dict) and isinstance(op.get("insert"), str)).strip()
    return ""


def guid(value: str) -> str:
    """Decode Zenbi's base92-packed GUIDs used in its JWT claims."""
    try:
        return str(UUID(value))
    except ValueError:
        alphabet = "!" + "".join(chr(n) for n in range(35, 127) if chr(n) != "\\")
        number = 0
        for char in value:
            number = number * len(alphabet) + alphabet.index(char)
        return str(UUID(int=number))


def guid_list(value: str) -> list[str]:
    if not value:
        return []
    if re.fullmatch(r"[0-9a-f\-,:]+", value) and (len(value) == 36 or len(value) % 37 == 36):
        return [guid(v) for v in re.split(r"[,:]", value)]
    return [guid(v) for v in value.split()]


def claims(token: str) -> dict:
    """Decode routing/expiry metadata only. TLS/API validate the actual token."""
    try:
        payload = token.split(".")[1]
        result = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if not isinstance(result, dict):
            raise ValueError
        return result
    except (ValueError, IndexError, TypeError) as err:
        raise SchemaError("Invalid token format") from err


def rows(value, key: str | None = None) -> list[dict]:
    if key is not None:
        if not isinstance(value, dict) or key not in value:
            raise SchemaError(f"Missing response collection: {key}")
        value = value[key]
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise SchemaError("Expected a list of objects")
    return value


def profile(global_data: dict, token_claims: dict) -> tuple[dict, dict]:
    """Keep only names/classes of relations and group membership for filtering."""
    metadata = {}
    groups = {}
    for timeframe in rows(global_data, "groupModelTimeFrames"):
        for group in timeframe.get("users", []):
            for user_id in group.get("userIds", []):
                groups.setdefault(user_id, set()).add(group["groupId"])
    for group in global_data.get("meInfo", {}).get("groupUsers", []):
        for user_id in group.get("userIds", []):
            groups.setdefault(user_id, set()).add(group["groupId"])
    for timeframe in rows(global_data, "userModelTimeFrames"):
        for user in timeframe.get("userModels", []):
            for item in user.get("userMetadata", []):
                if item.get("personFieldId") in NAME_FIELDS.values():
                    metadata.setdefault(item["userId"], {})[item["personFieldId"]] = item.get("value", "")
    related = guid_list(token_claims.get("rel", ""))[1::2]
    children = {}
    for user_id in related:
        fields = metadata.get(user_id, {})
        name = fields.get(NAME_FIELDS["full"]) or " ".join(
            fields.get(NAME_FIELDS[k], "") for k in ("first", "middle", "last")
            if fields.get(NAME_FIELDS[k])) or f"Relation {user_id[:8]}"
        children[user_id] = {"name": name, "class": fields.get(NAME_FIELDS["class"], "")}
    return children, groups


def parse_dt(value, zone: str) -> datetime:
    if not isinstance(value, str):
        raise SchemaError("Missing or invalid date")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        tz = ZoneInfo(zone)
        return result.replace(tzinfo=tz) if result.tzinfo is None else result.astimezone(tz)
    except ValueError as err:
        raise SchemaError("Invalid ISO date") from err


def participant_ids(row: dict) -> set[str]:
    ids = set(row.get("participantIds", [])) | set(row.get("recipientIds", [])) | set(row.get("userIds", []))
    ids.update(p["participantId"] for p in row.get("participantModels", []) if "participantId" in p)
    if row.get("userId"):
        ids.add(row["userId"])
    return ids


def children_for(row: dict, children: dict, groups: dict) -> list[str]:
    ids = participant_ids(row)
    return [uid for uid in children if ids & ({uid} | groups.get(uid, set()))]


def visible_calendar(raw: list[dict], account_id: str, groups: dict) -> list[dict]:
    """Mirror frontend masking of private events for non-participants."""
    result = []
    account_participants = {account_id} | groups.get(account_id, set())
    for row in raw:
        if row.get("private") and not participant_ids(row) & account_participants:
            result.append({**row, "title": "Privat begivenhed", "description": "", "note": "", "files": []})
        else:
            result.append(row)
    return result


def expand_calendar(raw: list[dict], start: datetime, end: datetime, zone: str) -> list[dict]:
    """Expand inspected daily/weekly rules, including removed/moved instances."""
    output = []
    for row in raw:
        repetition = row.get("repetition")
        if not repetition:
            occurrences = [(parse_dt(row.get("start"), zone), parse_dt(row.get("end"), zone))]
        else:
            frequency = repetition.get("frequency")
            if frequency not in (1, 2):
                raise SchemaError("Unsupported calendar recurrence frequency")
            origin = parse_dt(repetition.get("startDate"), zone)
            limit = parse_dt(repetition["endDate"], zone) if repetition.get("endDate") else end
            step = max(1, int(repetition.get("step", 1)))
            flags = int(repetition.get("dayFlags", 0))
            duration = timedelta(minutes=int(repetition.get("minuteLength", 0)))
            count_limit = int(repetition.get("repeatTimes", 0))
            # Count from series start for repeatTimes; cap malformed/unbounded work.
            day = origin.date()
            last_day = min(limit.date(), end.date())
            if (last_day - day).days > 36525:
                raise SchemaError("Calendar recurrence exceeds expansion limit")
            occurrences = []
            count = 0
            deviations = {parse_dt(d["date"], zone).date(): d for d in repetition.get("deviationDates", [])}
            moved_seen = set()
            while day <= last_day:
                delta = (day - origin.date()).days
                weeks = ((day - timedelta(days=day.weekday())) - (origin.date() - timedelta(days=origin.weekday()))).days // 7
                eligible = (delta % step == 0) if frequency == 1 else (weeks % step == 0 and bool(flags & (1 << day.weekday())))
                if eligible:
                    if count_limit and count >= count_limit:
                        break
                    count += 1
                    event_start = datetime.combine(day, origin.timetz())
                    event_end = event_start + duration
                    deviation = deviations.get(day)
                    if deviation:
                        moved_seen.add(day)
                        if deviation.get("type") == 0:
                            day += timedelta(days=1)
                            continue
                        if deviation.get("type") != 1:
                            raise SchemaError("Unsupported calendar deviation")
                        event_start = parse_dt(deviation.get("start"), zone)
                        event_end = parse_dt(deviation.get("end"), zone)
                    occurrences.append((event_start, event_end))
                day += timedelta(days=1)
            # A moved instance can enter the requested range from outside it.
            for original_day, deviation in deviations.items():
                if original_day not in moved_seen and deviation.get("type") == 1:
                    occurrences.append((parse_dt(deviation.get("start"), zone), parse_dt(deviation.get("end"), zone)))
        for event_start, event_end in occurrences:
            only_date = bool(repetition.get("onlyDate", False)) if repetition else bool(row.get("onlyDate", False))
            if event_end <= event_start:
                if only_date:
                    event_end = event_start + timedelta(days=1)
                else:
                    raise SchemaError("Calendar event ends before it starts")
            if event_start < end and event_end > start:
                output.append({"id": f"{row['id']}:{event_start.isoformat()}", "source_id": row["id"],
                               "title": row.get("title") or "Begivenhed", "text": text(row.get("description")),
                               "start": event_start.date().isoformat() if only_date else event_start.isoformat(),
                               "end": event_end.date().isoformat() if only_date else event_end.isoformat(),
                               "all_day": only_date})
    return sorted(output, key=lambda row: row["start"])


def item(row: dict, kind: str, children: list[str], *, title: str | None = None) -> dict:
    if not row.get("id"):
        raise SchemaError("Missing item id")
    return {"id": row["id"], "kind": kind, "title": title or row.get("title") or row.get("headline") or row.get("subject") or kind,
            "text": text(row.get("description")), "date": row.get("date") or row.get("closes") or row.get("start") or row.get("dateTime"),
            "end": row.get("end"), "updated": row.get("updatedTime"), "children": children,
            "attachment_count": len(row.get("files") or [])}
