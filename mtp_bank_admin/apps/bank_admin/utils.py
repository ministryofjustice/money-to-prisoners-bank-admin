from datetime import datetime, timedelta
import time

from mtp_common.api import retrieve_all_pages
from mtp_common.auth import api_client
import requests


def retrieve_all_transactions(request, **kwargs):
    endpoint = api_client.get_connection(request).transactions.get
    return retrieve_all_pages(endpoint, **kwargs)


def retrieve_all_valid_credits(request, **kwargs):
    endpoint = api_client.get_connection(request).credits.get
    return retrieve_all_pages(endpoint, valid=True, **kwargs)


def retrieve_prisons(request):
    prisons = api_client.get_connection(request).prisons.get().get('results', [])
    return {prison['nomis_id']: prison for prison in prisons}


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


def escape_csv_formula(value):
    """
    Escapes formulae (strings that start with =) to prevent
    spreadsheet software vulnerabilities being exploited
    :param value: the value being added to a CSV cell
    """
    if isinstance(value, str) and value.startswith('='):
        return "'" + value
    return value


class WorkdayChecker:

    def __init__(self):
        response = requests.get('https://www.gov.uk/bank-holidays.json')
        if response.status_code == 200:
            self.holidays = [
                datetime.strptime(holiday['date'], '%Y-%m-%d').date() for holiday in
                response.json()['england-and-wales']['events']
            ]
        else:
            raise RuntimeError(
                'Could not retrieve list of holidays for work day calculation'
            )

    def is_workday(self, date):
        return date.weekday() < 5 and date not in self.holidays

    def get_previous_workday(self, date):
        previous_day = date - timedelta(days=1)
        while not self.is_workday(previous_day):
            previous_day -= timedelta(days=1)
        return previous_day
