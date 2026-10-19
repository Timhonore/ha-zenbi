"""Async Zenbi client. Credentials are supplied by HA, never embedded here."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

import aiohttp

from .const import AUTH_PATH, BASE_URL, ENDPOINTS, ZERO_GUID
from .models import SchemaError, claims, guid, profile, rows

SESSION_COOKIE = "__Host-zenbi-session"
AUTH_FIELDS = ("token", "refreshToken", "cookies", "maxAge", "expires_at")


def stored_auth(data):
    """Read either the legacy token pair or the current cookie session."""
    return {key: data[key] for key in AUTH_FIELDS if key in data}




class ZenbiError(Exception):
    """A sanitized API error."""


class AuthenticationError(ZenbiError):
    """Invalid or expired authentication."""


class PermissionError(ZenbiError):
    """Account does not have permission for a data source."""


class RateLimitError(ZenbiError):
    """Server rate limit."""


class LoginChallenge(ZenbiError):
    def __init__(self, response: dict):
        super().__init__("Additional login step required")
        self.response = response


class ZenbiClient:
    def __init__(self, session: aiohttp.ClientSession, device_id: str | None = None,
                 tokens: dict | None = None, on_tokens: Callable | None = None,
                 refresh_before: int = 3600):
        self.session = session
        self.device_id = device_id or str(uuid4())
        self.tokens = dict(tokens or {})
        self.cookies = {key: value for key, value in (self.tokens.get("cookies") or {}).items()
                        if key == SESSION_COOKIE and isinstance(value, str) and value}
        self.on_tokens = on_tokens
        self.refresh_before = max(3600, refresh_before)
        self._lock = asyncio.Lock()

    @property
    def token_claims(self):
        return claims(self.tokens["token"])

    async def _request(self, path, *, method="GET", params=None, body=None, token=None):
        headers = {"Accept": "application/json"}
        if token and not self.cookies:
            headers["Authorization"] = f"Bearer {token}"
        if method == "POST":
            headers["Origin"] = BASE_URL
        # Public app serializes arrays as repeated query parameters.
        query = [(key, str(v)) for key, value in (params or {}).items() if value is not None
                 for v in (value if isinstance(value, list) else [value])]
        request_cookies = dict(self.cookies)
        try:
            async with self.session.request(method, BASE_URL + path, params=query, json=body,
                                            headers=headers, cookies=request_cookies, timeout=aiohttp.ClientTimeout(total=30),
                                            allow_redirects=False) as response:
                # Only retain Zenbi's host-bound session cookie, separately for
                # each account. Never use HA's shared session cookie jar.
                cookie = getattr(response, "cookies", {}).get(SESSION_COOKIE)
                if (cookie is not None and not cookie["domain"] and cookie["path"] == "/"
                        and request_cookies == self.cookies):
                    if cookie.value and cookie["max-age"] != "0":
                        self.cookies = {SESSION_COOKIE: cookie.value}
                    else:
                        self.cookies = {}
                    if self.tokens:
                        self.tokens["cookies"] = dict(self.cookies)
                        if self.on_tokens:
                            self.on_tokens(dict(self.tokens))
                if response.status == 401:
                    raise AuthenticationError("Authentication rejected")
                if response.status == 403:
                    raise PermissionError("Permission denied")
                if response.status == 429:
                    raise RateLimitError("Rate limited; wait before retrying")
                if response.status >= 400 or response.status < 200 or response.status >= 300:
                    raise ZenbiError(f"HTTP {response.status}")
                try:
                    return await response.json()
                except (ValueError, aiohttp.ContentTypeError) as err:
                    raise SchemaError("Expected JSON response") from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise ZenbiError("Could not connect to Zenbi") from err

    def accept_login(self, response):
        if not isinstance(response, dict):
            raise SchemaError("Invalid authentication response")
        if response.get("error"):
            raise AuthenticationError("Login rejected")
        if response.get("changePassword"):
            raise AuthenticationError("Password must be changed on Zenbi's website")
        max_age = response.get("maxAge")
        cookie_login = (isinstance(max_age, (int, float)) and not isinstance(max_age, bool)
                        and max_age > 0 and bool(self.cookies.get(SESSION_COOKIE)))
        if response.get("token") and (response.get("refreshToken") or cookie_login):
            metadata = claims(response["token"])
            if not isinstance(metadata.get("usr"), str) or not isinstance(metadata.get("org"), str):
                raise SchemaError("Token is missing account or organization routing")
            if cookie_login:
                # maxAge is milliseconds in the current public web client.
                self.tokens = {"token": response["token"], "refreshToken": None,
                               "cookies": dict(self.cookies), "maxAge": max_age,
                               "expires_at": datetime.now(timezone.utc).timestamp() + max_age / 1000}
            else:
                self.tokens = {"token": response["token"], "refreshToken": response["refreshToken"]}
            if self.on_tokens:
                self.on_tokens(dict(self.tokens))
            return
        if response.get("organizations") or response.get("twoFactorAuthentication"):
            raise LoginChallenge(response)
        raise SchemaError("Authentication response contains neither tokens nor challenge")

    async def login(self, username, password, organization_id=None):
        response = await self._request(AUTH_PATH + "authenticate", method="POST", body={
            "username": username, "password": password, "uniqueDeviceId": self.device_id,
            "organizationId": organization_id, "twoFactorType": ZERO_GUID})
        self.accept_login(response)

    async def select_organization(self, temp_token):
        response = await self._request(AUTH_PATH + "swap", method="POST", body={
            "uniqueDeviceId": self.device_id, "tempToken": temp_token, "twoFactorType": ZERO_GUID})
        self.accept_login(response)

    async def ensure_token(self, force=False, rejected_token=None):
        async with self._lock:
            # Concurrent 401s must not rotate the same refresh token twice.
            if rejected_token and rejected_token != self.tokens.get("token"):
                return
            if not self.tokens.get("token"):
                raise AuthenticationError("Login required")
            cookie_auth = "maxAge" in self.tokens
            if cookie_auth:
                if not self.cookies.get(SESSION_COOKIE):
                    raise AuthenticationError("Zenbi session expired; log in again")
                expiry = self.tokens.get("expires_at", 0)
                # Avoid renewing on every request when Zenbi issues a short lease.
                margin = min(self.refresh_before, self.tokens["maxAge"] / 2000)
            else:
                if not self.tokens.get("refreshToken"):
                    raise AuthenticationError("Login required")
                expiry = self.token_claims.get("exp", 0)
                margin = self.refresh_before
            if not force and expiry > datetime.now(timezone.utc).timestamp() + margin:
                return
            # Current Zenbi authenticates all requests by cookie. The refresh
            # endpoint now takes an empty body, not a token/refreshToken pair.
            response = await self._request(
                AUTH_PATH + "refresh-token", method="POST",
                body=None if cookie_auth else dict(self.tokens),
                token=None if cookie_auth else self.tokens["token"])
            try:
                self.accept_login(response)
            except LoginChallenge as err:
                raise AuthenticationError("Login required") from err

    async def get(self, path, params=None):
        await self.ensure_token()
        token = self.tokens["token"]
        try:
            return await self._request(path, params=params, token=token)
        except AuthenticationError:
            await self.ensure_token(force=True, rejected_token=token)
            return await self._request(path, params=params, token=self.tokens["token"])

    async def discover(self):
        data = await self.get("/api/authentication/api/v1/globaldata")
        organization = await self.get("/api/organisation/api/v1/organisation")
        if not isinstance(organization, dict) or "organisationModel" not in organization:
            raise SchemaError("Missing organisationModel")
        try:
            person_fields = await self.get("/api/authentication/api/v1/globaldata/personfields")
        except AuthenticationError:
            raise
        except ZenbiError:
            # Field labels are optional; unavailable labels must not break all school data.
            person_fields = {}
        if not isinstance(person_fields, dict):
            person_fields = {}
        metadata = {**self.token_claims, "org": organization["organisationModel"].get("id") or self.token_claims.get("org")}
        children, groups = profile(data, metadata, person_fields)
        school = organization["organisationModel"].get("name", "Zenbi")
        return children, groups, school

    async def source(self, name, start, end):
        params = {"start": start.isoformat(), "end": end.isoformat()}
        if name == "messages":
            params = {"take": 50}
        elif name == "unread":
            params = {}
        elif name == "posts":
            params = {"start": start.isoformat(), "end": end.isoformat(), "skip": 0, "take": 100}
        response = await self.get(ENDPOINTS[name], params)
        if name == "messages":
            parents = rows(response, "messageParents")
            childs = rows(response, "messageChilds")
            return parents + childs
        if name == "tasks":
            rows(response, "homeworkTasks")
            rows(response, "recipients")
            return response
        if name == "posts":
            return rows(response, "boards")
        if name == "unread":
            if not isinstance(response, list) or any(not isinstance(v, str) for v in response):
                raise SchemaError("Expected unread id list")
            return response
        return rows(response)
