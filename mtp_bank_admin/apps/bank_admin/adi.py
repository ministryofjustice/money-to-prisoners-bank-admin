from datetime import datetime
from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from openpyxl import load_workbook, styles
from openpyxl.writer.excel import save_virtual_workbook

from . import ADI_PAYMENT_LABEL, ADI_REFUND_LABEL
from . import adi_config as config
from .types import PaymentType, RecordType
from .exceptions import EmptyFileError
from .utils import retrieve_all_transactions, create_batch_record,\
    get_transaction_uid


class AdiJournal(object):

    STYLE_TYPES = {
        'fill': styles.PatternFill,
        'border': styles.Border,
        'font': styles.Font,
        'alignment': styles.Alignment
    }

    def __init__(self, payment_type, *args, **kwargs):
        self.wb = load_workbook(settings.ADI_TEMPLATE_FILEPATH)
        self.journal_ws = self.wb.get_sheet_by_name(config.ADI_JOURNAL_SHEET)

        self.current_row = config.ADI_JOURNAL_START_ROW
        self.payment_type = payment_type

    def _next_row(self, increment=1):
        self.current_row += increment

    def _set_field(self, field, value, style=None, extra_style=None):
        cell = '%s%s' % (config.ADI_JOURNAL_FIELDS[field]['column'],
                         self.current_row)
        self.journal_ws[cell] = value

        computed_style = defaultdict(dict)
        if style:
            computed_style.update(style)
        else:
            computed_style.update(config.ADI_JOURNAL_FIELDS[field]['style'])

        if extra_style:
            for key in extra_style:
                computed_style[key].update(extra_style[key])

        for key in computed_style:
            setattr(
                self.journal_ws[cell],
                key,
                self.STYLE_TYPES[key](**computed_style[key])
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

    def _lookup(self, field, record_type, context={}):
        try:
            value_dict = config.ADI_JOURNAL_FIELDS[field]['value']
            value = value_dict[self.payment_type.name][record_type.name]
            if value:
                return value.format(**context)
        except KeyError:
            pass  # no static value
        return None

    def _finish_journal(self):
        for field in config.ADI_JOURNAL_FIELDS:
            self._set_field(field, '', extra_style=config.ADI_FINAL_ROW_STYLE)

        self._add_column_sum('debit')
        self._add_column_sum('credit')

    def add_payment_row(self, amount, record_type, **kwargs):
        for field in config.ADI_JOURNAL_FIELDS:
            static_value = self._lookup(field, record_type, context=kwargs)
            self._set_field(field, static_value)

        if record_type == RecordType.debit:
            self._set_field('debit', float(amount))
        elif record_type == RecordType.credit:
            self._set_field('credit', float(amount))

        self._next_row()

    def create_file(self):
        self._finish_journal()

        if self.payment_type == PaymentType.payment:
            filename = settings.ADI_PAYMENT_OUTPUT_FILENAME
        elif self.payment_type == PaymentType.refund:
            filename = settings.ADI_REFUND_OUTPUT_FILENAME

        today = datetime.now()
        return (today.strftime(filename),
                save_virtual_workbook(self.wb))


def generate_adi_payment_file(request, receipt_date=None):
    journal = AdiJournal(PaymentType.payment)

    new_transactions = retrieve_all_transactions(
        request,
        'credited',
        receipt_date=receipt_date
    )

    if len(new_transactions) == 0:
        raise EmptyFileError()

    today = datetime.now().strftime('%d/%m/%Y')
    prison_payments = defaultdict(list)
    for transaction in new_transactions:
        prison_payments[transaction['prison']['nomis_id']].append(transaction)

    # do payments
    reconciled_transactions = []
    for _, transaction_list in prison_payments.items():
        credit_total = 0
        for transaction in transaction_list:
            credit_amount = Decimal(transaction['amount'])/100
            credit_total += credit_amount
            journal.add_payment_row(
                credit_amount, RecordType.debit,
                unique_id=get_transaction_uid(transaction)
            )
            reconciled_transactions.append(transaction['id'])
        journal.add_payment_row(
            credit_total, RecordType.credit,
            prison_ledger_code=transaction_list[0]['prison']['general_ledger_code'],
            prison_name=transaction_list[0]['prison']['name'],
            date=today
        )

    created_journal = journal.create_file()
    create_batch_record(request, ADI_PAYMENT_LABEL, reconciled_transactions)

    return created_journal


def generate_adi_refund_file(request, receipt_date=None):
    journal = AdiJournal(PaymentType.refund)

    refunds = retrieve_all_transactions(
        request,
        'refunded',
        receipt_date=receipt_date
    )

    if len(refunds) == 0:
        raise EmptyFileError()

    today = datetime.now().strftime('%d/%m/%Y')

    # do refunds
    reconciled_transactions = []
    refund_total = 0
    for refund in refunds:
        refund_amount = Decimal(refund['amount'])/100
        refund_total += refund_amount
        journal.add_payment_row(
            refund_amount, RecordType.debit,
            unique_id=get_transaction_uid(refund)
        )
        reconciled_transactions.append(refund['id'])
    journal.add_payment_row(refund_total, RecordType.credit, date=today)

    created_journal = journal.create_file()
    create_batch_record(request, ADI_REFUND_LABEL, reconciled_transactions)

    return created_journal
