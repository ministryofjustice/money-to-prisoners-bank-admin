from datetime import timedelta
import math
import time

from django.conf import settings
from mtp_common.api import retrieve_all_pages
from mtp_common.auth import api_client


def retrieve_all_transactions(request, **kwargs):
    endpoint = api_client.get_connection(request).transactions.get
    return retrieve_all_pages(endpoint, **kwargs)


def create_batch_record(request, label, transaction_ids):
    client = api_client.get_connection(request)
    response = client.batches.post({
        'label': label,
        'transactions': transaction_ids[:settings.REQUEST_PAGE_SIZE]
    })
    t_count = len(transaction_ids)
    if t_count > settings.REQUEST_PAGE_SIZE:
        batch_id = response['id']
        number_of_requests = math.ceil(len(transaction_ids)/settings.REQUEST_PAGE_SIZE)
        for i in range(1, number_of_requests):
            offset_start = i*settings.REQUEST_PAGE_SIZE
            offset_end = (i+1)*settings.REQUEST_PAGE_SIZE
            client.batches(batch_id).patch(
                {'transactions': transaction_ids[offset_start:offset_end]}
            )


def reconcile_for_date(request, date):
    if date:
        client = api_client.get_connection(request)
        client.transactions.reconcile.post({
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
