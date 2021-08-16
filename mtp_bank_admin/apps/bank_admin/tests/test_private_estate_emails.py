import base64
import datetime
import io
from unittest import mock
import zipfile

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from django.utils.timezone import utc
from mtp_common.auth.api_client import MoJOAuth2Session
from mtp_common.auth.test_utils import generate_tokens
from mtp_common.test_utils.notify import NotifyMock, GOVUK_NOTIFY_TEST_API_KEY
import responses

from bank_admin.tests.utils import TEST_PRISONS, TEST_BANK_ACCOUNT, api_url, mock_bank_holidays


def mock_api_session(mocked_api_session):
    mock_session = MoJOAuth2Session()
    mock_session.token = generate_tokens()
    mocked_api_session.return_value = mock_session


class PrivateEstateEmailTestCase(SimpleTestCase):
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.api_client.get_authenticated_api_session')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.timezone')
    def test_not_scheduled_on_weekend_or_bank_holiday(self, mocked_timezone, mocked_api_session):
        mocked_api_session.side_effect = AssertionError('Should not be called')

        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 17, 12, tzinfo=utc)
        with responses.RequestsMock() as rsps:
            mock_bank_holidays(rsps)
            call_command('send_private_estate_emails', scheduled=True)

        mocked_timezone.now.return_value = datetime.datetime(2016, 12, 26, 12, tzinfo=utc)
        with responses.RequestsMock() as rsps:
            mock_bank_holidays(rsps)
            call_command('send_private_estate_emails', scheduled=True)

    @mock.patch('bank_admin.management.commands.send_private_estate_emails.api_client.get_authenticated_api_session')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.timezone')
    def test_runs_on_weekday(self, mocked_timezone, mocked_api_session):
        mocked_api_session.side_effect = AssertionError('Must be called')

        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=utc)
        with responses.RequestsMock() as rsps:
            mock_bank_holidays(rsps)
            with self.assertRaisesMessage(AssertionError, 'Must be called'):
                call_command('send_private_estate_emails', scheduled=True)

    @mock.patch('bank_admin.management.commands.send_private_estate_emails.send_csv')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.api_client.get_authenticated_api_session')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.timezone')
    def test_empty_batches(self, mocked_timezone, mocked_api_session, mocked_send_csv):
        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=utc)
        mocked_send_csv.side_effect = AssertionError('Should not be called')
        with responses.RequestsMock() as rsps:
            mock_bank_holidays(rsps)
            mock_api_session(mocked_api_session)
            rsps.add(rsps.POST, api_url('transactions/reconcile/'))
            rsps.add(rsps.GET, api_url('private-estate-batches/'), json={
                'count': 0,
                'results': []
            })
            call_command('send_private_estate_emails', scheduled=True)

    @mock.patch('bank_admin.management.commands.send_private_estate_emails.send_csv')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.api_client.get_authenticated_api_session')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.timezone')
    def test_csv_created(self, mocked_timezone, mocked_api_session, mocked_send_csv):
        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=utc)
        with responses.RequestsMock() as rsps:
            mock_bank_holidays(rsps)
            mock_api_session(mocked_api_session)
            rsps.add(rsps.POST, api_url('transactions/reconcile/'))
            rsps.add(rsps.GET, api_url('private-estate-batches/'), json={
                'count': 5,
                'results': [
                    # no bank account, ignored
                    {'date': '2019-02-15',
                     'prison': 'ERR',
                     'total_amount': 2500,
                     'bank_account': None},
                    # ok
                    {'date': '2019-02-15',
                     'prison': 'PR1',
                     'total_amount': 2500,
                     'bank_account': TEST_BANK_ACCOUNT,
                     'remittance_emails': ['private@mtp.local']},
                    # empty batch, ignored
                    {'date': '2019-02-16',
                     'prison': 'PR1',
                     'total_amount': 0,
                     'bank_account': TEST_BANK_ACCOUNT,
                     'remittance_emails': ['private@mtp.local']},
                    # ok
                    {'date': '2019-02-17',
                     'prison': 'PR1',
                     'total_amount': 1200,
                     'bank_account': TEST_BANK_ACCOUNT,
                     'remittance_emails': ['private@mtp.local']},
                    # ok
                    {'date': '2019-02-15',
                     'prison': 'PR2',
                     'total_amount': 2000,
                     'bank_account': TEST_BANK_ACCOUNT,
                     'remittance_emails': ['private@mtp.local']},
                ]
            })
            rsps.add(rsps.GET, api_url('prisons/'), json={'count': len(TEST_PRISONS), 'results': TEST_PRISONS})
            rsps.add(rsps.PATCH, api_url('private-estate-batches/PR1/2019-02-15/'))
            rsps.add(rsps.PATCH, api_url('private-estate-batches/PR1/2019-02-17/'))
            rsps.add(rsps.PATCH, api_url('private-estate-batches/PR2/2019-02-15/'))
            rsps.add(rsps.GET, api_url('private-estate-batches/PR1/2019-02-15/credits/'), json={
                'count': 1,
                'results': [
                    {'id': 1,
                     'source': 'online',
                     'amount': 2500,
                     'prisoner_name': 'JOHN HALLS',
                     'prisoner_number': 'A1409AE',
                     'sender_name': 'Jilly Halls',
                     'billing_address': {'line1': 'Clive House 1', 'postcode': 'SW1H 9EX'}},
                ],
            })
            rsps.add(rsps.GET, api_url('private-estate-batches/PR1/2019-02-17/credits/'), json={
                'count': 1,
                'results': [
                    {'id': 2,
                     'source': 'online',
                     'amount': 1200,
                     'prisoner_name': 'JILLY HALLS',
                     'prisoner_number': 'A1401AE',
                     'sender_name': 'John Halls',
                     'billing_address': {'line1': 'Clive House 2', 'postcode': 'SW1H 9EX'}},
                ],
            })
            rsps.add(rsps.GET, api_url('private-estate-batches/PR2/2019-02-15/credits/'), json={
                'count': 2,
                'results': [
                    {'id': 3,
                     'source': 'online',
                     'amount': 700,
                     'prisoner_name': 'JOHN FREDSON',
                     'prisoner_number': 'A1000AA',
                     'sender_name': 'Mary [Φ] Fredson',  # note non-CP1252 character
                     'billing_address': {'line1': 'Clive House, 3', 'postcode': 'SW1H 9EX'}},  # note comma
                    {'id': 4,
                     'source': 'bank_transfer',
                     'amount': 100300,  # note > £1000
                     'prisoner_name': 'FRED JOHNSON',
                     'prisoner_number': 'A1000BB',
                     'sender_name': 'A "O\'Connell"',  # note quotes
                     'billing_address': None},
                ],
            })
            call_command('send_private_estate_emails', scheduled=True)

        self.assertEqual(mocked_send_csv.call_count, 2)
        pr1_call, pr2_call = mocked_send_csv.call_args_list
        if pr1_call[0][0]['cms_establishment_code'] == '20' and pr2_call[0][0]['cms_establishment_code'] == '10':
            pr1_call, pr2_call = pr2_call, pr1_call

        prison, date, batches, csv_contents, total, count = pr1_call[0]
        self.assertEqual(prison['cms_establishment_code'], '10')
        self.assertEqual(date, datetime.date(2019, 2, 15))
        self.assertEqual(len(batches), 2)
        self.assertEqual(total, 3700)
        self.assertEqual(count, 2)
        self.assertEqual(
            csv_contents.decode('cp1252').splitlines(),
            [
                'Establishment, Date, Prisoner Name, Prisoner Number, TransactionID, Value, Sender, Address',

                'Private 1, 15/02/19,JOHN HALLS, A1409AE, 100000001,'
                ' £25.00,Jilly Halls, Clive House 1 SW1H 9EX, ',

                'Private 1, 17/02/19,JILLY HALLS, A1401AE, 100000002,'
                ' £12.00,John Halls, Clive House 2 SW1H 9EX, ',

                ', , , ,Total , £37.00, , ',
            ]
        )

        prison, date, batches, csv_contents, total, count = pr2_call[0]
        self.assertEqual(prison['cms_establishment_code'], '20')
        self.assertEqual(date, datetime.date(2019, 2, 15))
        self.assertEqual(len(batches), 1)
        self.assertEqual(total, 101000)
        self.assertEqual(count, 2)
        self.assertEqual(
            csv_contents.decode('cp1252').splitlines(),
            [
                'Establishment, Date, Prisoner Name, Prisoner Number, TransactionID, Value, Sender, Address',

                'Private 2, 15/02/19,JOHN FREDSON, A1000AA, 100000003,'
                ' £7.00,Mary [] Fredson, Clive House  3 SW1H 9EX, ',

                'Private 2, 15/02/19,FRED JOHNSON, A1000BB, 100000004,'
                " £1003.00,A O'Connell, Bank Transfer 102 Petty France London SW1H 9AJ, ",

                ', , , ,Total , £1010.00, , ',
            ]
        )

    @mock.patch('bank_admin.management.commands.send_private_estate_emails.api_client.get_authenticated_api_session')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.timezone.now')
    @override_settings(GOVUK_NOTIFY_API_KEY=GOVUK_NOTIFY_TEST_API_KEY)
    def test_email_sent(self, mocked_now, mocked_api_session):
        mocked_now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=utc)
        with NotifyMock() as rsps:
            mock_bank_holidays(rsps)
            mock_api_session(mocked_api_session)
            rsps.add(rsps.POST, api_url('transactions/reconcile/'))
            rsps.add(rsps.GET, api_url('private-estate-batches/'), json={
                'count': 1,
                'results': [
                    {'date': '2019-02-15',
                     'prison': 'PR1',
                     'total_amount': 2501,
                     'bank_account': TEST_BANK_ACCOUNT,
                     'remittance_emails': ['private@mtp.local']},
                ]
            })
            rsps.add(rsps.GET, api_url('prisons/'), json={'count': len(TEST_PRISONS), 'results': TEST_PRISONS})
            rsps.add(rsps.PATCH, api_url('private-estate-batches/PR1/2019-02-15/'))
            rsps.add(rsps.GET, api_url('private-estate-batches/PR1/2019-02-15/credits/'), json={
                'count': 1,
                'results': [
                    {'id': 1,
                     'source': 'online',
                     'amount': 2501,
                     'prisoner_name': 'JOHN HALLS',
                     'prisoner_number': 'A1409AE',
                     'sender_name': 'Jilly Halls',
                     'billing_address': {'line1': 'Clive House 1', 'postcode': 'SW1H 9EX'}},
                ],
            })
            call_command('send_private_estate_emails', scheduled=True)
            send_email_request_data = rsps.send_email_request_data

        self.assertEqual(len(send_email_request_data), 1)
        send_email_request_data = send_email_request_data[0]
        send_email_request_data.pop('template_id')  # because template_id is random
        attachment = send_email_request_data['personalisation'].pop('attachment', {'file': 'AAAAAAA='})
        self.assertDictEqual(send_email_request_data, {
            'email_address': 'private@mtp.local',
            'personalisation': {
                'date': '15/02/2019',
                'prison_name': 'Private 1',
            },
        })
        # NB: file name should be 'payment_10_20190218_120000.csv.zip' but Notify doesn't support setting file names
        attachment_data = base64.b64decode(attachment['file'])
        attachment_data = io.BytesIO(attachment_data)
        with zipfile.ZipFile(attachment_data, 'r') as z:
            csv_contents = z.read('payment_10_20190218_120000.csv')
        self.assertIn('£25.01'.encode('cp1252'), csv_contents)
