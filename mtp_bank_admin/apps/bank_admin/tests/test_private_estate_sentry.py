import datetime
import os
import runpy
import sys
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import sentry_sdk
from django.test import SimpleTestCase, override_settings

from bank_admin.management.commands.send_private_estate_emails import send_csv
from mtp_bank_admin.settings import base


@override_settings(PRIVATE_ESTATE_DOWNLOAD_SIGNING_KEY='synthetic-signing-key')
class PrivateEstateSentryTestCase(SimpleTestCase):
    def test_failed_email_does_not_include_download_token_in_sentry_event(self):
        # Read the actual settings without replacing Django's active settings or Sentry client.
        env = os.environ.copy()
        env.update(SENTRY_DSN='https://public@example.invalid/1', DEBUG='False')
        env.pop('APPLICATIONINSIGHTS_CONNECTION_STRING', None)
        with mock.patch.dict(os.environ, env, clear=True), mock.patch('sentry_sdk.init') as init, \
                mock.patch.object(sys, 'path', sys.path[:]):
            runpy.run_path(base.__file__)

        events = []

        def capture(event, hint):
            events.append(event)
            return None

        # Use the app's Sentry options with an isolated, offline client. Capture the
        # real send failure directly, without installing SDK-wide logging hooks.
        options = dict(init.call_args.kwargs, transport=lambda event: None, before_send=capture,
                       auto_session_tracking=False, default_integrations=False, integrations=[])
        client = sentry_sdk.Client(**options)
        self.addCleanup(client.close)
        notify = mock.Mock()
        notify.send_email.side_effect = RuntimeError('synthetic send failure')
        prison = {'short_name': 'Synthetic', 'cms_establishment_code': 'SYN', 'nomis_id': 'PR1'}
        with sentry_sdk.isolation_scope(), sentry_sdk.new_scope() as scope, \
                mock.patch('bank_admin.management.commands.send_private_estate_emails.upload_to_s3'), \
                mock.patch('mtp_common.tasks.NotifyClient.shared_client', return_value=notify), \
                self.assertLogs('mtp', level='ERROR'):
            scope.set_client(client)
            try:
                send_csv(prison, datetime.date(2026, 11, 13),
                         [{'remittance_emails': ['test@example.invalid']}], b'test', 0, 1)
            except RuntimeError as exc:
                sentry_sdk.capture_exception(exc)
            else:
                self.fail('Expected the synthetic email failure')

        url = notify.send_email.call_args.kwargs['personalisation']['attachment']
        token = parse_qs(urlsplit(url).query)['token'][0]
        self.assertTrue(events, 'The exception was not captured')
        for event in events:
            self.assertNotIn(token, repr(event))
            self.assertNotIn('/download-private?token=', repr(event))
