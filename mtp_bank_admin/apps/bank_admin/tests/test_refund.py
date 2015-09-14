from unittest import mock

from django.test import SimpleTestCase
from django.conf import settings

from .. import refund
from ..exceptions import EmptyFileError

REFUND_TRANSACTIONS = [
    {
        'count': 2,
        'results': [{
            'id': '3',
            'amount': 25.68,
            'sender_account_number': '22222222',
            'sender_sort_code': '111111',
            'sender_name': 'John Doe',
            'reference': 'for birthday',
            'credited': False,
            'refunded': False
        }]
    },
    {
        'count': 2,
        'results': [{
            'id': '4',
            'amount': 18.72,
            'sender_account_number': '33333333',
            'sender_sort_code': '999999',
            'sender_name': 'Joe Bloggs',
            'reference': 'A1234 22/03/66',
            'credited': False,
            'refunded': False
        }]
    },
]

NO_TRANSACTIONS = {'count': 0, 'results': []}


@mock.patch('bank_admin.refund.api_client')
@mock.patch('bank_admin.utils.api_client')
class ValidTransactionsTestCase(SimpleTestCase):

    def test_generate_refund_file(self, mock_api_client, mock_refund_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.side_effect = REFUND_TRANSACTIONS

        refund_conn = mock_refund_api_client.get_connection().bank_admin.transactions

        _, csvdata = refund.generate_refund_file(None)

        refund_conn.patch.assert_called_once_with([
            {'id': '3', 'refunded': True}, {'id': '4', 'refunded': True}
        ])
        self.assertEqual(
            ('111111,22222222,John Doe,25.68,%(ref)s\r\n' +
             '999999,33333333,Joe Bloggs,18.72,%(ref)s\r\n')
            % {'ref': settings.REFUND_REFERENCE},
            csvdata)


@mock.patch('bank_admin.refund.api_client')
@mock.patch('bank_admin.utils.api_client')
class NoTransactionsTestCase(SimpleTestCase):

    def test_generate_refund_file_raises_error(self, mock_api_client,
                                               mock_refund_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = NO_TRANSACTIONS

        try:
            _, csvdata = refund.generate_refund_file(None)
            self.fail('EmptyFileError expected')
        except EmptyFileError:
            self.assertFalse(conn.patch.called)
