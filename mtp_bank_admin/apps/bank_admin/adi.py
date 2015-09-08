from datetime import datetime
from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from openpyxl import load_workbook, styles
from openpyxl.writer.excel import save_virtual_workbook
from moj_auth import api_client

from . import adi_config as config
from .types import PaymentType, RecordType
from .exceptions import EmptyFileError


class AdiJournal(object):

    STYLE_TYPES = {
        'fill': styles.PatternFill,
        'border': styles.Border,
        'font': styles.Font
    }

    def __init__(self, *args, **kwargs):
        self.wb = load_workbook(settings.ADI_TEMPLATE_FILEPATH)
        self.journal_ws = self.wb.get_sheet_by_name(config.ADI_JOURNAL_SHEET)

        self.current_row = config.ADI_JOURNAL_START_ROW

    def _next_row(self):
        self.current_row += 1

    def _set_field(self, field, value, style=None, extra_style=None):
        cell = '%s%s' % (config.ADI_JOURNAL_FIELDS[field]['column'],
                         self.current_row)
        self.journal_ws[cell] = value

        if not style:
            style = defaultdict(dict)
            style.update(config.ADI_JOURNAL_FIELDS[field]['style'])

        if extra_style:
            for key in extra_style:
                style[key].update(extra_style[key])

        for key in style:
            self.journal_ws[cell].__setattr__(
                key,
                self.STYLE_TYPES[key](**style[key])
            )
        return self.journal_ws[cell]

    def _add_column_sum(self, field):
        self._set_field(
            field,
            ('=SUM(%(column)s%(start)s:%(column)s%(end)s)'
                % {
                    'column': config.ADI_JOURNAL_FIELDS[field]['column'],
                    'start': config.ADI_JOURNAL_START_ROW,
                    'end': self.current_row - 1
                })
        )

    def _lookup(self, field, payment_type, record_type):
        try:
            value_dict = config.ADI_JOURNAL_FIELDS[field]['value']
            return value_dict[payment_type.name][record_type.name]
        except KeyError:
            # no static value
            return None

    def _add_payment_row(self, prison, amount, payment_type, record_type):
        self._set_field('business_unit', prison)
        if record_type == RecordType.debit:
            self._set_field('debit', float(amount))
        elif record_type == RecordType.credit:
            self._set_field('credit', float(amount))

        for field in config.ADI_JOURNAL_FIELDS:
            static_value = self._lookup(field, payment_type, record_type)
            if static_value:
                self._set_field(field, static_value)

        self._next_row()

    def _finish_journal(self):
        for field in config.ADI_JOURNAL_FIELDS:
            self._set_field(field, '', extra_style=config.ADI_FINAL_ROW_STYLE)

        self._add_column_sum('debit')
        self._add_column_sum('credit')

        bold = {'font': {'bold': True}}

        self._next_row()
        self._next_row()
        self._next_row()

        self._set_field('description', 'UPLOADED BY:', style=bold)

        self._next_row()
        self._next_row()
        self._next_row()

        self._set_field('description', 'CHECKED BY:', style=bold)

        self._next_row()
        self._next_row()
        self._next_row()

        self._set_field('description', 'POSTED BY:', style=bold)

    def add_payment(self, prison, amount, payment_type):
        self._add_payment_row(prison, amount, payment_type, RecordType.debit)
        self._add_payment_row(prison, amount, payment_type, RecordType.credit)

    def create_file(self):
        self._finish_journal()

        today = datetime.now()
        self.journal_ws[config.ADI_DATE_FIELD] = today.strftime('%d/%m/%Y')
        return (today.strftime(settings.OUTPUT_FILENAME),
                save_virtual_workbook(self.wb))


def generate_adi_file(request):
    journal = AdiJournal()

    client = api_client.get_connection(request)
    new_transactions = client.bank_admin.transactions.get(status='refunded,credited')

    if len(new_transactions) == 0:
        raise EmptyFileError()

    prison_payments = defaultdict(list)
    refunds = []
    for transaction in new_transactions:
        try:
            prison_payments[transaction['prison']].append(transaction)
        except KeyError:
            if transaction['refunded']:
                refunds.append(transaction)

    # do payments
    for prison, transaction_list in prison_payments.items():
        total_credit = sum([Decimal(t['amount']) for t in transaction_list
                            if t['credited']])
        journal.add_payment(prison, total_credit, PaymentType.payment)

    # do refunds
    total_debit = sum([Decimal(t['amount']) for t in refunds])
    journal.add_payment(None, total_debit, PaymentType.refund)

    return journal.create_file()
