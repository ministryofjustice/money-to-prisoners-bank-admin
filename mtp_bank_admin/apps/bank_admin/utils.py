from datetime import timedelta
import time

from moj_auth import api_client
from mtp_common.api import retrieve_all_pages


def retrieve_all_transactions(request, **kwargs):
    endpoint = api_client.get_connection(request).bank_admin.transactions.get
    return retrieve_all_pages(endpoint, **kwargs)


def create_batch_record(request, label, transaction_ids):
    client = api_client.get_connection(request)
    client.batches.post({
        'label': label,
        'transactions': transaction_ids
    })


def get_last_batch(request, label):
    client = api_client.get_connection(request)
    response = client.batches.get(limit=1, label=label)
    if response.get('results'):
        return response['results'][0]
    else:
        return None


def reconcile_for_date(request, date):
    if date:
        client = api_client.get_connection(request)
        client.bank_admin.transactions.reconcile.post({
            'date': date.isoformat(),
        })


def retrieve_last_balance(request, date):
    client = api_client.get_connection(request)
    response = client.balances.get(limit=1, date__lt=date.isoformat())
    if response.get('results'):
        return response['results'][0]
    else:
        return None


def get_daily_file_uid():
    int(time.time()) % 86400


def get_next_weekday(date):
    next_weekday = date + timedelta(days=1)
    while next_weekday.weekday() >= 5:
        next_weekday += timedelta(days=1)
    return next_weekday


def escape_csv_formula(value):
    """
    Escapes formulae (strings that start with =) to prevent
    spreadsheet software vulnerabilities being exploited
    :param value: the value being added to a CSV cell
    """
    if isinstance(value, str) and value.startswith('='):
        return "'" + value
    return value
