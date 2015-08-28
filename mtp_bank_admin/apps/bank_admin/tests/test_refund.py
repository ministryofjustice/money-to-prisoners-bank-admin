from unittest import mock
from copy import deepcopy

from django.test import SimpleTestCase
from django.conf import settings

from .. import refund
from ..exceptions import EmptyFileError

REFUND_TRANSACTION = [{
    'id': '3',
    'sender_account_number': '22222222',
    'prisoner_number': 'A1234BC',
    'reference': 'A1234BC 22/03/66',
    'sender_sort_code': '111111',
    'amount': 25.68,
    'sender_name': 'DOE JO',
    'prisoner_dob': '1966-03-22'
}]


@mock.patch('bank_admin.refund.api_client')
class RefundFileTestCase(SimpleTestCase):

    def test_generate(self, mock_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = REFUND_TRANSACTION

        _, csvdata = refund.generate_refund_file(None)

        conn.patch.assert_called_once_with([{'id': '3', 'refunded': True}])
        self.assertEqual('111111,22222222,DOE JO,25.68,%s\r\n' % settings.REFUND_REFERENCE,
                         csvdata)

    def test_generate_no_transactions(self, mock_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = []

        try:
            _, csvdata = refund.generate_refund_file(None)
            self.fail('EmptyFileError expected')
        except EmptyFileError:
            self.assertFalse(conn.patch.called)
