import csv
import io
from datetime import datetime

from django.conf import settings
from moj_auth.backends import api_client

from .exceptions import EmptyFileError
from .utils import retrieve_all_transactions

OUTPUT_FILENAME = 'mtp_accesspay_%s.csv'


def generate_refund_file(request):
    transactions_to_refund = retrieve_all_transactions(request, 'refund_pending')

    with io.StringIO() as out:
        writer = csv.writer(out)

        refunded_transactions = []
        for transaction in transactions_to_refund:
            writer.writerow([
                transaction['sender_sort_code'],
                transaction['sender_account_number'],
                transaction['sender_name'],
                transaction['amount'],
                settings.REFUND_REFERENCE
            ])
            refunded_transactions.append({'id': transaction['id'], 'refunded': True})

        filedata = out.getvalue()

    if len(refunded_transactions) == 0:
        raise EmptyFileError()

    client = api_client.get_connection(request)
    client.bank_admin.transactions.patch(refunded_transactions)

    return (OUTPUT_FILENAME % datetime.now().strftime('%Y-%m-%d'),
            filedata)
