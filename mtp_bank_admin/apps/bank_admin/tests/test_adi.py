import os
from contextlib import contextmanager
from datetime import datetime

from openpyxl import load_workbook
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.test import SimpleTestCase
from unittest import mock, skip

from . import TEST_PRISONS, NO_TRANSACTIONS, get_test_transactions,\
    AssertCalledWithBatchRequest
from .. import adi, adi_config, ADI_JOURNAL_LABEL
from ..exceptions import EmptyFileError
from ..types import PaymentType


@contextmanager
def temp_file(name, data):
    path = '/tmp/' + name
    with open(path, 'w+b') as f:
        f.write(data)
    yield path
    os.remove(path)


def get_cell_value(journal_ws, field, row):
    cell = '%s%s' % (
        adi_config.ADI_JOURNAL_FIELDS[field]['column'],
        row
    )
    return journal_ws[cell].value


@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class AdiPaymentFileGenerationTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def get_request(self, **kwargs):
        return self.factory.get(
            reverse('bank_admin:download_adi_journal'),
            **kwargs
        )

    def _generate_test_adi_journal(self, mock_api_client):
        creditable_transactions = get_test_transactions(PaymentType.payment, 20)
        refundable_transactions = get_test_transactions(PaymentType.refund, 5)
        rejected_transactions = get_test_transactions(PaymentType.reject, 2)

        conn = mock_api_client.get_connection().transactions
        conn.get.side_effect = [
            creditable_transactions,
            refundable_transactions,
            rejected_transactions
        ]

        batch_conn = mock_api_client.get_connection().batches
        batch_conn.post.side_effect = AssertCalledWithBatchRequest(self, {
            'label': ADI_JOURNAL_LABEL,
            'transactions': [
                t['id'] for t in
                creditable_transactions['results'] +
                refundable_transactions['results'] +
                rejected_transactions['results']
            ]
        })

        filename, exceldata = adi.generate_adi_journal(self.get_request(),
                                                       datetime.now().date())

        self.assertTrue(batch_conn.post.side_effect.called)

        return filename, exceldata, (creditable_transactions, refundable_transactions, rejected_transactions)

    @skip('Enable to generate an example file for inspection')
    def test_adi_journal_generation(self, mock_api_client):
        creditable_transactions = get_test_transactions(PaymentType.payment, 20)
        refundable_transactions = get_test_transactions(PaymentType.refund, 5)
        rejected_transactions = get_test_transactions(PaymentType.reject, 2)

        conn = mock_api_client.get_connection().transactions
        conn.get.side_effect = [
            creditable_transactions,
            refundable_transactions,
            rejected_transactions
        ]

        filename, exceldata = adi.generate_adi_journal(self.get_request(),
                                                       datetime.now().date())

        with open(filename, 'wb+') as f:
            f.write(exceldata)

    def test_adi_journal_debits_match_credits(self, mock_api_client):
        filename, exceldata, test_data = self._generate_test_adi_journal(mock_api_client)
        creditable_transactions, refundable_transactions, rejected_transactions = test_data

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(adi_config.ADI_JOURNAL_SHEET)
            row = adi_config.ADI_JOURNAL_START_ROW

            current_total_debit = 0
            for _ in range(len(creditable_transactions['results']) + len(TEST_PRISONS)):
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit:
                    current_total_debit += debit
                elif credit:
                    self.assertAlmostEqual(credit, current_total_debit)
                    current_total_debit = 0
                row += 1

            current_total_debit = 0
            for _ in range(len(refundable_transactions['results']) + 1):
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit:
                    current_total_debit += debit
                elif credit:
                    self.assertAlmostEqual(credit, current_total_debit)
                    current_total_debit = 0
                row += 1

            for _ in range(len(rejected_transactions['results'])):
                debit = get_cell_value(journal_ws, 'debit', row)
                row += 1
                credit = get_cell_value(journal_ws, 'credit', row)
                row += 1
                self.assertAlmostEqual(credit, debit)

    def test_adi_journal_number_of_payment_rows_correct(self, mock_api_client):
        filename, exceldata, test_data = self._generate_test_adi_journal(mock_api_client)
        creditable_transactions, refundable_transactions, rejected_transactions = test_data

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(adi_config.ADI_JOURNAL_SHEET)
            row = adi_config.ADI_JOURNAL_START_ROW

            debit_rows = 0
            credit_rows = 0
            for _ in range(len(creditable_transactions['results']) + len(TEST_PRISONS)):
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit:
                    debit_rows += 1
                elif credit:
                    credit_rows += 1
                row += 1

            self.assertEqual(debit_rows, len(creditable_transactions['results']))
            self.assertEqual(credit_rows, len(TEST_PRISONS))

            debit_rows = 0
            credit_rows = 0
            for _ in range(len(refundable_transactions['results']) + 1):
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit:
                    debit_rows += 1
                elif credit:
                    credit_rows += 1
                row += 1

            self.assertEqual(debit_rows, len(refundable_transactions['results']))
            self.assertEqual(credit_rows, 1)

            debit_rows = 0
            credit_rows = 0
            for _ in range(len(rejected_transactions['results'])*2):
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit:
                    debit_rows += 1
                elif credit:
                    credit_rows += 1
                row += 1

            self.assertEqual(debit_rows, len(rejected_transactions['results']))
            self.assertEqual(credit_rows, len(rejected_transactions['results']))

    def test_adi_journal_credit_sums_correct(self, mock_api_client):
        filename, exceldata, test_data = self._generate_test_adi_journal(mock_api_client)
        creditable_transactions, refundable_transactions, rejected_transactions = test_data

        prison_totals = {}
        for prison in TEST_PRISONS:
            prison_totals[prison['general_ledger_code']] = float(sum(
                [t['amount'] for t in creditable_transactions['results']
                    if 'prison' in t and t['prison'] == prison]
            ))/100

        refund_total = float(sum([t['amount'] for t in refundable_transactions['results']]))/100

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(adi_config.ADI_JOURNAL_SHEET)
            row = adi_config.ADI_JOURNAL_START_ROW

            credits_checked = 0
            for _ in range(len(creditable_transactions['results']) + len(TEST_PRISONS)):
                credit = get_cell_value(journal_ws, 'credit', row)

                if credit:
                    credits_checked += 1
                    prison = get_cell_value(journal_ws, 'business_unit', row)
                    self.assertAlmostEqual(credit, prison_totals[prison])
                row += 1

            self.assertEqual(credits_checked, len(TEST_PRISONS))

            row += len(refundable_transactions['results'])
            credit = get_cell_value(journal_ws, 'credit', row)
            self.assertAlmostEqual(credit, refund_total)

    def test_no_transactions_raises_error(self, mock_api_client):
        conn = mock_api_client.get_connection().transactions
        conn.get.side_effect = [NO_TRANSACTIONS, NO_TRANSACTIONS, NO_TRANSACTIONS]

        try:
            _, exceldata = adi.generate_adi_journal(self.get_request(),
                                                    datetime.now().date())
            self.fail('EmptyFileError expected')
        except EmptyFileError:
            pass

    def test_adi_journal_reconciles_date(self, mock_api_client):
        _, _, _ = self._generate_test_adi_journal(mock_api_client)

        conn = mock_api_client.get_connection().transactions
        conn.reconcile.post.assert_called_with({'date': datetime.now().date().isoformat()})
