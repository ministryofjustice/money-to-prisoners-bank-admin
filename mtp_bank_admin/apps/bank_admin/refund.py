import csv
from datetime import date, datetime
from decimal import Decimal
import io
import logging

from django.conf import settings
from mtp_common.auth.backends import api_client

from . import ACCESSPAY_LABEL
from .exceptions import EmptyFileError
from .utils import (
    retrieve_all_transactions, escape_csv_formula, reconcile_for_date, WorkdayChecker
)

logger = logging.getLogger('mtp')


def generate_refund_file_for_date(request, receipt_date):
    checker = WorkdayChecker()
    start_date, end_date = checker.get_reconciliation_period_bounds(receipt_date)
    reconcile_for_date(request, start_date, end_date)

    transactions_to_refund = retrieve_all_transactions(
        request,
        status='refundable',
        received_at__gte=start_date,
        received_at__lt=end_date
    )

    filedata = generate_refund_file(request, transactions_to_refund)

    refunded_transactions = [
        {'id': t['id'], 'refunded': True} for t in transactions_to_refund if not t['refunded']
    ]

    # mark transactions as refunded
    client = api_client.get_connection(request)
    client.transactions.patch(refunded_transactions)

    logger.info('{user} downloaded {label} containing {count} records'.format(
        user=request.user.username,
        label=ACCESSPAY_LABEL,
        count=len(transactions_to_refund)
    ))

    return (date.today().strftime(settings.REFUND_OUTPUT_FILENAME),
            filedata)


def generate_refund_file(request, transactions):
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
