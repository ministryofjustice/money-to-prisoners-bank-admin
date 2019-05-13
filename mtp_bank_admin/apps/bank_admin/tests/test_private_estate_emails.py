import datetime
import io
from unittest import mock
import zipfile

from django.core.management import call_command
from django.test import SimpleTestCase
from django.utils.timezone import utc
from mtp_common.auth.api_client import MoJOAuth2Session
from mtp_common.auth.test_utils import generate_tokens
import responses

from bank_admin.tests.utils import TEST_HOLIDAYS, TEST_PRISONS, TEST_BANK_ACCOUNT, api_url
from bank_admin.utils import BANK_HOLIDAY_URL


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
            rsps.add(rsps.GET, BANK_HOLIDAY_URL, json=TEST_HOLIDAYS)
            call_command('send_private_estate_emails', scheduled=True)

        mocked_timezone.now.return_value = datetime.datetime(2016, 12, 26, 12, tzinfo=utc)
        with responses.RequestsMock() as rsps:
            rsps.add(rsps.GET, BANK_HOLIDAY_URL, json=TEST_HOLIDAYS)
            call_command('send_private_estate_emails', scheduled=True)

    @mock.patch('bank_admin.management.commands.send_private_estate_emails.api_client.get_authenticated_api_session')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.timezone')
    def test_runs_on_weekday(self, mocked_timezone, mocked_api_session):
        mocked_api_session.side_effect = AssertionError('Must be called')

        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=utc)
        with responses.RequestsMock() as rsps:
            rsps.add(rsps.GET, BANK_HOLIDAY_URL, json=TEST_HOLIDAYS)
            with self.assertRaisesMessage(AssertionError, 'Must be called'):
                call_command('send_private_estate_emails', scheduled=True)

    @mock.patch('bank_admin.management.commands.send_private_estate_emails.send_csv')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.api_client.get_authenticated_api_session')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.timezone')
    def test_empty_batches(self, mocked_timezone, mocked_api_session, mocked_send_csv):
        mocked_timezone.now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=utc)
        mocked_send_csv.side_effect = AssertionError('Should not be called')
        with responses.RequestsMock() as rsps:
            rsps.add(rsps.GET, BANK_HOLIDAY_URL, json=TEST_HOLIDAYS)
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
            rsps.add(rsps.GET, BANK_HOLIDAY_URL, json=TEST_HOLIDAYS)
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
                     'billing_address': {'line1': 'Clive House 3', 'postcode': 'SW1H 9EX'}},
                    {'id': 4,
                     'source': 'bank_transfer',
                     'amount': 1300,
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
        self.assertEqual(total, 2000)
        self.assertEqual(count, 2)
        self.assertEqual(
            csv_contents.decode('cp1252').splitlines(),
            [
                'Establishment, Date, Prisoner Name, Prisoner Number, TransactionID, Value, Sender, Address',

                'Private 2, 15/02/19,JOHN FREDSON, A1000AA, 100000003,'
                ' £7.00,Mary [] Fredson, Clive House 3 SW1H 9EX, ',

                'Private 2, 15/02/19,FRED JOHNSON, A1000BB, 100000004,'
                ' £13.00,A O\'Connell, Bank Transfer 102 Petty France London SW1H 9AJ, ',

                ', , , ,Total , £20.00, , ',
            ]
        )

    @mock.patch('bank_admin.management.commands.send_private_estate_emails.AnymailMessage')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.api_client.get_authenticated_api_session')
    @mock.patch('bank_admin.management.commands.send_private_estate_emails.timezone.now')
    def test_email_sent(self, mocked_now, mocked_api_session, mocked_anymail_message):
        mocked_now.return_value = datetime.datetime(2019, 2, 18, 12, tzinfo=utc)
        with responses.RequestsMock() as rsps:
            rsps.add(rsps.GET, BANK_HOLIDAY_URL, json=TEST_HOLIDAYS)
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

        self.assertEqual(mocked_anymail_message.call_count, 1)
        email_kwargs = mocked_anymail_message.call_args_list[0][1]
        self.assertIn('Private 1', email_kwargs['subject'])
        self.assertIn('15/02/2019', email_kwargs['subject'])
        self.assertIn('private@mtp.local', email_kwargs['to'])

        attachment_args = mocked_anymail_message().attach.call_args_list[0][0]
        self.assertEqual(attachment_args[0], 'payment_10_20190218_120000.csv.zip')
        attachment = io.BytesIO(attachment_args[1])
        with zipfile.ZipFile(attachment, 'r') as z:
            csv_contents = z.read('payment_10_20190218_120000.csv')
        self.assertIn('£25.01'.encode('cp1252'), csv_contents)
