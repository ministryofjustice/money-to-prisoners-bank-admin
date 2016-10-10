from contextlib import contextmanager
from datetime import date, datetime
import os
from unittest import mock, skip

from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.test import SimpleTestCase
from django.utils.timezone import utc
from mtp_common.auth.models import MojUser
from openpyxl import load_workbook

from . import (
    TEST_PRISONS, TEST_PRISONS_RESPONSE, NO_TRANSACTIONS, TEST_HOLIDAYS,
    get_test_transactions, get_test_credits
)
from .. import adi, adi_config
from ..exceptions import EmptyFileError, EarlyReconciliationError
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
        request = self.factory.get(
            reverse('bank_admin:download_adi_journal'),
            **kwargs
        )
        request.user = MojUser(
            1, '',
            {'first_name': 'John', 'last_name': 'Smith', 'username': 'jsmith'}
        )
        return request

    def _generate_test_adi_journal(self, mock_api_client, receipt_date=None):
        credits = get_test_credits(20)
        refundable_transactions = get_test_transactions(PaymentType.refund, 5)
        rejected_transactions = get_test_transactions(PaymentType.reject, 2)

        conn = mock_api_client.get_connection()
        conn.prisons.get.return_value = TEST_PRISONS_RESPONSE
        conn.credits.get.return_value = credits
        conn.transactions.get.side_effect = [
            refundable_transactions,
            rejected_transactions
        ]

        if receipt_date is None:
            receipt_date = date(2016, 9, 13)
        with mock.patch('bank_admin.utils.requests') as mock_requests:
            mock_requests.get().status_code = 200
            mock_requests.get().json.return_value = TEST_HOLIDAYS
            filename, exceldata = adi.generate_adi_journal(self.get_request(),
                                                           receipt_date)

        return filename, exceldata, (credits, refundable_transactions, rejected_transactions)

    def _get_expected_number_of_rows(self, credits, refundable_transactions, rejected_transactions):
        expected_credits = 0
        has_card_payments = False
        for credit in credits['results']:
            if credit['source'] == 'bank_transfer':
                expected_credits += 1
            else:
                # one lump sum for card payments
                if not has_card_payments:
                    has_card_payments = True
                    expected_credits += 1

        expected_debit_rows = (
            # valid credits
            expected_credits +
            # refunds
            len(refundable_transactions['results']) +
            # rejects
            len(rejected_transactions['results'])
        )

        expected_credit_rows = (
            # valid credits
            len(TEST_PRISONS) +
            # refunds
            1 +
            # rejects
            len(rejected_transactions['results'])
        )

        return expected_debit_rows, expected_credit_rows

    @skip('Enable to generate an example file for inspection')
    def test_adi_journal_generation(self, mock_api_client):
        filename, exceldata, _ = self._generate_test_adi_journal(mock_api_client)
        with open(filename, 'wb+') as f:
            f.write(exceldata)

    def test_adi_journal_debits_match_credits(self, mock_api_client):
        filename, exceldata, test_data = self._generate_test_adi_journal(mock_api_client)
        credits, refundable_transactions, rejected_transactions = test_data

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name('130916')
            row = adi_config.ADI_JOURNAL_START_ROW

            current_balance = 0
            while True:
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit and credit:
                    # final line
                    break
                elif debit:
                    current_balance -= debit
                elif credit:
                    current_balance += credit
                row += 1
            self.assertAlmostEqual(0, current_balance)

    def test_adi_journal_number_of_payment_rows_correct(self, mock_api_client):
        filename, exceldata, test_data = self._generate_test_adi_journal(mock_api_client)
        credits, refundable_transactions, rejected_transactions = test_data

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name('130916')
            row = adi_config.ADI_JOURNAL_START_ROW

            expected_debit_rows, expected_credit_rows = self._get_expected_number_of_rows(
                credits, refundable_transactions, rejected_transactions
            )

            file_debit_rows = 0
            file_credit_rows = 0
            while True:
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit and credit:
                    # final line
                    break
                elif debit:
                    file_debit_rows += 1
                elif credit:
                    file_credit_rows += 1
                row += 1

            credit = self.assertEqual(expected_credit_rows, file_credit_rows)
            credit = self.assertEqual(expected_debit_rows, file_debit_rows)

    def test_adi_journal_credit_sums_correct(self, mock_api_client):
        filename, exceldata, test_data = self._generate_test_adi_journal(mock_api_client)
        credits, refundable_transactions, rejected_transactions = test_data

        prison_totals = {}
        for prison in TEST_PRISONS:
            prison_totals[prison['general_ledger_code']] = float(sum(
                [c['amount'] for c in credits['results']
                    if 'prison' in c and c['prison'] == prison['nomis_id']]
            ))/100

        refund_total = float(sum([t['amount'] for t in refundable_transactions['results']]))/100

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name('130916')
            row = adi_config.ADI_JOURNAL_START_ROW

            refund_bu_code = adi_config.ADI_JOURNAL_FIELDS['business_unit']['value']['refund']['credit']
            reject_analysis = adi_config.ADI_JOURNAL_FIELDS['analysis']['value']['reject']['credit']

            while True:
                debit = get_cell_value(journal_ws, 'debit', row)
                credit = get_cell_value(journal_ws, 'credit', row)

                if debit and credit:
                    # final line
                    break
                elif credit:
                    bu_code = get_cell_value(journal_ws, 'business_unit', row)
                    analysis = get_cell_value(journal_ws, 'analysis', row)
                    if bu_code == refund_bu_code:
                        if analysis != reject_analysis:
                            self.assertAlmostEqual(credit, refund_total)
                    else:
                        self.assertAlmostEqual(credit, prison_totals[bu_code])
                row += 1

    def test_no_transactions_raises_error(self, mock_api_client):
        conn = mock_api_client.get_connection()
        conn.prisons.get.return_value = TEST_PRISONS_RESPONSE
        conn.credits.get.return_value = NO_TRANSACTIONS
        conn.transactions.get.return_value = NO_TRANSACTIONS

        with self.assertRaises(EmptyFileError):
            with mock.patch('bank_admin.utils.requests') as mock_requests:
                mock_requests.get().status_code = 200
                mock_requests.get().json.return_value = TEST_HOLIDAYS
                _, exceldata = adi.generate_adi_journal(self.get_request(),
                                                        date(2016, 9, 13))

    def test_adi_journal_reconciles_date(self, mock_api_client):
        _, _, _ = self._generate_test_adi_journal(
            mock_api_client, receipt_date=date(2016, 9, 13)
        )

        conn = mock_api_client.get_connection().transactions
        conn.reconcile.post.assert_called_with(
            {'received_at__gte': datetime(2016, 9, 12, 23, 0, tzinfo=utc).isoformat(),
             'received_at__lt': datetime(2016, 9, 13, 23, 0, tzinfo=utc).isoformat()}
        )

    def test_adi_journal_upload_range_set(self, mock_api_client):
        filename, exceldata, test_data = self._generate_test_adi_journal(mock_api_client)
        credits, refundable_transactions, rejected_transactions = test_data

        expected_debit_rows, expected_credit_rows = self._get_expected_number_of_rows(
            credits, refundable_transactions, rejected_transactions
        )
        expected_rows = expected_debit_rows + expected_credit_rows

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name('130916')

            self.assertEqual(
                wb.get_named_range('BNE_UPLOAD').destinations,
                [(
                    journal_ws,
                    '$B$%(start)s:$B$%(end)s' % {
                        'start': adi_config.ADI_JOURNAL_START_ROW,
                        'end': adi_config.ADI_JOURNAL_START_ROW + expected_rows - 1
                    }
                )]
            )

    def test_batch_name_includes_initials(self, mock_api_client):
        filename, exceldata, _ = self._generate_test_adi_journal(mock_api_client)

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name('130916')
            self.assertTrue('JS' in journal_ws[adi_config.ADI_BATCH_NAME_CELL].value)

    @mock.patch('mtp_bank_admin.apps.bank_admin.adi.date')
    def test_accounting_date_is_download_date(self, mock_date, mock_api_client):
        processing_date = date(2016, 8, 31)
        mock_date.today.return_value = processing_date
        receipt_date = date(2016, 8, 30)
        filename, exceldata, _ = self._generate_test_adi_journal(
            mock_api_client, receipt_date=receipt_date
        )

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(receipt_date.strftime('%d%m%y'))
            self.assertEqual(
                processing_date.strftime(adi_config.ADI_DATE_FORMAT),
                journal_ws[adi_config.ADI_DATE_CELL].value
            )

    @mock.patch('mtp_bank_admin.apps.bank_admin.adi.date')
    def test_accounting_date_is_set_back_across_month_boundary(self, mock_date, mock_api_client):
        processing_date = date(2016, 9, 1)
        mock_date.today.return_value = processing_date
        receipt_date = date(2016, 8, 31)
        filename, exceldata, _ = self._generate_test_adi_journal(
            mock_api_client, receipt_date=receipt_date
        )

        with temp_file(filename, exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(receipt_date.strftime('%d%m%y'))
            self.assertEqual(
                receipt_date.strftime(adi_config.ADI_DATE_FORMAT),
                journal_ws[adi_config.ADI_DATE_CELL].value
            )

    def test_early_reconciliation_raises_error(self, mock_api_client):
        with self.assertRaises(EarlyReconciliationError):
            self._generate_test_adi_journal(
                mock_api_client, receipt_date=date.today()
            )
