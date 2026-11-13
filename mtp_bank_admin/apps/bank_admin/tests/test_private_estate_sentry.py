import os
import subprocess
import sys
import textwrap

from django.test import SimpleTestCase


class PrivateEstateSentryTestCase(SimpleTestCase):
    def test_failed_email_does_not_include_download_token_in_sentry_event(self):
        # Use a separate process so this test exercises the real settings and Sentry
        # logging integration without changing the test runner's global client.
        script = textwrap.dedent("""
            import datetime
            from unittest import mock
            from urllib.parse import parse_qs, urlsplit

            import django
            import sentry_sdk

            init_sentry = sentry_sdk.init
            def init_offline(**kwargs):
                kwargs['transport'] = lambda event: None
                kwargs['auto_session_tracking'] = False
                return init_sentry(**kwargs)

            with mock.patch('sentry_sdk.init', side_effect=init_offline):
                django.setup()
            from bank_admin.management.commands.send_private_estate_emails import send_csv

            events = []
            def capture(event, hint):
                events.append(event)
                return None  # Do not transmit the synthetic event.

            sentry_sdk.get_client().options['before_send'] = capture
            notify = mock.Mock()
            notify.send_email.side_effect = RuntimeError('synthetic send failure')
            prison = {'short_name': 'Synthetic', 'cms_establishment_code': 'SYN', 'nomis_id': 'PR1'}
            with mock.patch('bank_admin.management.commands.send_private_estate_emails.upload_to_s3'), \\
                    mock.patch('mtp_common.tasks.NotifyClient.shared_client', return_value=notify):
                try:
                    send_csv(prison, datetime.date(2026, 11, 13),
                             [{'remittance_emails': ['test@example.invalid']}], b'test', 0, 1)
                except RuntimeError:
                    pass
            url = notify.send_email.call_args.kwargs['personalisation']['attachment']
            token = parse_qs(urlsplit(url).query)['token'][0]
            assert events, 'The Sentry logging integration did not capture the failed send'
            assert all(token not in repr(event) for event in events), 'Bearer token present in Sentry event'
            assert all('/download-private?token=' not in repr(event) for event in events), 'Link in Sentry event'
        """)
        env = os.environ.copy()
        env.update({
            'DJANGO_SETTINGS_MODULE': 'mtp_bank_admin.settings',
            'ENV': 'local',
            'DEBUG': 'False',
            'SENTRY_DSN': 'https://public@example.invalid/1',
            'PRIVATE_ESTATE_DOWNLOAD_SIGNING_KEY': 'synthetic-signing-key',
        })
        env.pop('APPLICATIONINSIGHTS_CONNECTION_STRING', None)
        result = subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
