"""Send blueprint reminders using HA's registered Companion App targets."""
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


async def async_send_reminder(hass, device_ids, title, message, context):
    """Resolve device IDs through mobile_app, without guessing service names."""
    from homeassistant.components.mobile_app.util import (
        get_notify_service, webhook_id_from_device_id,
    )

    if not device_ids:
        raise HomeAssistantError("Vælg mindst én telefon til påmindelsen.")
    failures = 0
    for device in dict.fromkeys(device_ids):
        try:
            webhook = webhook_id_from_device_id(hass, device)
            service = get_notify_service(hass, webhook) if webhook else None
            if not service:
                raise HomeAssistantError("Telefonens notifikationstjeneste er ikke tilgængelig.")
            await hass.services.async_call(
                "notify", service, {"target": webhook, "title": title, "message": message},
                blocking=True, context=context,
            )
        except (HomeAssistantError, KeyError):
            # A removed/offline registration must not prevent other recipients.
            failures += 1
    if failures:
        raise HomeAssistantError(
            f"Påmindelsen kunne ikke sendes til {failures} af de valgte telefoner. "
            "De øvrige telefoner er forsøgt. Kontrollér Companion App-registreringen."
        )


def async_register_notifications(hass):
    """Register once for every account and blueprint instance."""
    try:
        import probatio as vol
    except ImportError:
        import voluptuous as vol

    async def send(call):
        await async_send_reminder(
            hass, call.data["device_ids"], call.data["title"], call.data["message"], call.context,
        )

    hass.services.async_register(
        DOMAIN, "send_reminder", send,
        schema=vol.Schema({vol.Required("device_ids"): [str],
                           vol.Required("message"): str,
                           vol.Optional("title", default="Zenbi"): str}),
    )
