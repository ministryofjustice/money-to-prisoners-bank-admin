import csv
from datetime import datetime
from decimal import Decimal
import io
import logging

from django.conf import settings

from . import ACCESSPAY_LABEL
from .exceptions import EmptyFileError
from .utils import (
    retrieve_all_transactions, escape_csv_formula, reconcile_for_date,
    get_or_create_file, get_start_and_end_date
)

logger = logging.getLogger('mtp')


def get_refund_file(api_session, receipt_date, mark_refunded=False):
    filepath = get_or_create_file(
        ACCESSPAY_LABEL,
        receipt_date,
        generate_refund_file_for_date,
        f_args=[api_session, receipt_date]
    )
    if mark_refunded:
        mark_as_refunded(api_session, receipt_date)
    return open(filepath, 'rb')


def mark_as_refunded(api_session, date):
    start_date, end_date = get_start_and_end_date(date)
    transactions_to_refund = retrieve_all_transactions(
        api_session,
        status='refundable',
        received_at__gte=start_date,
        received_at__lt=end_date
    )
    if len(transactions_to_refund) != 0:
        refunded_transactions = [
            {'id': t['id'], 'refunded': True}
            for t in transactions_to_refund if not t['refunded']
        ]
        api_session.patch('transactions/', json=refunded_transactions)


def generate_refund_file_for_date(api_session, receipt_date):
    start_date, end_date = reconcile_for_date(api_session, receipt_date)
    transactions_to_refund = retrieve_all_transactions(
        api_session,
        status='refundable',
        received_at__gte=start_date,
        received_at__lt=end_date
    )
    filedata = generate_refund_file(transactions_to_refund)
    return filedata


def generate_refund_file(transactions):
    if len(transactions) == 0:
        raise EmptyFileError()

    with io.StringIO() as out:
        writer = csv.writer(out)

        for transaction in transactions:
            cells = map(escape_csv_formula, [
                transaction['sender_sort_code'],
                transaction['sender_account_number'],
                transaction['sender_name'],
                '%.2f' % (Decimal(transaction['amount'])/100),
                refund_reference(transaction)
            ])
            writer.writerow(list(cells))

        return out.getvalue()


def refund_reference(transaction):
    if transaction.get('sender_roll_number'):
        return transaction['sender_roll_number']
    else:
        receipt_date = datetime.strptime(transaction['received_at'][:10], '%Y-%m-%d')
        date_part = receipt_date.strftime('%d%m')
        ref_part = transaction['ref_code'][1:]
        return settings.REFUND_REFERENCE % (date_part, ref_part)
