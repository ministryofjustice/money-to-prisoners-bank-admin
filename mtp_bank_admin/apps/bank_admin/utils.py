from django.conf import settings

from moj_auth import api_client


def retrieve_all_transactions(request, status, exclude_file_type=''):
    client = api_client.get_connection(request)
    response = client.bank_admin.transactions.get(
        status=status,
        exclude_file_type=exclude_file_type,
        limit=settings.REQUEST_PAGE_SIZE
    )
    transactions = response.get('results', [])
    total_count = response.get('count', 0)

    num_reqs = 1
    while len(transactions) < total_count:
        response = client.bank_admin.transactions.get(
            status=status,
            exclude_file_type=exclude_file_type,
            limit=settings.REQUEST_PAGE_SIZE,
            offset=settings.REQUEST_PAGE_SIZE*num_reqs
        )
        transactions += response.get('results', [])
        num_reqs += 1

    return transactions


def post_new_file(request, file_type, transactions):
    client = api_client.get_connection(request)
    client.files.post({
        'file_type': file_type,
        'transactions': transactions
    })
