import time

from django.conf import settings
import six

from moj_auth import api_client


def retrieve_all_transactions(request, status, exclude_batch_label=''):
    client = api_client.get_connection(request)
    response = client.bank_admin.transactions.get(
        status=status,
        exclude_batch_label=exclude_batch_label,
        limit=settings.REQUEST_PAGE_SIZE
    )
    transactions = response.get('results', [])
    total_count = response.get('count', 0)

    num_reqs = 1
    while len(transactions) < total_count:
        response = client.bank_admin.transactions.get(
            status=status,
            exclude_batch_label=exclude_batch_label,
            limit=settings.REQUEST_PAGE_SIZE,
            offset=settings.REQUEST_PAGE_SIZE*num_reqs
        )
        transactions += response.get('results', [])
        num_reqs += 1

    return transactions


def create_batch_record(request, label, transaction_ids):
    client = api_client.get_connection(request)
    client.batches.post({
        'label': label,
        'transactions': transaction_ids
    })


def get_transaction_uid(transaction):
    return settings.TRANSACTION_ID_BASE+int(transaction['id'])


def get_daily_file_uid():
    int(time.time()) % 86400


def escape_csv_formula(value):
    """
    Escapes formulae (strings that start with =) to prevent
    spreadsheet software vulnerabilities being exploited
    :param value: the value being added to a CSV cell
    """
    if isinstance(value, six.string_types) and value.startswith('='):
        return "'" + value
    return value
