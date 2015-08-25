import csv
import io
from datetime import datetime

from moj_auth.backends import api_client

from .exceptions import EmptyFileError

OUTPUT_FILENAME = 'mtp_accesspay_%s.csv'


def generate_refund_file(request):
    client = api_client.get_connection(request)
    refund_transactions = client.bank_admin.transactions.get(status='refund_pending')

    with io.StringIO() as out:
        writer = csv.writer(out)

        refunded_transactions = []
        for transaction in refund_transactions:
            writer.writerow([
                transaction['sender_sort_code'],
                transaction['sender_account_number'],
                transaction['sender_name'],
                transaction['amount'],
                transaction['reference']
            ])
            refunded_transactions.append({'id': transaction['id'], 'refunded': True})

        filedata = out.getvalue()

    if len(refunded_transactions) == 0:
        raise EmptyFileError()

    client.bank_admin.transactions.patch(refunded_transactions)

    return (OUTPUT_FILENAME % datetime.now().strftime('%Y-%m-%d'),
            filedata)
