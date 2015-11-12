import mock

from django.test import SimpleTestCase
from bai2 import bai2
from bai2.constants import TypeCodes

from . import get_test_transactions, NO_TRANSACTIONS, AssertCalledWithBatchRequest
from .. import BAI2_STMT_LABEL
from ..statement import generate_bank_statement
from ..exceptions import EmptyFileError


@mock.patch('mtp_bank_admin.apps.bank_admin.statement.api_client')
@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class BankStatementGenerationTestCase(SimpleTestCase):

    def test_number_of_records_correct(self, mock_api_client, mock_stmt_api_client):
        test_data = get_test_transactions()

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        test_balance = 16600
        balance_conn = mock_stmt_api_client.get_connection().batches
        balance_conn.get.return_value = {
            'results': [{'closing_balance': test_balance}]
        }

        batch_conn = mock_api_client.get_connection().batches
        batch_conn.post.side_effect = AssertCalledWithBatchRequest(self, {
            'label': BAI2_STMT_LABEL,
            'transactions': [t['id'] for t in test_data['results']]
        })

        _, bai2_file = generate_bank_statement(None)
        self.assertTrue(batch_conn.post.side_effect.called)

        parsed_file = bai2.parse_from_string(bai2_file, check_integrity=True)

        self.assertEqual(len(parsed_file.children), 1)
        self.assertEqual(len(parsed_file.children[0].children), 1)
        self.assertEqual(
            len(parsed_file.children[0].children[0].children),
            len(test_data['results'])
        )

    def test_control_totals_correct(self, mock_api_client, mock_stmt_api_client):
        test_data = get_test_transactions()

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        test_balance = 16600
        balance_conn = mock_stmt_api_client.get_connection().batches
        balance_conn.get.return_value = {
            'results': [{'closing_balance': test_balance}]
        }

        batch_conn = mock_api_client.get_connection().batches
        batch_conn.post.side_effect = AssertCalledWithBatchRequest(self, {
            'label': BAI2_STMT_LABEL,
            'transactions': [t['id'] for t in test_data['results']]
        })

        _, bai2_file = generate_bank_statement(None)
        self.assertTrue(batch_conn.post.side_effect.called)

        parsed_file = bai2.parse_from_string(bai2_file, check_integrity=True)

        credit_num = 0
        credit_total = 0
        debit_num = 0
        debit_total = 0
        for transaction in test_data['results']:
            if transaction.get('refunded', False):
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
                amount = test_balance
            elif summary.type_code == TypeCodes['015'] or\
                    summary.type_code == TypeCodes['045']:
                amount = test_balance + credit_total - debit_total
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


@mock.patch('mtp_bank_admin.apps.bank_admin.statement.api_client')
@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class NoTransactionsTestCase(SimpleTestCase):

    def test_generate_bank_statement_raises_error(self, mock_api_client,
                                                  mock_stmt_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = NO_TRANSACTIONS

        try:
            generate_bank_statement(None)
            self.fail('EmptyFileError expected')
        except EmptyFileError:
            pass
