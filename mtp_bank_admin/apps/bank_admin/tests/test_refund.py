from copy import deepcopy
from datetime import datetime, date
from unittest import mock

from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.test import SimpleTestCase
from django.utils.timezone import utc
from mtp_common.auth.models import MojUser

from . import NO_TRANSACTIONS, TEST_HOLIDAYS
from .. import refund
from ..exceptions import EmptyFileError

REFUND_TRANSACTIONS = [
    {
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
        }]
    },
    {
        'count': 3,
        'results': [{
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
    },
]


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


class RefundFileTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def get_request(self, **kwargs):
        request = self.factory.get(
            reverse('bank_admin:download_refund_file'),
            **kwargs
        )
        request.user = MojUser(
            1, '',
            {'first_name': 'John', 'last_name': 'Smith', 'username': 'jsmith'}
        )
        return request

    def _generate_refund_file(self, mock_api_client, mock_refund_api_client,
                              transactions=REFUND_TRANSACTIONS, refund_date=None):
        conn = mock_api_client.get_connection().transactions
        conn.get.side_effect = transactions

        refund_conn = mock_refund_api_client.get_connection().transactions

        if refund_date is None:
            refund_date = date(2016, 9, 13)
        with mock.patch('bank_admin.utils.requests') as mock_requests:
            mock_requests.get().status_code = 200
            mock_requests.get().json.return_value = TEST_HOLIDAYS
            _, csvdata = refund.generate_refund_file_for_date(
                self.get_request(), refund_date
            )

        return conn, refund_conn, csvdata


@mock.patch('mtp_bank_admin.apps.bank_admin.refund.api_client')
@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class ValidTransactionsTestCase(RefundFileTestCase):

    def test_generate_refund_file(self, mock_api_client, mock_refund_api_client):
        conn, refund_conn, csvdata = self._generate_refund_file(
            mock_api_client, mock_refund_api_client, refund_date=date(2016, 9, 13)
        )

        conn.reconcile.post.assert_called_with(
            {'received_at__gte': datetime(2016, 9, 13, 0, 0, tzinfo=utc).isoformat(),
             'received_at__lt': datetime(2016, 9, 14, 0, 0, tzinfo=utc).isoformat()}
        )
        refund_conn.patch.assert_called_once_with([
            {'id': '3', 'refunded': True},
            {'id': '4', 'refunded': True},
            {'id': '5', 'refunded': True}
        ])

        self.assertEqual(expected_output(), csvdata)

    def test_escaping_formulae_in_csv_export(self, mock_api_client, mock_refund_api_client):
        naughty_transactions = deepcopy(REFUND_TRANSACTIONS)
        naughty_transactions[0]['results'][0]['sender_name'] = (
            '=HYPERLINK("http://127.0.0.1/?value="&A1&A1, '
            '"Error: please click for further information")'
        )
        naughty_transactions[1]['results'][0]['sender_name'] = ('=1+2')

        conn, refund_conn, csvdata = self._generate_refund_file(
            mock_api_client, mock_refund_api_client, transactions=naughty_transactions
        )

        self.assertEqual(
            ('''111111,22222222,"'=HYPERLINK(""http://127.0.0.1/?value=""&A1&A1, '''
             '''""Error: please click for further information"")",25.68,%(ref_a)s\r\n'''
             '''999999,33333333,'=1+2,18.72,%(ref_b)s\r\n'''
             '''667788,00000005,Janet Buildingsoc,10.00,A1234567XY\r\n''')
            % {'ref_a': get_base_ref() + '00001',
               'ref_b': get_base_ref() + '00002'},
            csvdata)


@mock.patch('mtp_bank_admin.apps.bank_admin.refund.api_client')
@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class NoTransactionsTestCase(RefundFileTestCase):

    def test_generate_refund_file_raises_error(self, mock_api_client,
                                               mock_refund_api_client):
        conn = mock_api_client.get_connection().transactions
        conn.get.return_value = NO_TRANSACTIONS

        refund_conn = mock_refund_api_client.get_connection().transactions

        with self.assertRaises(EmptyFileError):
            with mock.patch('bank_admin.utils.requests') as mock_requests:
                mock_requests.get().status_code = 200
                mock_requests.get().json.return_value = TEST_HOLIDAYS
                _, csvdata = refund.generate_refund_file_for_date(
                    self.get_request(), date(2016, 9, 13)
                )
        self.assertFalse(refund_conn.patch.called)
