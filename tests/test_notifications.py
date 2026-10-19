"""Verify routing uses mobile_app registrations, not editable phone names."""
import importlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from test_coordinator import UpdateFailed

notifications = importlib.import_module('zenbi.notifications')


class NotificationsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.targets = {'phone-a': 'webhook-a', 'phone-b': 'webhook-b'}
        self.util = types.ModuleType('homeassistant.components.mobile_app.util')
        self.util.webhook_id_from_device_id = lambda hass, device: self.targets.get(device)
        self.util.get_notify_service = lambda hass, webhook: {'webhook-a': 'renamed_original_a', 'webhook-b': 'registered_b'}.get(webhook)
        self.modules = patch.dict(sys.modules, {'homeassistant.components.mobile_app.util': self.util})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.hass = types.SimpleNamespace(services=types.SimpleNamespace(async_call=AsyncMock()))

    async def test_all_devices_deduplicated_with_context_and_literal_text(self):
        context = object()
        await notifications.async_send_reminder(self.hass, ['phone-a','phone-a','phone-b'],
                                                'Freja', '{{ literal text }}', context)
        calls = self.hass.services.async_call.await_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args[:2], ('notify', 'renamed_original_a'))
        self.assertEqual(calls[0].args[2], {'target':'webhook-a','title':'Freja','message':'{{ literal text }}'})
        self.assertTrue(all(call.kwargs['context'] is context and call.kwargs['blocking'] for call in calls))

    async def test_removed_phone_does_not_block_next_phone(self):
        with self.assertRaises(UpdateFailed):
            await notifications.async_send_reminder(self.hass, ['removed','phone-b'], 'T', 'M', None)
        self.assertEqual(self.hass.services.async_call.await_count, 1)
        self.assertEqual(self.hass.services.async_call.await_args.args[1], 'registered_b')

    async def test_failed_delivery_does_not_block_next_phone(self):
        self.hass.services.async_call.side_effect = [UpdateFailed('unavailable'), None]
        with self.assertRaises(UpdateFailed):
            await notifications.async_send_reminder(self.hass, ['phone-a','phone-b'], 'T', 'M', None)
        self.assertEqual(self.hass.services.async_call.await_count, 2)

    async def test_empty_recipients_is_explicit_error(self):
        with self.assertRaises(UpdateFailed):
            await notifications.async_send_reminder(self.hass, [], 'T', 'M', None)
        self.hass.services.async_call.assert_not_awaited()
