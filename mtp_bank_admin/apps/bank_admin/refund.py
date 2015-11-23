import csv
import io
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from moj_auth.backends import api_client

from . import ACCESSPAY_LABEL
from .exceptions import EmptyFileError
from .utils import retrieve_all_transactions, create_batch_record, escape_csv_formula


def generate_refund_file(request):
    transactions_to_refund = retrieve_all_transactions(
        request,
        'refund_pending'
    )

    with io.StringIO() as out:
        writer = csv.writer(out)

        refunded_transactions = []
        for transaction in transactions_to_refund:
            cells = map(escape_csv_formula, [
                transaction['sender_sort_code'],
                transaction['sender_account_number'],
                transaction['sender_name'],
                '%.2f' % (Decimal(transaction['amount'])/100),
                settings.REFUND_REFERENCE
            ])
            writer.writerow(list(cells))
            refunded_transactions.append({'id': transaction['id'],
                                          'refunded': True})

        filedata = out.getvalue()

    if len(refunded_transactions) == 0:
        raise EmptyFileError()

    # mark transactions as refunded
    client = api_client.get_connection(request)
    client.bank_admin.transactions.patch(refunded_transactions)

    create_batch_record(request, ACCESSPAY_LABEL,
                        [t['id'] for t in refunded_transactions])

    return (settings.REFUND_OUTPUT_FILENAME % datetime.now().strftime('%Y-%m-%d'),
            filedata)
