"""UI setup, relation selection and reauthentication."""
from __future__ import annotations

try:
    import probatio as vol  # Newer Home Assistant schema library.
except ImportError:
    import voluptuous as vol  # Home Assistant 2025.x.

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AuthenticationError, LoginChallenge, ZenbiClient, ZenbiError
from .const import (CONF_CHILDREN, CONF_DEVICE_ID, CONF_DAYS, CONF_INTERVAL,
                    CONF_ORGANIZATION_ID, DEFAULT_DAYS, DEFAULT_INTERVAL, DOMAIN)
from .models import SchemaError, guid


class ZenbiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.client = None
        self._challenge = {}
        self._children = {}
        self._school = "Zenbi"

    async def async_step_reauth(self, entry_data):
        return await self.async_step_user()

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        self.client = ZenbiClient(async_get_clientsession(self.hass), entry.data[CONF_DEVICE_ID],
                                  {k: entry.data[k] for k in ("token", "refreshToken")})
        try:
            self._children, _, self._school = await self.client.discover()
        except AuthenticationError:
            return self.async_abort(reason="login_expired")
        except (ZenbiError, SchemaError):
            return self.async_abort(reason="cannot_connect")
        return await self.async_step_children(user_input)

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            existing = self._get_reauth_entry() if self.source == config_entries.SOURCE_REAUTH else None
            self.client = ZenbiClient(async_get_clientsession(self.hass),
                                      existing.data.get(CONF_DEVICE_ID) if existing else None)
            try:
                await self.client.login(user_input[CONF_USERNAME].strip(), user_input[CONF_PASSWORD],
                                        existing.data.get(CONF_ORGANIZATION_ID) if existing else None)
                return await self._discover()
            except LoginChallenge as err:
                self._challenge = err.response
                organizations = self._challenge.get("organizations", [])
                if organizations:
                    return await self.async_step_organization()
                return self.async_abort(reason="unsupported_two_factor")
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except (ZenbiError, SchemaError):
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
        }), errors=errors)

    async def async_step_organization(self, user_input=None):
        organizations = self._challenge.get("organizations", [])
        choices = {str(index): row.get("name") or row.get("organisationId") or f"Skole {index + 1}"
                   for index, row in enumerate(organizations)}
        errors = {}
        if user_input is not None:
            try:
                row = organizations[int(user_input[CONF_ORGANIZATION_ID])]
                await self.client.select_organization(row["tempToken"])
                return await self._discover()
            except LoginChallenge:
                return self.async_abort(reason="unsupported_two_factor")
            except AuthenticationError:
                return self.async_abort(reason="login_expired")
            except (ZenbiError, SchemaError, KeyError, ValueError):
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="organization", data_schema=vol.Schema({
            vol.Required(CONF_ORGANIZATION_ID): vol.In(choices)
        }), errors=errors)

    async def _discover(self):
        self._children, _, self._school = await self.client.discover()
        account = guid(self.client.token_claims["usr"])
        organization = guid(self.client.token_claims["org"])
        unique_id = f"{organization}:{account}"
        if self.source == config_entries.SOURCE_REAUTH:
            if unique_id != self._get_reauth_entry().unique_id:
                return self.async_abort(reason="wrong_account")
            return self.async_update_reload_and_abort(self._get_reauth_entry(), data_updates={
                **self.client.tokens, CONF_DEVICE_ID: self.client.device_id})
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return await self.async_step_children()

    async def async_step_children(self, user_input=None):
        if user_input is not None:
            if self.source == config_entries.SOURCE_RECONFIGURE:
                return self.async_update_reload_and_abort(self._get_reconfigure_entry(), data_updates={
                    **self.client.tokens, CONF_CHILDREN: user_input[CONF_CHILDREN]})
            return self.async_create_entry(title=f"Zenbi · {self._school}", data={
                **self.client.tokens, CONF_DEVICE_ID: self.client.device_id,
                CONF_ORGANIZATION_ID: guid(self.client.token_claims["org"]),
                CONF_CHILDREN: user_input[CONF_CHILDREN], "school": self._school,
            })
        default = (self._get_reconfigure_entry().data.get(CONF_CHILDREN, [])
                   if self.source == config_entries.SOURCE_RECONFIGURE else list(self._children))
        return self.async_show_form(step_id="children", data_schema=vol.Schema({
            vol.Required(CONF_CHILDREN, default=default): selector.SelectSelector(
                selector.SelectSelectorConfig(multiple=True, options=[
                    {"value": uid, "label": f"{child['name']} {child['class']}".strip()}
                    for uid, child in self._children.items()]))
        }))

    @staticmethod
    def async_get_options_flow(config_entry):
        return ZenbiOptionsFlow()


class ZenbiOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(CONF_INTERVAL, default=self.config_entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)):
                vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
            vol.Required(CONF_DAYS, default=self.config_entry.options.get(CONF_DAYS, DEFAULT_DAYS)):
                vol.All(vol.Coerce(int), vol.Range(min=7, max=90)),
        }))
