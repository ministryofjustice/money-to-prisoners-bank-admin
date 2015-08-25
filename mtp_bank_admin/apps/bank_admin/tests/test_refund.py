from unittest import mock
from copy import deepcopy

from django.test import SimpleTestCase

from .. import refund

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
        self.assertEqual('111111,22222222,DOE JO,25.68,A1234BC 22/03/66\r\n',
                         csvdata)

    def test_generate_missing_ref(self, mock_api_client):
        missing_ref = deepcopy(REFUND_TRANSACTION)
        missing_ref[0]['reference'] = ''

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = missing_ref

        _, csvdata = refund.generate_refund_file(None)

        conn.patch.assert_called_once_with([{'id': '3', 'refunded': True}])
        self.assertEqual('111111,22222222,DOE JO,25.68,\r\n',
                         csvdata)

    def test_generate_missing_account_details(self, mock_api_client):
        missing_account_details = deepcopy(REFUND_TRANSACTION)
        missing_account_details[0]['sender_account_number'] = ''

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = missing_account_details

        _, csvdata = refund.generate_refund_file(None)

        self.assertFalse(conn.patch.called)
        self.assertEqual('', csvdata)

    def test_generate_mixed(self, mock_api_client):
        missing_account_details = deepcopy(REFUND_TRANSACTION)
        missing_account_details[0]['id'] = '39'
        missing_account_details[0]['sender_account_number'] = ''

        missing_ref = deepcopy(REFUND_TRANSACTION)
        missing_ref[0]['id'] = '17'
        missing_ref[0]['reference'] = ''

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = (REFUND_TRANSACTION + missing_account_details +
                                 missing_ref)

        _, csvdata = refund.generate_refund_file(None)

        conn.patch.assert_called_once_with([
            {'id': '3', 'refunded': True},
            {'id': '17', 'refunded': True}
        ])
        self.assertEqual('111111,22222222,DOE JO,25.68,A1234BC 22/03/66\r\n' +
                         '111111,22222222,DOE JO,25.68,\r\n', csvdata)
