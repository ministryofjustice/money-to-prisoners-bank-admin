from unittest import mock
from copy import copy

from django.test import SimpleTestCase

from .. import refund

REFUND_TRANSACTION = [{
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
        conn = mock_api_client.get_connection().transactions
        conn.get.return_value = REFUND_TRANSACTION

        _, csvdata = refund.generate_refund_file(None)

        self.assertEqual('111111,22222222,DOE JO,25.68,A1234BC 22/03/66\r\n',
                         csvdata)

    def test_generate_missing_ref(self, mock_api_client):
        missing_ref = copy(REFUND_TRANSACTION)
        missing_ref[0]['reference'] = ''

        conn = mock_api_client.get_connection().transactions
        conn.get.return_value = missing_ref

        _, csvdata = refund.generate_refund_file(None)

        self.assertEqual('111111,22222222,DOE JO,25.68,\r\n',
                         csvdata)

    def test_missing_account_details(self, mock_api_client):
        missing_account_details = copy(REFUND_TRANSACTION)
        missing_account_details[0]['sender_account_number'] = ''

        conn = mock_api_client.get_connection().transactions
        conn.get.return_value = missing_account_details

        _, csvdata = refund.generate_refund_file(None)

        self.assertEqual('', csvdata)
