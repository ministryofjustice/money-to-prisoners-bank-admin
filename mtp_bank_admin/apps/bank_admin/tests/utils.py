from contextlib import contextmanager
import json
import random
import shutil
import tempfile
from urllib.parse import urljoin, urlparse, parse_qsl

from django.conf import settings
from django.test import SimpleTestCase
import responses

from bank_admin.types import PaymentType
from bank_admin.utils import BANK_HOLIDAY_URL

TEST_PRISONS = [
    {'nomis_id': 'BPR', 'general_ledger_code': '048', 'name': 'Big Prison'},
    {'nomis_id': 'MPR', 'general_ledger_code': '067', 'name': 'Medium Prison'},
    {'nomis_id': 'SPR', 'general_ledger_code': '054', 'name': 'Small Prison'},
    {'nomis_id': 'NPR', 'general_ledger_code': '067', 'name': 'New Prison'},
]
TEST_PRISONS_RESPONSE = {'count': 4, 'results': TEST_PRISONS}
TEST_HOLIDAYS = {'england-and-wales': {
    'division': 'england-and-wales',
    'events': [
        {'title': 'Boxing Day', 'date': '2016-12-26', 'notes': '', 'bunting': True},
        {'title': 'Christmas Day', 'date': '2016-12-27', 'notes': 'Substitute day', 'bunting': True}]
}}
NO_TRANSACTIONS = {'count': 0, 'results': []}
ORIGINAL_REF = 'reference'
SENDER_NAME = 'sender'
OPENING_BALANCE = 20000


def api_url(path):
    return urljoin(settings.API_URL, path)


def mock_list_prisons():
    responses.add(
        responses.GET,
        api_url('/prisons/'),
        json=TEST_PRISONS_RESPONSE
    )


def get_test_credits(count=20):
    credits = []
    for i in range(count):
        credit = {'id': i, 'status': 'credited'}
        credit['amount'] = random.randint(500, 5000)
        if i % 2:
            credit['source'] = 'bank_transfer'
            credit['reconciliation_code'] = '9' + str(random.randint(0, 99999)).zfill(5)
        else:
            credit['source'] = 'online'
            credit['reconciliation_code'] = '800001'
        if i % 5 == 0:
            credit['prison'] = TEST_PRISONS[0]['nomis_id']
        elif i % 5 == 1:
            credit['prison'] = TEST_PRISONS[1]['nomis_id']
        elif i % 5 == 2:
            credit['prison'] = TEST_PRISONS[2]['nomis_id']
        else:
            credit['prison'] = TEST_PRISONS[3]['nomis_id']
        credits.append(credit)
    return {'count': count, 'results': sorted(credits, key=lambda t: t['id'])}


def get_test_transactions(trans_type=None, count=20):
    transactions = []
    for i in range(count):
        transaction = {'id': i, 'category': 'credit'}
        if trans_type == PaymentType.refund or trans_type is None and i % 5 == 0:
            transaction['refunded'] = True
        elif trans_type == PaymentType.payment or trans_type is None and i % 12:
            transaction['credited'] = True
            if i % 4 == 0:
                transaction['prison'] = TEST_PRISONS[0]['nomis_id']
            elif i % 4 == 1:
                transaction['prison'] = TEST_PRISONS[1]['nomis_id']
            elif i % 4 == 2:
                transaction['prison'] = TEST_PRISONS[2]['nomis_id']
            else:
                transaction['prison'] = TEST_PRISONS[3]['nomis_id']

        transaction['amount'] = random.randint(500, 5000)
        transaction['ref_code'] = '9' + str(random.randint(0, 99999)).zfill(5)
        if i % 5:
            transaction['sender_name'] = SENDER_NAME
            transaction['reference'] = ORIGINAL_REF
            transaction['reference_in_sender_field'] = False
        else:
            transaction['sender_name'] = ORIGINAL_REF
            transaction['reference_in_sender_field'] = True
        transactions.append(transaction)
    return {'count': count, 'results': sorted(transactions, key=lambda t: t['id'])}


def get_test_disbursements(count=20):
    disbursements = []
    for i in range(count):
        disbursement = {
            'id': i,
            'amount': random.randint(500, 5000),
            'prisoner': 'A' + str(random.randint(1000, 9999)) + 'AE',
            'recipient_first_name': 'Stan',
            'recipient_last_name': 'White',
            'address_line1': '50 Fake Street',
            'address_line2': '',
            'city': 'London',
            'postcode': 'N17 9LK',
            'country': 'United Kingdom',
            'resolution': 'confirmed',
            'email': 'person@mtp.local',
            'log_set': [
                {
                    'user': {
                        'first_name': 'John',
                        'last_name': 'Smith'
                    },
                    'action': 'created',
                },
                {
                    'user': {
                        'first_name': 'Pearl',
                        'last_name': 'Vance'
                    },
                    'action': 'confirmed',
                }
            ]
        }

        if i % 4 == 0:
            disbursement['prison'] = TEST_PRISONS[0]['nomis_id']
        elif i % 4 == 1:
            disbursement['prison'] = TEST_PRISONS[1]['nomis_id']
        elif i % 4 == 2:
            disbursement['prison'] = TEST_PRISONS[2]['nomis_id']
        else:
            disbursement['prison'] = TEST_PRISONS[3]['nomis_id']

        if i % 3 == 0:
            disbursement['method'] = 'cheque'
            disbursement['sort_code'] = ''
            disbursement['account_number'] = ''
            disbursement['roll_number'] = ''
        else:
            disbursement['method'] = 'bank_transfer'
            disbursement['sort_code'] = '123456'
            disbursement['account_number'] = '12345678'
            disbursement['roll_number'] = ''

        disbursements.append(disbursement)

    return {'count': count, 'results': disbursements}


class AssertCalledWithBatchRequest(object):

    def __init__(self, test_case, expected):
        self.called = False
        self.test_case = test_case
        self.expected = expected

    def __call__(self, actual):
        self.called = True
        self.test_case.assertEqual(
            actual['label'], self.expected['label']
        )
        self.test_case.assertEqual(
            sorted(actual['transactions']),
            sorted(self.expected['transactions'])
        )
        return {'id': 1}


def mock_balance():
    responses.add(
        responses.GET,
        api_url('/balances/'),
        json={
            'count': 1,
            'results': [{'closing_balance': OPENING_BALANCE, 'date': '2017-06-05'}]
        }
    )


def mock_bank_holidays():
    responses.add(
        responses.GET,
        BANK_HOLIDAY_URL,
        json=TEST_HOLIDAYS
    )


def base_urls_equal(url1, url2):
    return urlparse(url1)[:3] == urlparse(url2)[:3]


def get_query_dict(url):
    parsed_url = urlparse(url)
    return dict(parse_qsl(parsed_url.query))


@contextmanager
def temp_file(data):
    with tempfile.TemporaryFile() as f:
        f.write(data)
        yield f


class BankAdminTestCase(SimpleTestCase):

    def tearDown(self, *args, **kwargs):
        super().tearDown(*args, **kwargs)
        shutil.rmtree('local_files/cache/', ignore_errors=True)

    def assert_called_with(self, url, method, expected_data):
        called = False
        for call in responses.calls:
            if (base_urls_equal(call.request.url, url) and call.request.method == method):
                request_data = call.request.body
                if method == responses.GET:
                    request_data = get_query_dict(call.request.url)
                else:
                    request_data = json.loads(call.request.body.decode('utf-8'))
                called = called or request_data == expected_data
        self.assertTrue(called, msg='{url} not called with data {data}'.format(
            url=url, data=expected_data
        ))
