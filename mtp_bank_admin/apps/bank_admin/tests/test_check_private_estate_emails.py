import datetime
from datetime import timezone
import json
from unittest import mock
from urllib.parse import parse_qsl, urlsplit

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings
from mtp_common.auth.api_client import MoJOAuth2Session
from mtp_common.auth.test_utils import generate_tokens
from mtp_common.notify import NotifyClient
from mtp_common.test_utils.notify import (
    GOVUK_NOTIFY_API_BASE_URL, GOVUK_NOTIFY_TEST_API_KEY, mock_all_templates_response,
)
import responses

from bank_admin.tests.utils import TEST_BANK_ACCOUNT, api_url, mock_bank_holidays

COMMAND = 'check_private_estate_emails'
PATH = 'bank_admin.management.commands.check_private_estate_emails'


def mock_api_session(mocked_api_session):
    mock_session = MoJOAuth2Session()
    mock_session.token = generate_tokens()
    mocked_api_session.return_value = mock_session


def mock_notifications(rsps, sent_references):
    """
    Fakes GOV.UK Notify's `get_all_notifications`: returns one notification for references that
    were 'sent', and none otherwise.
    """
    def callback(request):
        reference = dict(parse_qsl(urlsplit(request.url).query)).get('reference', '')
        notifications = []
        if reference in sent_references:
            notifications = [{'id': '1', 'reference': reference, 'status': 'delivered'}]
        return 200, {}, json.dumps({'notifications': notifications})

    rsps.add_callback(
        responses.GET,
        f'{GOVUK_NOTIFY_API_BASE_URL}/v2/notifications',
        callback=callback,
        content_type='application/json',
    )


PRIVATE_ESTATE_BATCHES = {
    'count': 2,
    'results': [
        {'date': '2019-02-15', 'prison': 'PR1', 'total_amount': 2500,
         'bank_account': TEST_BANK_ACCOUNT, 'remittance_emails': ['private@mtp.local']},
        {'date': '2019-02-15', 'prison': 'PR2', 'total_amount': 2000,
         'bank_account': TEST_BANK_ACCOUNT, 'remittance_emails': ['private@mtp.local']},
    ],
}


@override_settings(GOVUK_NOTIFY_API_KEY=GOVUK_NOTIFY_TEST_API_KEY)
class CheckPrivateEstateEmailsTestCase(SimpleTestCase):
    def setUp(self):
        # the Notify client is cached across the process, ensure a fresh one per test
        NotifyClient.shared_client.cache_clear()

    @mock.patch(f'{PATH}.is_first_instance', return_value=True)
    @mock.patch(f'{PATH}.api_client.get_authenticated_api_session')
    @mock.patch(f'{PATH}.timezone')
    def test_not_checked_on_weekend_or_bank_holiday(self, mocked_timezone, mocked_api_session, _mocked_first):
        mocked_api_session.side_effect = AssertionError('Should not be called')

        # Sunday
        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 17, 12, tzinfo=timezone.utc)
        with responses.RequestsMock() as rsps:
            mock_bank_holidays(rsps)
            call_command(COMMAND)

        # Boxing day (bank holiday)
        mocked_timezone.now.return_value = datetime.datetime(2016, 12, 26, 12, tzinfo=timezone.utc)
        with responses.RequestsMock() as rsps:
            mock_bank_holidays(rsps)
            call_command(COMMAND)

    @mock.patch(f'{PATH}.is_first_instance', return_value=False)
    @mock.patch(f'{PATH}.api_client.get_authenticated_api_session')
    @mock.patch(f'{PATH}.timezone')
    def test_skipped_on_non_key_instance(self, mocked_timezone, mocked_api_session, _mocked_first):
        mocked_api_session.side_effect = AssertionError('Should not be called')
        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=timezone.utc)
        call_command(COMMAND)

    @mock.patch(f'{PATH}.is_first_instance', return_value=True)
    @mock.patch(f'{PATH}.api_client.get_authenticated_api_session')
    @mock.patch(f'{PATH}.timezone')
    def test_passes_when_all_prisons_sent(self, mocked_timezone, mocked_api_session, _mocked_first):
        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=timezone.utc)
        with responses.RequestsMock() as rsps:
            mock_bank_holidays(rsps)
            mock_api_session(mocked_api_session)
            rsps.add(rsps.GET, api_url('private-estate-batches/'), json=PRIVATE_ESTATE_BATCHES)
            mock_all_templates_response(rsps)
            mock_notifications(rsps, sent_references={
                'bank-admin-private-csv-2019-02-15-PR1',
                'bank-admin-private-csv-2019-02-15-PR2',
            })

            call_command(COMMAND)

    @mock.patch(f'{PATH}.is_first_instance', return_value=True)
    @mock.patch(f'{PATH}.api_client.get_authenticated_api_session')
    @mock.patch(f'{PATH}.timezone')
    def test_raises_when_a_prison_missing(self, mocked_timezone, mocked_api_session, _mocked_first):
        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=timezone.utc)
        with responses.RequestsMock() as rsps:
            mock_bank_holidays(rsps)
            mock_api_session(mocked_api_session)
            rsps.add(rsps.GET, api_url('private-estate-batches/'), json=PRIVATE_ESTATE_BATCHES)
            mock_all_templates_response(rsps)
            # PR2's email is missing from Notify
            mock_notifications(rsps, sent_references={'bank-admin-private-csv-2019-02-15-PR1'})

            with self.assertRaises(CommandError) as ctx:
                call_command(COMMAND)
            self.assertIn('PR2', str(ctx.exception))

    @mock.patch(f'{PATH}.is_first_instance', return_value=True)
    @mock.patch(f'{PATH}.api_client.get_authenticated_api_session')
    @mock.patch(f'{PATH}.timezone')
    def test_passes_when_no_batches(self, mocked_timezone, mocked_api_session, _mocked_first):
        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=timezone.utc)
        with responses.RequestsMock() as rsps:
            mock_bank_holidays(rsps)
            mock_api_session(mocked_api_session)
            rsps.add(rsps.GET, api_url('private-estate-batches/'), json={'count': 0, 'results': []})

            call_command(COMMAND)
