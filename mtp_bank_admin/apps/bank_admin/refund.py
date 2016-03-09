import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from moj_auth.backends import api_client

from . import ACCESSPAY_LABEL
from .exceptions import EmptyFileError
from .utils import (
    retrieve_all_transactions, create_batch_record, escape_csv_formula,
    get_next_weekday, reconcile_for_date
)


def generate_refund_file_for_date(request, receipt_date):
    reconcile_for_date(request, receipt_date)
    transactions_to_refund = retrieve_all_transactions(
        request,
        status='refund_pending,refunded',
        received_at__gte=receipt_date,
        received_at__lt=(receipt_date + timedelta(days=1))
    )

    filedata = generate_refund_file(request, transactions_to_refund)

    refunded_transactions = [
        {'id': t['id'], 'refunded': True} for t in transactions_to_refund if not t['refunded']
    ]

    # mark transactions as refunded
    client = api_client.get_connection(request)
    client.bank_admin.transactions.patch(refunded_transactions)

    create_batch_record(request, ACCESSPAY_LABEL,
                        [t['id'] for t in transactions_to_refund])

    return (get_next_weekday(receipt_date).strftime(settings.REFUND_OUTPUT_FILENAME),
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
