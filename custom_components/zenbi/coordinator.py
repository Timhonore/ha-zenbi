"""One poll coordinator; sources fail separately rather than becoming empty."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AuthenticationError, RateLimitError, ZenbiClient, ZenbiError
from .const import CONF_CHILDREN, CONF_DAYS, CONF_INTERVAL, DEFAULT_DAYS, DEFAULT_INTERVAL, DOMAIN, ENDPOINTS
from .models import SchemaError, children_for, expand_calendar, item, parse_dt, guid, visible_calendar

_LOGGER = logging.getLogger(__name__)


class ZenbiCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client: ZenbiClient):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(minutes=entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)))
        self.entry = entry
        self.options_snapshot = dict(entry.options)
        self.client = client
        self.children = {}
        self.groups = {}
        self.school = entry.data.get("school", "Zenbi")

    async def _async_setup(self):
        try:
            relations, self.groups, self.school = await self.client.discover()
            self.children = {uid: relations.get(uid, {"name": f"Relation {uid[:8]}", "class": ""})
                             for uid in self.entry.data.get(CONF_CHILDREN, [])}
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed("Log ind på Zenbi igen") from err
        except (ZenbiError, SchemaError) as err:
            raise UpdateFailed("Kunne ikke hente konto og relationer") from err

    async def _async_update_data(self):
        now = dt_util.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=2)
        end = start + timedelta(days=self.entry.options.get(CONF_DAYS, DEFAULT_DAYS) + 3)
        zone = self.hass.config.time_zone
        # Throttle concurrency and avoid fetching credentials multiple times.
        try:
            await self.client.ensure_token()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed("Log ind på Zenbi igen") from err
        except (ZenbiError, SchemaError) as err:
            raise UpdateFailed("Kunne ikke forny forbindelsen til Zenbi") from err
        semaphore = asyncio.Semaphore(3)

        async def fetch(name):
            async with semaphore:
                source_start = start - timedelta(days=30) if name == "posts" else start
                return await self.client.source(name, source_start, end)

        names = list(ENDPOINTS)
        results = await asyncio.gather(*(fetch(name) for name in names), return_exceptions=True)
        raw, status = {}, {}
        for name, result in zip(names, results, strict=True):
            if isinstance(result, AuthenticationError):
                raise ConfigEntryAuthFailed("Log ind på Zenbi igen") from result
            if isinstance(result, Exception):
                status[name] = type(result).__name__
                _LOGGER.debug("Zenbi source %s failed (%s)", name, type(result).__name__)
            else:
                if name in ("calendar", "child_calendar"):
                    result = visible_calendar(result, guid(self.client.token_claims["usr"]), self.groups)
                raw[name] = result
                status[name] = "ok"
        if any(isinstance(r, RateLimitError) for r in results):
            self.update_interval = timedelta(minutes=max(30, self.entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)))
        else:
            self.update_interval = timedelta(minutes=self.entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL))
        data = {"status": status, "updated": now.isoformat(), "children": self.children,
                "school": self.school, "items": {}, "events": {}, "unmapped": {},
                "range_start": start.isoformat(), "range_end": end.isoformat()}
        calendars = {row["id"]: row for name in ("calendar", "child_calendar") for row in raw.get(name, [])}
        for name in ("calendar", "child_calendar"):
            if name not in raw:
                continue
            try:
                data["events"][name] = expand_calendar(raw[name], start, end, zone)
            except (SchemaError, KeyError, TypeError, ValueError):
                status[name] = "SchemaError"
        data["child_events"] = {}
        if status.get("child_calendar") == "ok":
            data["unmapped"]["child_calendar"] = sum(
                not children_for(row, self.children, self.groups)
                for row in raw.get("child_calendar", []))
            for uid in self.children:
                matching = [row for row in raw.get("child_calendar", [])
                            if uid in children_for(row, self.children, self.groups)]
                try:
                    data["child_events"][uid] = expand_calendar(matching, start, end, zone)
                except (SchemaError, KeyError, TypeError, ValueError):
                    status["child_calendar"] = "SchemaError"
        for name in ("homework", "tasks", "weekly_plans", "messages", "posts"):
            if name not in raw:
                continue
            try:
                source = raw[name]
                recipients = {}
                if name == "tasks":
                    recipients = {r["homeworkTaskId"]: r for r in source["recipients"]}
                    source = source["homeworkTasks"]
                normalized = []
                unmapped = 0
                for row in source:
                    association = row
                    title = None
                    if name == "homework":
                        association = calendars.get(row.get("calendarItemId"), {})
                        title = association.get("title") or "Lektier"
                    elif name == "tasks":
                        association = recipients.get(row.get("id"), {})
                    child_ids = children_for(association, self.children, self.groups)
                    if not child_ids and name in ("homework", "tasks", "weekly_plans"):
                        unmapped += 1
                    normalized.append(item(row, name, child_ids, title=title))
                    if name in ("homework", "tasks", "weekly_plans"):
                        parse_dt(normalized[-1]["date"], zone)
                data["items"][name] = normalized
                data["unmapped"][name] = unmapped
            except (SchemaError, KeyError, TypeError, ValueError):
                status[name] = "SchemaError"
        if "unread" in raw:
            data["unread_count"] = len(raw["unread"])
        if not any(v == "ok" for v in status.values()):
            raise UpdateFailed("Ingen Zenbi-datakilder kunne hentes")
        return data

    def items(self, kind, child_id=None):
        result = self.data["items"].get(kind, [])
        if child_id is not None:
            result = [row for row in result if child_id in row["children"]]
        return result

    def future_items(self, kind, child_id=None):
        today = dt_util.now().date()
        result = []
        for row in self.items(kind, child_id):
            value = row.get("date")
            if not value:
                continue
            try:
                if parse_dt(value, self.hass.config.time_zone).date() >= today:
                    result.append(row)
            except SchemaError:
                continue
        return sorted(result, key=lambda row: row["date"])
