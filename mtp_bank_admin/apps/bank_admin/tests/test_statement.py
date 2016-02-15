from datetime import datetime
import random
from unittest import mock

from django.test import SimpleTestCase
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from bai2 import bai2
from bai2.constants import TypeCodes

from . import (
    get_test_transactions, NO_TRANSACTIONS, ORIGINAL_REF,
    AssertCalledWithBatchRequest
)
from .. import BAI2_STMT_LABEL
from ..statement import generate_bank_statement


def get_test_transactions_for_stmt(count=20):
    transactions = get_test_transactions(count=int(count*0.75))
    for i in range(int(count*0.75), count):
        transaction = {'id': i, 'category': 'debit', 'source': 'administrative'}
        transaction['amount'] = random.randint(500, 5000)
        transaction['reference'] = ORIGINAL_REF
        transactions['results'].append(transaction)
    transactions['count'] = count
    return transactions


def mock_test_transactions(mock_api_client):
    test_data = get_test_transactions_for_stmt()
    conn = mock_api_client.get_connection().bank_admin.transactions
    conn.get.return_value = test_data

    return conn, test_data


def mock_balance(mock_api_client):
    balance_conn = mock_api_client.get_connection().balances
    balance_conn.get.return_value = {'count': 1,
                                     'results': [{'closing_balance': 20000}]}

    return balance_conn


def mock_batch(test_case, mock_api_client, test_data):
    batch_conn = mock_api_client.get_connection().batches
    batch_conn.post.side_effect = AssertCalledWithBatchRequest(test_case, {
        'label': BAI2_STMT_LABEL,
        'transactions': [t['id'] for t in test_data['results']]
    })

    return batch_conn


@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class BankStatementGenerationTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def get_request(self, **kwargs):
        return self.factory.get(
            reverse('bank_admin:download_bank_statement'),
            **kwargs
        )

    def test_number_of_records_correct(self, mock_api_client):
        _, test_data = mock_test_transactions(mock_api_client)
        mock_balance(mock_api_client)
        batch_conn = mock_batch(self, mock_api_client, test_data)

        _, bai2_file = generate_bank_statement(self.get_request(),
                                               datetime.now().date())
        self.assertTrue(batch_conn.post.side_effect.called)

        parsed_file = bai2.parse_from_string(bai2_file, check_integrity=True)

        self.assertEqual(len(parsed_file.children), 1)
        self.assertEqual(len(parsed_file.children[0].children), 1)
        self.assertEqual(
            len(parsed_file.children[0].children[0].children),
            len(test_data['results'])
        )

    def test_control_totals_correct(self, mock_api_client):
        _, test_data = mock_test_transactions(mock_api_client)
        mock_balance(mock_api_client)
        batch_conn = mock_batch(self, mock_api_client, test_data)

        _, bai2_file = generate_bank_statement(self.get_request(),
                                               datetime.now().date())
        self.assertTrue(batch_conn.post.side_effect.called)

        parsed_file = bai2.parse_from_string(bai2_file, check_integrity=True)

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
        _, test_data = mock_test_transactions(mock_api_client)
        mock_balance(mock_api_client)

        today = datetime.now().date()
        _, bai2_file = generate_bank_statement(self.get_request(),
                                               today)

        parsed_file = bai2.parse_from_string(bai2_file, check_integrity=True)

        account = parsed_file.children[0].children[0]
        for record in account.children:
            if record.type_code == TypeCodes['399']:
                self.assertTrue(record.text != ORIGINAL_REF)
            else:
                self.assertTrue(record.text == ORIGINAL_REF)

    def test_reconciles_date(self, mock_api_client):
        conn, test_data = mock_test_transactions(mock_api_client)

        today = datetime.now().date()
        _, bai2_file = generate_bank_statement(self.get_request(),
                                               today)

        conn.reconcile.post.assert_called_with({'date': today.isoformat()})

    def test_posts_new_balance(self, mock_api_client):
        _, test_data = mock_test_transactions(mock_api_client)
        balance_conn = mock_balance(mock_api_client)

        today = datetime.now().date()
        _, bai2_file = generate_bank_statement(self.get_request(),
                                               today)

        closing_balance = 20000
        for transaction in test_data['results']:
            if transaction['category'] == 'debit':
                closing_balance -= transaction['amount']
            else:
                closing_balance += transaction['amount']

        balance_conn.post.assert_called_with(
            {'date': today.isoformat(), 'closing_balance': closing_balance})


@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class NoTransactionsTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def get_request(self, **kwargs):
        return self.factory.get(
            reverse('bank_admin:download_bank_statement'),
            **kwargs
        )

    def test_empty_statement_generated(self, mock_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = NO_TRANSACTIONS
        mock_balance(mock_api_client)

        today = datetime.now().date()
        _, bai2_file = generate_bank_statement(self.get_request(),
                                               today)

        parsed_file = bai2.parse_from_string(bai2_file, check_integrity=True)
        account = parsed_file.children[0].children[0]
        self.assertEqual(len(account.children), 0)
