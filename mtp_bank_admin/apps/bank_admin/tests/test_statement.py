from datetime import date, datetime
import random
from unittest import mock

from django.core.urlresolvers import reverse
from django.test import SimpleTestCase
from django.test.client import RequestFactory
from django.utils.timezone import utc
import mt940
from mtp_common.auth.models import MojUser

from . import (
    get_test_transactions, NO_TRANSACTIONS, ORIGINAL_REF, SENDER_NAME, TEST_HOLIDAYS,
    mock_balance, OPENING_BALANCE
)
from ..statement import generate_bank_statement


def get_test_transactions_for_stmt(count=20):
    transactions = get_test_transactions(count=int(count*0.75))
    for i in range(int(count*0.75), count):
        transaction = {'id': i, 'category': 'debit', 'source': 'administrative'}
        transaction['amount'] = random.randint(500, 5000)
        transaction['sender_name'] = SENDER_NAME
        transaction['reference'] = ORIGINAL_REF
        transactions['results'].append(transaction)
    transactions['count'] = count
    transactions['results'] = sorted(transactions['results'], key=lambda t: t['id'])
    return transactions


def mock_test_transactions(mock_api_client, count=20):
    test_data = get_test_transactions_for_stmt(count)
    conn = mock_api_client.get_connection().transactions
    conn.get.return_value = test_data

    return conn, test_data


class BankStatementTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def get_request(self, **kwargs):
        request = self.factory.get(
            reverse('bank_admin:download_bank_statement'),
            **kwargs
        )
        request.user = MojUser(
            1, '',
            {'first_name': 'John', 'last_name': 'Smith', 'username': 'jsmith'}
        )
        return request

    def _generate_and_parse_bank_statement(self, mock_api_client, receipt_date=None):
        _, test_data = mock_test_transactions(mock_api_client)
        mock_balance(mock_api_client)

        if receipt_date is None:
            receipt_date = date(2016, 9, 13)
        with mock.patch('bank_admin.utils.requests') as mock_requests:
            mock_requests.get().status_code = 200
            mock_requests.get().json.return_value = TEST_HOLIDAYS
            _, mt940_file = generate_bank_statement(self.get_request(), receipt_date)
        return mt940.parse(mt940_file), test_data


@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class BankStatementGenerationTestCase(BankStatementTestCase):

    def test_number_of_records_correct(self, mock_api_client):
        parsed_file, test_data = self._generate_and_parse_bank_statement(mock_api_client)

        self.assertEqual(len(parsed_file.transactions), len(test_data['results']))

    def test_closing_balance_correct(self, mock_api_client):
        parsed_file, test_data = self._generate_and_parse_bank_statement(mock_api_client)

        expected_credit_total = 0
        expected_debit_total = 0
        for transaction in test_data['results']:
            if transaction['category'] == 'debit':
                expected_debit_total += transaction['amount']
            else:
                expected_credit_total += transaction['amount']
        expected_closing_balance = OPENING_BALANCE + (expected_credit_total - expected_debit_total)

        credit_total = 0
        debit_total = 0
        for transaction in parsed_file.transactions:
            if transaction.data['status'] == 'C':
                credit_total += transaction.data['amount'].amount
            else:
                debit_total += transaction.data['amount'].amount

        self.assertEqual(credit_total*100, expected_credit_total)
        self.assertEqual(debit_total*100*-1, expected_debit_total)

        self.assertEqual(
            parsed_file.data['final_closing_balance'].amount.amount*100,
            expected_closing_balance
        )

    def test_reference_overwritten_for_credit_and_not_debit(self, mock_api_client):
        parsed_file, test_data = self._generate_and_parse_bank_statement(mock_api_client)

        for transaction in parsed_file.transactions:
            if transaction.data['status'] == 'C':
                self.assertNotEqual(
                    transaction.data['customer_reference'],
                    SENDER_NAME + ' ' + ORIGINAL_REF
                )
                self.assertNotEqual(transaction.data['customer_reference'], ORIGINAL_REF)
                self.assertNotEqual(transaction.data['customer_reference'], SENDER_NAME)
            else:
                self.assertEqual(
                    transaction.data['customer_reference'],
                    SENDER_NAME + ' ' + ORIGINAL_REF
                )

    def test_reconciles_date(self, mock_api_client):
        _, _ = self._generate_and_parse_bank_statement(
            mock_api_client, receipt_date=date(2016, 9, 13)
        )

        conn = mock_api_client.get_connection().transactions
        conn.reconcile.post.assert_called_with(
            {'received_at__gte': datetime(2016, 9, 13, 0, 0, tzinfo=utc).isoformat(),
             'received_at__lt': datetime(2016, 9, 14, 0, 0, tzinfo=utc).isoformat()}
        )


@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class NoTransactionsTestCase(BankStatementTestCase):

    def test_empty_statement_generated(self, mock_api_client):
        conn = mock_api_client.get_connection().transactions
        conn.get.return_value = NO_TRANSACTIONS
        mock_balance(mock_api_client)

        today = date(2016, 9, 13)
        with mock.patch('bank_admin.utils.requests') as mock_requests:
            mock_requests.get().status_code = 200
            mock_requests.get().json.return_value = TEST_HOLIDAYS
            _, mt940_file = generate_bank_statement(self.get_request(), today)
        parsed_file = mt940.parse(mt940_file)
        self.assertEqual(len(parsed_file.transactions), 1)
        self.assertEqual(parsed_file.transactions[0].data, {})
