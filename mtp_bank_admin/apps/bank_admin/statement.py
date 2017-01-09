from decimal import Decimal
import logging

from django.conf import settings
from django.utils.dateparse import parse_date
from mt940_writer import Account, Balance, Statement, Transaction, TransactionType

from . import MT940_STMT_LABEL
from .utils import (
    retrieve_all_transactions, get_daily_file_uid,
    reconcile_for_date, retrieve_last_balance, get_full_narrative
)

logger = logging.getLogger('mtp')


def generate_bank_statement(request, receipt_date):
    start_date, end_date = reconcile_for_date(request, receipt_date)

    transactions = retrieve_all_transactions(
        request,
        received_at__gte=start_date,
        received_at__lt=end_date
    )

    transaction_records = []
    credit_num = 0
    credit_total = 0
    debit_num = 0
    debit_total = 0
    for transaction in transactions:
        narrative = get_full_narrative(transaction)
        amount = Decimal(transaction['amount']) / 100

        if transaction['category'] == 'debit':
            amount *= -1
            debit_num += 1
            debit_total += amount
        else:
            if transaction.get('ref_code'):
                narrative = str(transaction['ref_code']) + ' BGC'
            credit_num += 1
            credit_total += amount

        transaction_record = Transaction(
            receipt_date,
            amount,
            TransactionType.miscellaneous,
            narrative
        )
        transaction_records.append(transaction_record)

    account = Account(settings.BANK_STMT_ACCOUNT_NUMBER, settings.BANK_STMT_SORT_CODE)

    last_balance = retrieve_last_balance(request, receipt_date)
    if last_balance:
        opening_date = parse_date(last_balance['date']) or receipt_date
        opening_amount = Decimal(last_balance['closing_balance']) / 100
    else:
        opening_date = receipt_date
        opening_amount = 0
    closing_amount = opening_amount + credit_total + debit_total

    opening_balance = Balance(opening_amount, opening_date, settings.BANK_STMT_CURRENCY)
    closing_balance = Balance(closing_amount, receipt_date, settings.BANK_STMT_CURRENCY)

    statement = Statement(
        get_daily_file_uid(), account, '1/1', opening_balance,
        closing_balance, transaction_records
    )

    logger.info('{user} downloaded {label} containing {count} records'.format(
        user=request.user.username,
        label=MT940_STMT_LABEL,
        count=len(transactions)
    ))

    return (receipt_date.strftime(settings.BANK_STMT_OUTPUT_FILENAME),
            str(statement))
