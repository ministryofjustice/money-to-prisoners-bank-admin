from collections import defaultdict
from datetime import date
from decimal import Decimal
import logging

from django.conf import settings

from . import ADI_JOURNAL_LABEL
from . import adi_config as config
from .types import PaymentType, RecordType
from .exceptions import EmptyFileError
from .utils import (
    Journal, retrieve_all_transactions, retrieve_all_valid_credits,
    reconcile_for_date, retrieve_prisons, get_full_narrative
)

logger = logging.getLogger('mtp')


class AdiJournal(Journal):
    def _add_column_sum(self, field):
        self.set_field(
            field,
            ('=SUM(%(column)s%(start)s:%(column)s%(end)s)'
                % {
                    'column': self.fields[field]['column'],
                    'start': self.start_row,
                    'end': self.current_row - 1
                }),
            extra_style=config.ADI_FINAL_ROW_STYLE
        )
        cell = self.get_cell(field)
        self.journal_ws[cell].number_format = '£#,##0.00_-'

    def lookup(self, field, payment_type, record_type, context={}):
        try:
            value_dict = self.fields[field]['value']
            value = value_dict[payment_type.name][record_type.name]
            if value:
                return value.format(**context)
        except KeyError:
            pass  # no static value
        return None

    def finish_journal(self, receipt_date, user):
        for field in self.fields:
            self.set_field(field, '', extra_style=config.ADI_FINAL_ROW_STYLE)
        bold = {'font': {'name': 'Arial', 'bold': True},
                'alignment': {'horizontal': 'left'}}

        self.set_field('upload', 'Totals:', extra_style=dict(config.ADI_FINAL_ROW_STYLE, **bold))
        self._add_column_sum('debit')
        self._add_column_sum('credit')

        self.journal_ws.title = receipt_date.strftime('%d%m%y')
        self.wb.create_named_range(
            'BNE_UPLOAD',
            self.journal_ws,
            '$B$%(start)s:$B$%(end)s' % {
                'start': self.start_row,
                'end': self.current_row - 1,
            }
        )

        self.next_row(increment=2)
        self.set_field('description', 'Uploaded by:', style=config._light_blue_style, extra_style=bold)

        self.next_row(increment=2)
        self.set_field('description', 'Checked by:', style=config._light_blue_style, extra_style=bold)

        self.next_row(increment=2)
        self.set_field('description', 'Posted by:', style=config._light_blue_style, extra_style=bold)

        batch_date = date.today().strftime(config.ADI_BATCH_DATE_FORMAT)
        self.journal_ws[config.ADI_BATCH_NAME_CELL] = config.ADI_BATCH_NAME_FORMAT % {
            'date': batch_date,
            'initials': user.get_initials() or '<initials>',
        }
        accounting_date = date.today()
        if accounting_date.month != receipt_date.month:
            accounting_date = receipt_date
        self.journal_ws[config.ADI_DATE_CELL] = accounting_date.strftime(config.ADI_DATE_FORMAT)

    def add_payment_row(self, amount, payment_type, record_type, **kwargs):
        for field in self.fields:
            static_value = self.lookup(field, payment_type, record_type, context=kwargs)
            self.set_field(field, static_value)

        if record_type == RecordType.debit:
            self.set_field('debit', float(amount))
        elif record_type == RecordType.credit:
            self.set_field('credit', float(amount))

        self.next_row()


def generate_adi_journal(request, receipt_date):
    start_date, end_date = reconcile_for_date(request, receipt_date)

    credits = retrieve_all_valid_credits(
        request,
        received_at__gte=start_date,
        received_at__lt=end_date
    )
    refundable_transactions = retrieve_all_transactions(
        request,
        status='refundable',
        received_at__gte=start_date,
        received_at__lt=end_date
    )
    rejected_transactions = retrieve_all_transactions(
        request,
        status='unidentified',
        received_at__gte=start_date,
        received_at__lt=end_date
    )

    if (len(credits) == 0 and
            len(rejected_transactions) == 0 and
            len(refundable_transactions) == 0):
        raise EmptyFileError()

    journal_date = receipt_date.strftime('%d/%m/%Y')
    journal = AdiJournal(
        settings.ADI_TEMPLATE_FILEPATH,
        config.ADI_JOURNAL_SHEET,
        config.ADI_JOURNAL_START_ROW,
        config.ADI_JOURNAL_FIELDS
    )

    prisons = retrieve_prisons(request)
    bu_lookup = {prison['general_ledger_code']: nomis_id for nomis_id, prison in prisons.items()}

    debit_card_batches = defaultdict(int)
    prison_totals = defaultdict(int)
    prison_transactions = defaultdict(list)
    for credit in credits:
        business_unit = prisons[credit['prison']]['general_ledger_code']
        amount = Decimal(credit['amount'])/100
        prison_totals[business_unit] += amount
        if credit['source'] == 'online':
            if credit['reconciliation_code']:
                card_reconciliation_code = credit['reconciliation_code']
            else:
                card_reconciliation_code = '%s - Card payment' % journal_date
            debit_card_batches[card_reconciliation_code] += amount
        else:
            prison_transactions[business_unit].append(credit)

    # add valid payment rows
    # debit card batches
    for batch_code in debit_card_batches:
        journal.add_payment_row(
            debit_card_batches[batch_code], PaymentType.payment, RecordType.debit,
            reconciliation_code=batch_code
        )
    # other credits
    for business_unit in prison_totals:
        for transaction in prison_transactions.get(business_unit, []):
            journal.add_payment_row(
                Decimal(transaction['amount'])/100,
                PaymentType.payment, RecordType.debit,
                reconciliation_code=transaction['reconciliation_code']
            )
        journal.add_payment_row(
            prison_totals[business_unit], PaymentType.payment, RecordType.credit,
            prison_ledger_code=business_unit,
            prison_name=prisons[bu_lookup[business_unit]]['name'],
            date=journal_date
        )

    # add refund rows
    refund_total = 0
    for refund in refundable_transactions:
        refund_amount = Decimal(refund['amount'])/100
        refund_total += refund_amount
        journal.add_payment_row(
            refund_amount, PaymentType.refund, RecordType.debit,
            reconciliation_code=str(refund['ref_code'])
        )
    journal.add_payment_row(
        refund_total, PaymentType.refund, RecordType.credit, date=journal_date
    )

    # add reject rows
    for reject in rejected_transactions:
        reject_amount = Decimal(reject['amount'])/100
        reference = get_full_narrative(reject)
        journal.add_payment_row(
            reject_amount, PaymentType.reject, RecordType.debit,
            reconciliation_code=str(reject['ref_code'])
        )
        journal.add_payment_row(
            reject_amount, PaymentType.reject, RecordType.credit,
            reference=reference, date=journal_date
        )

    journal.finish_journal(receipt_date, request.user)
    created_journal = (
        settings.ADI_OUTPUT_FILENAME.format(
            initials=request.user.get_initials() or config.DEFAULT_INITIALS,
            date=date.today()
        ),
        journal.create_file()
    )
    logger.info('{user} downloaded {label} containing {count} records'.format(
        user=request.user.username,
        label=ADI_JOURNAL_LABEL,
        count=len(credits) + len(rejected_transactions) + len(refundable_transactions)
    ))

    return created_journal
