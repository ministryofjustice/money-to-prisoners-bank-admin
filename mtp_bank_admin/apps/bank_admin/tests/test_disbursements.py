from datetime import date
import logging
from unittest import mock, skip

from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from mtp_common.auth.models import MojUser
from mtp_common.test_utils import silence_logger
from openpyxl import load_workbook
import responses

from . import (
    NO_TRANSACTIONS, mock_list_prisons,
    get_test_disbursements, temp_file, api_url,
    mock_bank_holidays, ResponsesTestCase
)
from bank_admin import disbursements, disbursements_config
from bank_admin.exceptions import EmptyFileError


def get_cell_value(journal_ws, field, row):
    cell = '%s%s' % (
        disbursements_config.DISBURSEMENT_FIELDS[field]['column'],
        row
    )
    return journal_ws[cell].value


class DisbursementsFileGenerationTestCase(ResponsesTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def get_request(self, **kwargs):
        request = self.factory.get(
            reverse('bank_admin:download_disbursements'),
            **kwargs
        )
        request.user = MojUser(
            1, '',
            {'first_name': 'John', 'last_name': 'Smith', 'username': 'jsmith'}
        )
        request.session = mock.MagicMock()
        return request

    def _generate_test_disbursements_file(self, receipt_date=None):
        if receipt_date is None:
            receipt_date = date(2016, 9, 13)

        test_disbursements = get_test_disbursements(20)

        mock_list_prisons()
        mock_bank_holidays()
        responses.add(
            responses.GET,
            api_url('/disbursements/'),
            json=test_disbursements,
            status=200
        )
        responses.add(
            responses.POST,
            api_url('/disbursements/actions/send/'),
            status=200
        )

        with silence_logger(name='mtp', level=logging.WARNING):
            filename, exceldata = disbursements.generate_disbursements_journal(
                self.get_request(), receipt_date
            )

        return filename, exceldata, test_disbursements

    @responses.activate
    @skip('Enable to generate an example file for inspection')
    def test_disbursements_file_generation(self):
        filename, exceldata, _ = self._generate_test_disbursements_file()
        with open(filename, 'wb+') as f:
            f.write(exceldata)

    @responses.activate
    def test_disbursements_file_number_of_payment_rows_correct(self):
        filename, exceldata, test_data = self._generate_test_disbursements_file()

        with temp_file(exceldata) as f:
            wb = load_workbook(f)
            journal_ws = wb.get_sheet_by_name(
                disbursements_config.DISBURSEMENTS_JOURNAL_SHEET)

            row = disbursements_config.DISBURSEMENTS_JOURNAL_START_ROW
            disbursement_ref = 1
            lines = 0
            while True:
                disbursement_ref = get_cell_value(journal_ws, 'unique_payee_reference', row)
                if disbursement_ref:
                    lines += 1
                    row += 1
                else:
                    break

            self.assertEqual(lines, len(test_data['results']))

    @responses.activate
    def test_no_transactions_raises_error(self):
        mock_list_prisons()
        mock_bank_holidays()
        responses.add(
            responses.GET,
            api_url('/disbursements/'),
            json=NO_TRANSACTIONS
        )

        with self.assertRaises(EmptyFileError), silence_logger(name='mtp', level=logging.WARNING):
            _, exceldata = disbursements.generate_disbursements_journal(
                self.get_request(), date(2016, 9, 13))

    @responses.activate
    def test_disbursements_marked_as_sent(self):
        _, _, data = self._generate_test_disbursements_file(receipt_date=date(2016, 9, 13))

        self.assert_called_with(
            api_url('disbursements/actions/send/'), responses.POST,
            {'disbursement_ids': [d['id'] for d in data['results']]}
        )
