import csv
import io
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from moj_auth.backends import api_client

from . import ACCESSPAY_LABEL
from .exceptions import EmptyFileError
from .utils import retrieve_all_transactions, create_batch_record,\
    escape_csv_formula, get_last_batch


def generate_previous_refund_file(request):
    batch = get_last_batch(request, ACCESSPAY_LABEL)
    if batch:
        batched_transactions = retrieve_all_transactions(
            request,
            batch=batch['id']
        )
        return generate_refund_file(request, batched_transactions)
    else:
        raise EmptyFileError()


def generate_new_refund_file(request):
    transactions_to_refund = retrieve_all_transactions(
        request,
        status='refund_pending'
    )

    generated_data = generate_refund_file(request, transactions_to_refund)

    refunded_transactions = [
        {'id': t['id'], 'refunded': True} for t in transactions_to_refund
    ]

    # mark transactions as refunded
    client = api_client.get_connection(request)
    client.bank_admin.transactions.patch(refunded_transactions)

    create_batch_record(request, ACCESSPAY_LABEL,
                        [t['id'] for t in refunded_transactions])

    return generated_data


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

        filedata = out.getvalue()

    return (date.today().strftime(settings.REFUND_OUTPUT_FILENAME),
            filedata)


def refund_reference(transaction):
    if transaction.get('sender_roll_number'):
        return transaction['sender_roll_number']
    else:
        receipt_date = datetime.strptime(transaction['received_at'][:10], '%Y-%m-%d')
        date_part = receipt_date.strftime('%d%m')
        ref_part = transaction['ref_code'][1:]
        return settings.REFUND_REFERENCE % (date_part, ref_part)
