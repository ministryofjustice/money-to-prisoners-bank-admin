from django.conf import settings

from moj_auth import api_client


def retrieve_all_transactions(request, status):
    client = api_client.get_connection(request)
    response = client.bank_admin.transactions.get(
        status=status,
        limit=settings.REQUEST_PAGE_SIZE
    )
    transactions = response.get('results', [])
    total_count = response.get('count', 0)

    num_reqs = 1
    while len(transactions) < total_count:
        response = client.bank_admin.transactions.get(
            status=status,
            limit=settings.REQUEST_PAGE_SIZE,
            offset=settings.REQUEST_PAGE_SIZE*num_reqs
        )
        transactions += response.get('results', [])
        num_reqs += 1

    return transactions
