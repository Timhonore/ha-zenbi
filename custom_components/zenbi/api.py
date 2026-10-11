"""Async Zenbi client. Credentials are supplied by HA, never embedded here."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

import aiohttp

from .const import AUTH_PATH, BASE_URL, ENDPOINTS, ZERO_GUID
from .models import SchemaError, claims, guid, profile, rows


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
                 tokens: dict | None = None, on_tokens: Callable | None = None):
        self.session = session
        self.device_id = device_id or str(uuid4())
        self.tokens = tokens or {}
        self.on_tokens = on_tokens
        self._lock = asyncio.Lock()

    @property
    def token_claims(self):
        return claims(self.tokens["token"])

    async def _request(self, path, *, method="GET", params=None, body=None, token=None):
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        # Public app serializes arrays as repeated query parameters.
        query = [(key, str(v)) for key, value in (params or {}).items() if value is not None
                 for v in (value if isinstance(value, list) else [value])]
        try:
            async with self.session.request(method, BASE_URL + path, params=query, json=body,
                                            headers=headers, timeout=aiohttp.ClientTimeout(total=30),
                                            allow_redirects=False) as response:
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
        if response.get("token") and response.get("refreshToken"):
            metadata = claims(response["token"])
            if not isinstance(metadata.get("usr"), str) or not isinstance(metadata.get("org"), str):
                raise SchemaError("Token is missing account or organization routing")
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
            if not self.tokens.get("token") or not self.tokens.get("refreshToken"):
                raise AuthenticationError("Login required")
            expiry = self.token_claims.get("exp", 0)
            if not force and expiry > datetime.now(timezone.utc).timestamp() + 300:
                return
            response = await self._request(AUTH_PATH + "refresh-token", method="POST", body=self.tokens)
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
        children, groups = profile(data, self.token_claims)
        organization = await self.get("/api/organisation/api/v1/organisation")
        if not isinstance(organization, dict) or "organisationModel" not in organization:
            raise SchemaError("Missing organisationModel")
        school = organization["organisationModel"].get("name", "Zenbi")
        return children, groups, school

    async def source(self, name, start, end):
        params = {"start": start.isoformat(), "end": end.isoformat()}
        if name == "messages":
            params = {"take": 50}
        elif name == "unread":
            params = {}
        elif name == "posts":
            params = {"starttime": start.isoformat(), "endtime": end.isoformat()}
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
            return rows(response, "diaries")
        if name == "unread":
            if not isinstance(response, list) or any(not isinstance(v, str) for v in response):
                raise SchemaError("Expected unread id list")
            return response
        return rows(response)
