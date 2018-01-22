from datetime import date, datetime
import random
from unittest import mock

from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.utils.timezone import utc
import mt940
from mtp_common.auth.api_client import get_api_session
from mtp_common.auth.models import MojUser
import responses

from .utils import (
    get_test_transactions, NO_TRANSACTIONS, ORIGINAL_REF, SENDER_NAME,
    mock_balance, OPENING_BALANCE, api_url, mock_bank_holidays, BankAdminTestCase
)
from bank_admin.statement import generate_bank_statement


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


def mock_test_transactions(count=20):
    test_data = get_test_transactions_for_stmt(count)
    responses.add(
        responses.GET,
        api_url('/transactions/'),
        json=test_data
    )

    return test_data


class BankStatementTestCase(BankAdminTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def get_api_session(self, **kwargs):
        request = self.factory.get(
            reverse('bank_admin:download_bank_statement'),
            **kwargs
        )
        request.user = MojUser(
            1, '',
            {'first_name': 'John', 'last_name': 'Smith', 'username': 'jsmith'}
        )
        request.session = mock.MagicMock()
        return get_api_session(request)

    def _generate_and_parse_bank_statement(self, receipt_date=None):
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        test_data = mock_test_transactions()
        mock_balance()
        mock_bank_holidays()

        if receipt_date is None:
            receipt_date = date(2016, 9, 13)
        mt940_file = generate_bank_statement(self.get_api_session(), receipt_date)
        return mt940.parse(mt940_file), test_data


class BankStatementGenerationTestCase(BankStatementTestCase):

    @responses.activate
    def test_number_of_records_correct(self):
        parsed_file, test_data = self._generate_and_parse_bank_statement()

        self.assertEqual(len(parsed_file.transactions), len(test_data['results']))

    @responses.activate
    def test_closing_balance_correct(self):
        parsed_file, test_data = self._generate_and_parse_bank_statement()

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

    @responses.activate
    def test_reference_overwritten_for_credit_and_not_debit(self):
        parsed_file, test_data = self._generate_and_parse_bank_statement()

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

    @responses.activate
    def test_reconciles_date(self):
        _, _ = self._generate_and_parse_bank_statement(receipt_date=date(2016, 9, 13))

        self.assert_called_with(
            api_url('/transactions/reconcile/'), responses.POST,
            {
                'received_at__gte': datetime(2016, 9, 13, 0, 0, tzinfo=utc).isoformat(),
                'received_at__lt': datetime(2016, 9, 14, 0, 0, tzinfo=utc).isoformat()
            }
        )


class NoTransactionsTestCase(BankStatementTestCase):

    @responses.activate
    def test_empty_statement_generated(self):
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        responses.add(
            responses.GET,
            api_url('/transactions/'),
            json=NO_TRANSACTIONS
        )
        mock_balance()
        mock_bank_holidays()

        today = date(2016, 9, 13)
        mt940_file = generate_bank_statement(self.get_api_session(), today)
        parsed_file = mt940.parse(mt940_file)
        self.assertEqual(len(parsed_file.transactions), 1)
        self.assertEqual(parsed_file.transactions[0].data, {})
