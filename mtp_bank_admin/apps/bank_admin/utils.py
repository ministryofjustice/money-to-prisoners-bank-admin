from datetime import datetime, time, timedelta
import time as systime

from django.utils.timezone import now, utc
from mtp_common.api import retrieve_all_pages
from mtp_common.auth import api_client
import requests

from .exceptions import EarlyReconciliationError, UpstreamServiceUnavailable


def retrieve_all_transactions(request, **kwargs):
    endpoint = api_client.get_connection(request).transactions.get
    return retrieve_all_pages(endpoint, **kwargs)


def retrieve_all_valid_credits(request, **kwargs):
    endpoint = api_client.get_connection(request).credits.get
    return retrieve_all_pages(endpoint, valid=True, **kwargs)


def retrieve_prisons(request):
    endpoint = api_client.get_connection(request).prisons.get
    return {prison['nomis_id']: prison for prison in retrieve_all_pages(endpoint)}


def set_worldpay_cutoff(date):
    return datetime.combine(date, time(0, 0, 0, tzinfo=utc))


def get_start_and_end_date(date):
    checker = WorkdayChecker()
    start_date = set_worldpay_cutoff(date)
    end_date = set_worldpay_cutoff(checker.get_next_workday(date))
    return start_date, end_date


def reconcile_for_date(request, receipt_date):
    start_date, end_date = get_start_and_end_date(receipt_date)

    if start_date.date() >= now().date() or end_date.date() > now().date():
        raise EarlyReconciliationError

    reconciliation_date = start_date
    while reconciliation_date < end_date:
        end_of_day = reconciliation_date + timedelta(days=1)
        client = api_client.get_connection(request)
        client.transactions.reconcile.post({
            'received_at__gte': reconciliation_date.isoformat(),
            'received_at__lt': end_of_day.isoformat(),
        })
        reconciliation_date = end_of_day

    return start_date, end_date


def retrieve_last_balance(request, date):
    client = api_client.get_connection(request)
    response = client.balances.get(limit=1, date__lt=date.isoformat())
    if response.get('results'):
        return response['results'][0]
    else:
        return None


def get_daily_file_uid():
    return int(systime.time()) % 86400


def escape_csv_formula(value):
    """
    Escapes formulae (strings that start with =) to prevent
    spreadsheet software vulnerabilities being exploited
    :param value: the value being added to a CSV cell
    """
    if isinstance(value, str) and value.startswith('='):
        return "'" + value
    return value


def get_full_narrative(transaction):
    return ' '.join([
        str(transaction[field_name]) for field_name
        in ['sender_name', 'reference']
        if transaction.get(field_name)
    ])


class WorkdayChecker:

    def __init__(self):
        response = requests.get('https://www.gov.uk/bank-holidays.json')
        if response.status_code == 200:
            self.holidays = [
                datetime.strptime(holiday['date'], '%Y-%m-%d').date() for holiday in
                response.json()['england-and-wales']['events']
            ]
        else:
            raise UpstreamServiceUnavailable(
                'Could not retrieve list of holidays for work day calculation'
            )

    def is_workday(self, date):
        return date.weekday() < 5 and date not in self.holidays

    def get_next_workday(self, date):
        next_day = date + timedelta(days=1)
        while not self.is_workday(next_day):
            next_day += timedelta(days=1)
        return next_day

    def get_previous_workday(self, date):
        previous_day = date - timedelta(days=1)
        while not self.is_workday(previous_day):
            previous_day -= timedelta(days=1)
        return previous_day
