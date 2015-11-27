import random

from ..types import PaymentType

TEST_PRISONS = [
    {'nomis_id': 'BPR', 'general_ledger_code': '048', 'name': 'Big Prison'},
    {'nomis_id': 'DPR', 'general_ledger_code': '067',  'name': 'Dark Prison'},
    {'nomis_id': 'SPR', 'general_ledger_code': '054',  'name': 'Scary Prison'}
]

NO_TRANSACTIONS = {'count': 0, 'results': []}


def get_test_transactions(trans_type=None, count=20):
    transactions = []
    for i in range(count):
        transaction = {'id': i, 'category': 'credit'}
        if trans_type == PaymentType.refund or trans_type is None and i % 5:
            transaction['refunded'] = True
        else:
            transaction['credited'] = True
            if i % 2:
                transaction['prison'] = TEST_PRISONS[0]
            elif i % 3:
                transaction['prison'] = TEST_PRISONS[1]
            else:
                transaction['prison'] = TEST_PRISONS[2]

        transaction['amount'] = random.randint(500, 5000)
        transaction['ref_code'] = '9' + str(random.randint(0, 99999)).zfill(5)
        transactions.append(transaction)
    return {'count': count, 'results': transactions}


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
