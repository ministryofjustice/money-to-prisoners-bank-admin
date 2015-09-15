import os
import random
from decimal import Decimal
from contextlib import contextmanager

from openpyxl import load_workbook
from django.test import SimpleTestCase
from unittest import mock, skip

from .. import adi, adi_config
from ..exceptions import EmptyFileError
from ..types import PaymentType

TEST_PRISONS = [
    {'nomis_id': '048', 'name': 'Big Prison'},
    {'nomis_id': '067', 'name': 'Dark Prison'},
    {'nomis_id': '054', 'name': 'Scary Prison'}
]

NO_TRANSACTIONS = {'count': 0, 'results': []}


@contextmanager
def temp_file(name, data):
    path = '/tmp/' + name
    with open(path, 'w+b') as f:
        f.write(data)
    yield path
    os.remove(path)


def get_adi_transactions(type, count=20):
    transactions = []
    for i in range(count):
        transaction = {'id': i}
        if type == PaymentType.refund:
            transaction['refunded'] = True
        else:
            transaction['credited'] = True
            if i % 2:
                transaction['prison'] = TEST_PRISONS[0]
            elif i % 3:
                transaction['prison'] = TEST_PRISONS[1]
            else:
                transaction['prison'] = TEST_PRISONS[2]

        transaction['amount'] = Decimal(random.randint(500, 5000))/100
        transactions.append(transaction)
    return {'count': count, 'results': transactions}


def get_cell_value(journal_ws, field, row):
    cell = '%s%s' % (
        adi_config.ADI_JOURNAL_FIELDS[field]['column'],
        row
    )
    return journal_ws[cell].value


@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class AdiPaymentFileGenerationTestCase(SimpleTestCase):

    @skip('Enable to generate an example file for inspection')
    def test_adi_payment_file_generation(self, mock_api_client):
        test_data = get_adi_transactions(PaymentType.payment)

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        filename, exceldata = adi.generate_adi_payment_file(None)

        with open(filename, 'wb+') as f:
            f.write(exceldata)

    def test_adi_payment_file_debits_match_credit(self, mock_api_client):
        test_data = get_adi_transactions(PaymentType.payment)

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        filename, exceldata = adi.generate_adi_payment_file(None)

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(adi_config.ADI_JOURNAL_SHEET)

            current_total_debit = 0
            for i in range(len(test_data['results']) + len(TEST_PRISONS)):
                row = i + adi_config.ADI_JOURNAL_START_ROW
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit:
                    current_total_debit += debit
                elif credit:
                    self.assertAlmostEqual(credit, current_total_debit)
                    current_total_debit = 0

    def test_adi_payment_file_number_of_payment_rows_correct(self, mock_api_client):
        test_data = get_adi_transactions(PaymentType.payment)

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        filename, exceldata = adi.generate_adi_payment_file(None)
        debit_rows = 0
        credit_rows = 0

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(adi_config.ADI_JOURNAL_SHEET)

            for i in range(len(test_data['results']) + len(TEST_PRISONS)):
                row = i + adi_config.ADI_JOURNAL_START_ROW
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit:
                    debit_rows += 1
                elif credit:
                    credit_rows += 1

        self.assertEqual(debit_rows, len(test_data['results']))
        self.assertEqual(credit_rows, len(TEST_PRISONS))

    def test_adi_payment_file_credit_sum_correct(self, mock_api_client):
        test_data = get_adi_transactions(PaymentType.payment)

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        filename, exceldata = adi.generate_adi_payment_file(None)

        prison_totals = {}
        for prison in TEST_PRISONS:
            prison_totals[prison['nomis_id']] = float(sum(
                [t['amount'] for t in test_data['results']
                    if 'prison' in t and t['prison'] == prison]
            ))
        credits_checked = 0

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(adi_config.ADI_JOURNAL_SHEET)

            for i in range(len(test_data['results']) + len(TEST_PRISONS)):
                row = i + adi_config.ADI_JOURNAL_START_ROW
                credit = get_cell_value(journal_ws, 'credit', row)

                if credit:
                    credits_checked += 1
                    prison = get_cell_value(journal_ws, 'business_unit', row)
                    self.assertAlmostEqual(credit, prison_totals[prison])

        self.assertEqual(credits_checked, len(TEST_PRISONS))


@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class AdiRefundFileGenerationTestCase(SimpleTestCase):

    @skip('Enable to generate an example file for inspection')
    def test_adi_refund_file_generation(self, mock_api_client):
        test_data = get_adi_transactions(PaymentType.refund)

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        filename, exceldata = adi.generate_adi_refund_file(None)

        with open(filename, 'wb+') as f:
            f.write(exceldata)

    def test_adi_refund_file_debits_match_credit(self, mock_api_client):
        test_data = get_adi_transactions(PaymentType.refund)

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        filename, exceldata = adi.generate_adi_refund_file(None)

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(adi_config.ADI_JOURNAL_SHEET)

            current_total_debit = 0
            for i in range(len(test_data['results']) + 1):
                row = i + adi_config.ADI_JOURNAL_START_ROW
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit:
                    current_total_debit += debit
                elif credit:
                    self.assertAlmostEqual(credit, current_total_debit)
                    current_total_debit = 0

    def test_adi_refund_file_number_of_payment_rows_correct(self, mock_api_client):
        test_data = get_adi_transactions(PaymentType.refund)

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        filename, exceldata = adi.generate_adi_refund_file(None)
        debit_rows = 0
        credit_rows = 0

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(adi_config.ADI_JOURNAL_SHEET)

            for i in range(len(test_data['results']) + 1):
                row = i + adi_config.ADI_JOURNAL_START_ROW
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit:
                    debit_rows += 1
                elif credit:
                    credit_rows += 1

        self.assertEqual(debit_rows, len(test_data['results']))
        self.assertEqual(credit_rows, 1)

    def test_adi_refund_file_credit_sum_correct(self, mock_api_client):
        test_data = get_adi_transactions(PaymentType.refund)

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        filename, exceldata = adi.generate_adi_refund_file(None)

        refund_total = float(sum([t['amount'] for t in test_data['results']]))
        credit_checked = False

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(adi_config.ADI_JOURNAL_SHEET)

            for i in range(len(test_data['results']) + 1):
                row = i + adi_config.ADI_JOURNAL_START_ROW
                credit = get_cell_value(journal_ws, 'credit', row)

                if credit:
                    self.assertAlmostEqual(credit, refund_total)
                    credit_checked = True

        self.assertTrue(credit_checked)


@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class NoTransactionsTestCase(SimpleTestCase):

    def test_generate_adi_payment_file_raises_error(self, mock_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = NO_TRANSACTIONS

        try:
            _, exceldata = adi.generate_adi_payment_file(None)
            self.fail('EmptyFileError expected')
        except EmptyFileError:
            self.assertFalse(conn.patch.called)

    def test_generate_adi_refund_file_raises_error(self, mock_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = NO_TRANSACTIONS

        try:
            _, exceldata = adi.generate_adi_refund_file(None)
            self.fail('EmptyFileError expected')
        except EmptyFileError:
            self.assertFalse(conn.patch.called)
