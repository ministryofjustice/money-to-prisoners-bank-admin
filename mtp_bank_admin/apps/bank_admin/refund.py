import csv
import io
from datetime import datetime

from moj_auth.backends import api_client

OUTPUT_FILENAME = 'mtp_accesspay_%s.csv'


def generate_refund_file(request):
    client = api_client.get_connection(request)
    refund_transactions = client.bank_admin.transactions.get()

    out = io.StringIO()
    writer = csv.writer(out)

    for transaction in refund_transactions:
        if (not transaction['sender_sort_code'] or
                not transaction['sender_account_number'] or
                not transaction['amount']):
            continue

        writer.writerow([
            transaction['sender_sort_code'],
            transaction['sender_account_number'],
            transaction['sender_name'],
            transaction['amount'],
            transaction['reference']
        ])

    return (OUTPUT_FILENAME % datetime.now().strftime('%Y-%m-%d'),
            out.getvalue())
