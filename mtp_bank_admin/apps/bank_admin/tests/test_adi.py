import random
from decimal import Decimal

from django.test import SimpleTestCase
from unittest import mock

from .. import adi
from ..exceptions import EmptyFileError


def get_adi_transactions(count=20):
    transactions = []
    for i in range(count):
        transaction = {}
        if i % 5 == 0:
            transaction['refunded'] = True
        else:
            transaction['credited'] = True
            if i % 2:
                transaction['prison'] = '048'
            elif i % 3:
                transaction['prison'] = '067'
            else:
                transaction['prison'] = '054'

        transaction['amount'] = Decimal(random.randint(500, 5000))/100
        transactions.append(transaction)
    return transactions


class AdiFileGenerationTestCase(SimpleTestCase):

    @mock.patch('bank_admin.adi.api_client')
    def test_adi_file_generation(self, mock_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = get_adi_transactions()

        filename, exceldata = adi.generate_adi_file(None)

        # with open(filename, 'wb') as f:
        #     f.write(exceldata)


@mock.patch('bank_admin.adi.api_client')
class NoTransactionsTestCase(SimpleTestCase):

    def test_generate_refund_file_raises_error(self, mock_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = []

        try:
            _, exceldata = adi.generate_adi_file(None)
            self.fail('EmptyFileError expected')
        except EmptyFileError:
            self.assertFalse(conn.patch.called)
