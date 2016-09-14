from datetime import date
import random
from unittest import mock

from bai2 import bai2
from bai2.constants import TypeCodes
from django.core.urlresolvers import reverse
from django.test import SimpleTestCase
from django.test.client import RequestFactory
from mtp_common.auth.models import MojUser

from . import (
    get_test_transactions, NO_TRANSACTIONS, ORIGINAL_REF, TEST_HOLIDAYS
)
from ..statement import generate_bank_statement


def get_test_transactions_for_stmt(count=20):
    transactions = get_test_transactions(count=int(count*0.75))
    for i in range(int(count*0.75), count):
        transaction = {'id': i, 'category': 'debit', 'source': 'administrative'}
        transaction['amount'] = random.randint(500, 5000)
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


def mock_balance(mock_api_client):
    balance_conn = mock_api_client.get_connection().balances
    balance_conn.get.return_value = {'count': 1,
                                     'results': [{'closing_balance': 20000}]}

    return balance_conn


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
            _, bai2_file = generate_bank_statement(self.get_request(),
                                                   receipt_date)
        return bai2.parse_from_string(bai2_file, check_integrity=True), test_data


@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class BankStatementGenerationTestCase(BankStatementTestCase):

    def test_number_of_records_correct(self, mock_api_client):
        parsed_file, test_data = self._generate_and_parse_bank_statement(mock_api_client)

        self.assertEqual(len(parsed_file.children), 1)
        self.assertEqual(len(parsed_file.children[0].children), 1)
        self.assertEqual(
            len(parsed_file.children[0].children[0].children),
            len(test_data['results'])
        )

    def test_control_totals_correct(self, mock_api_client):
        parsed_file, test_data = self._generate_and_parse_bank_statement(mock_api_client)

        credit_num = 0
        credit_total = 0
        debit_num = 0
        debit_total = 0
        for transaction in test_data['results']:
            if transaction['category'] == 'debit':
                debit_num += 1
                debit_total += transaction['amount']
            else:
                credit_num += 1
                credit_total += transaction['amount']

        expected_control_total = credit_total + debit_total
        account = parsed_file.children[0].children[0]
        for summary in account.header.summary_items:
            amount = None
            if summary.type_code == TypeCodes['010'] or\
                    summary.type_code == TypeCodes['040']:
                amount = 20000
            elif summary.type_code == TypeCodes['015'] or\
                    summary.type_code == TypeCodes['045']:
                amount = 20000 + (credit_total - debit_total)
            elif summary.type_code == TypeCodes['400']:
                amount = debit_total
            elif summary.type_code == TypeCodes['100']:
                amount = credit_total

            self.assertTrue(amount is not None)
            expected_control_total += amount
            self.assertEqual(summary.amount, amount)

        self.assertEqual(
            parsed_file.trailer.file_control_total,
            expected_control_total
        )

    def test_reference_overwritten_for_credit_and_not_debit(self, mock_api_client):
        parsed_file, test_data = self._generate_and_parse_bank_statement(mock_api_client)

        account = parsed_file.children[0].children[0]
        for record in account.children:
            if record.type_code == TypeCodes['399']:
                self.assertTrue(record.text != ORIGINAL_REF)
            else:
                self.assertTrue(record.text == ORIGINAL_REF)

    def test_reconciles_date(self, mock_api_client):
        _, _ = self._generate_and_parse_bank_statement(
            mock_api_client, receipt_date=date(2016, 9, 13)
        )

        conn = mock_api_client.get_connection().transactions
        conn.reconcile.post.assert_called_with(
            {'received_at__gte': date(2016, 9, 13).isoformat(),
             'received_at__lt': date(2016, 9, 14).isoformat()}
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
            _, bai2_file = generate_bank_statement(self.get_request(),
                                                   today)

        parsed_file = bai2.parse_from_string(bai2_file, check_integrity=True)
        account = parsed_file.children[0].children[0]
        self.assertEqual(len(account.children), 0)
