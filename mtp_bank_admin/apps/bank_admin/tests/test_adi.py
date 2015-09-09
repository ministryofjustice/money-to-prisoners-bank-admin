import os
import random
from decimal import Decimal
from contextlib import contextmanager

from openpyxl import load_workbook
from django.test import SimpleTestCase
from unittest import mock

from .. import adi, adi_config
from ..exceptions import EmptyFileError
from ..types import PaymentType

TEST_PRISONS = [
    {'nomis_id': '048', 'name': 'Big Prison'},
    {'nomis_id': '067', 'name': 'Dark Prison'},
    {'nomis_id': '054', 'name': 'Scary Prison'}
]


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
        transaction = {}
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
    return transactions


def get_cell_value(journal_ws, field, row):
    cell = '%s%s' % (
        adi_config.ADI_JOURNAL_FIELDS[field]['column'],
        row
    )
    return journal_ws[cell].value


class AdiFileGenerationTestCase(SimpleTestCase):

    @mock.patch('bank_admin.adi.api_client')
    def test_adi_payment_file_debits_match_credit(self, mock_api_client):
        test_data = get_adi_transactions(PaymentType.payment)

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = test_data

        filename, exceldata = adi.generate_adi_payment_file(None)

        prison_totals = {}
        for prison in TEST_PRISONS:
            prison_totals[prison['nomis_id']] = sum(
                [t['amount'] for t in test_data
                    if 'prison' in t and t['prison'] == prison]
            )

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(adi_config.ADI_JOURNAL_SHEET)

            current_total_debit = 0
            for i in range(len(test_data) + 3):
                row = i + adi_config.ADI_JOURNAL_START_ROW
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit:
                    current_total_debit += debit
                elif credit:
                    self.assertEqual(credit, current_total_debit)
                    current_total_debit = 0


@mock.patch('bank_admin.adi.api_client')
class NoTransactionsTestCase(SimpleTestCase):

    def test_generate_refund_file_raises_error(self, mock_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = []

        try:
            _, exceldata = adi.generate_adi_payment_file(None)
            self.fail('EmptyFileError expected')
        except EmptyFileError:
            self.assertFalse(conn.patch.called)
