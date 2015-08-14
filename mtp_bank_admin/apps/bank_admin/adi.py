from datetime import datetime
from collections import defaultdict
from functools import reduce
from decimal import Decimal

from openpyxl import load_workbook
from openpyxl.writer.excel import save_virtual_workbook
from moj_auth import api_client

from . import settings
from .exceptions import UnrecognisedFieldError
from .types import PaymentType, RecordType


class AdiJournal(object):

    def __init__(self, *args, **kwargs):
        self.wb = load_workbook(settings.ADI_TEMPLATE_FILEPATH)
        self.journal_ws = self.wb.get_sheet_by_name(settings.JOURNAL_SHEET)
        self.lookup_ws = self.wb.get_sheet_by_name(settings.LOOKUP_SHEET)

        self.current_row = settings.JOURNAL_START_ROW

    def _next_row(self):
        self.current_row += 1

    def _set_field(self, field, value):
        cell = '%s%s' % (settings.JOURNAL_COLUMNS[field], self.current_row)
        self.journal_ws[cell] = value

    def _lookup(self, field, payment_type, record_type):
        try:
            return settings.COLUMN_VALUES[field][payment_type.name][record_type.name]
        except KeyError:
            raise UnrecognisedFieldError(field)

    def _add_payment_row(self, prison, amount, payment_type, record_type):
        self._set_field('prison', prison)
        if payment_type == record_type.debit:
            self._set_field('debit', amount)
        elif payment_type == record_type.credit:
            self._set_field('credit', amount)

        for field in settings.JOURNAL_COLUMNS:
            self.set_field(
                field,
                self._lookup(field, payment_type, record_type)
            )
        self._next_row()

    def add_payment(self, prison, amount, payment_type):
        self._add_payment_row(self, prison, amount, payment_type,
                              RecordType.credit)
        self._add_payment_row(self, prison, amount, payment_type,
                              RecordType.debit)

    def create_file(self):
        self.journal_ws[self.DATE_FIELD] = datetime.now().strftime('%d/%m/%Y')
        return (datetime.now().strftime(settings.OUTPUT_FILENAME),
                save_virtual_workbook(self.wb))


def generate_file(request):
    journal = AdiJournal()

    client = api_client.get_connection(request)
    new_transactions = client.bank_admin().transactions.get(status='refunded,credited')

    prison_transactions = reduce(
        lambda d, t: d[t['prison']].append(t),
        new_transactions,
        defaultdict(list)
    )

    for prison, transaction_list in prison_transactions.items():
        # do payments
        total_credit = sum([Decimal(t['amount']) for t in transaction_list
                            if t['credited']])
        journal.add_payment(prison, total_credit, PaymentType.payment)

        # do refunds
        total_debit = sum([Decimal(t['amount']) for t in transaction_list
                           if t['refunded']])
        journal.add_payment(prison, total_debit, PaymentType.refund)

    return journal.create_file()
