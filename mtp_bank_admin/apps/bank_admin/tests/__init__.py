import random

from ..types import PaymentType

TEST_PRISONS = [
    {'nomis_id': 'BPR', 'general_ledger_code': '048', 'name': 'Big Prison'},
    {'nomis_id': 'DPR', 'general_ledger_code': '067',  'name': 'Dark Prison'},
    {'nomis_id': 'SPR', 'general_ledger_code': '054',  'name': 'Scary Prison'}
]

NO_TRANSACTIONS = {'count': 0, 'results': []}


def get_test_transactions(type, count=20):
    transactions = []
    for i in range(count):
        transaction = {'id': i}
        if type == PaymentType.refund:
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
        transactions.append(transaction)
    return {'count': count, 'results': transactions}
