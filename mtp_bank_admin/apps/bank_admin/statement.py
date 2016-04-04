import datetime

from django.conf import settings
from bai2 import bai2, models, constants

from . import BAI2_STMT_LABEL
from .utils import (
    retrieve_all_transactions, create_batch_record, get_daily_file_uid,
    reconcile_for_date, retrieve_last_balance
)


CREDIT_TYPE_CODE = '399'
DEBIT_TYPE_CODE = '699'
OPENING_BALANCE_TYPE_CODE = '010'
CLOSING_BALANCE_TYPE_CODE = '015'
OPENING_LEDGER_TYPE_CODE = '040'
CLOSING_LEDGER_TYPE_CODE = '045'
CREDIT_TOTAL_TYPE_CODE = '100'
DEBIT_TOTAL_TYPE_CODE = '400'

RECORD_LENGTH = 80


def generate_bank_statement(request, receipt_date):
    reconcile_for_date(request, receipt_date)
    transactions = retrieve_all_transactions(
        request,
        received_at__gte=receipt_date,
        received_at__lt=(receipt_date + datetime.timedelta(days=1))
    )

    transaction_records = []
    credit_num = 0
    credit_total = 0
    debit_num = 0
    debit_total = 0
    for transaction in transactions:
        transaction_record = models.TransactionDetail([])
        transaction_record.text = str(transaction.get('reference', ''))

        if transaction['category'] == 'debit':
            transaction_record.type_code = constants.TypeCodes[DEBIT_TYPE_CODE]
            debit_num += 1
            debit_total += transaction['amount']
        else:
            transaction_record.type_code = constants.TypeCodes[CREDIT_TYPE_CODE]
            if transaction.get('ref_code'):
                transaction_record.text = 'BGC ' + str(transaction['ref_code'])
            credit_num += 1
            credit_total += transaction['amount']

        transaction_record.amount = transaction['amount']
        transaction_records.append(transaction_record)

    bai2_file = models.Bai2File()

    file_header = bai2_file.header
    file_header.sender_id = settings.BANK_STMT_SENDER_ID
    file_header.receiver_id = settings.BANK_STMT_RECEIVER_ID
    file_header.creation_date = datetime.date.today()
    file_header.creation_time = datetime.datetime.utcnow().time()
    file_header.file_id = get_daily_file_uid()
    file_header.physical_record_size = RECORD_LENGTH

    group = models.Group()
    group_header = group.header
    group_header.ultimate_receiver_id = settings.BANK_STMT_RECEIVER_ID
    group_header.originator_id = settings.BANK_STMT_SENDER_ID
    group_header.group_status = constants.GroupStatus.update
    group_header.as_of_date = receipt_date
    group_header.as_of_time = datetime.time.max
    group_header.currency = settings.BANK_STMT_CURRENCY
    group_header.as_of_date_modifier = constants.AsOfDateModifier.interim_same_day
    bai2_file.children.append(group)

    # calculate balance values with reference to 0
    opening_balance = 0
    last_balance = retrieve_last_balance(request, receipt_date)
    if last_balance:
        opening_balance = last_balance['closing_balance']
    closing_balance = opening_balance + credit_total - debit_total

    account = models.Account()
    account_header = account.header
    account_header.customer_account_number = settings.BANK_STMT_ACCOUNT_NUMBER
    account_header.currency = settings.BANK_STMT_CURRENCY
    account_header.summary_items = [
        models.Summary(
            type_code=constants.TypeCodes[OPENING_BALANCE_TYPE_CODE],
            amount=opening_balance
        ),
        models.Summary(
            type_code=constants.TypeCodes[CLOSING_BALANCE_TYPE_CODE],
            amount=closing_balance
        ),
        models.Summary(
            type_code=constants.TypeCodes[CLOSING_LEDGER_TYPE_CODE],
            amount=closing_balance
        ),
        models.Summary(
            type_code=constants.TypeCodes[OPENING_LEDGER_TYPE_CODE],
            amount=opening_balance
        ),
        models.Summary(
            type_code=constants.TypeCodes[DEBIT_TOTAL_TYPE_CODE],
            amount=debit_total,
            item_count=debit_num
        ),
        models.Summary(
            type_code=constants.TypeCodes[CREDIT_TOTAL_TYPE_CODE],
            amount=credit_total,
            item_count=credit_num
        )
    ]
    account.children = transaction_records
    group.children.append(account)

    output = bai2.write(bai2_file, clock_format_for_intra_day=True)
    if len(transactions) > 0:
        create_batch_record(request, BAI2_STMT_LABEL,
                            [t['id'] for t in transactions])

    return (receipt_date.strftime(settings.BANK_STMT_OUTPUT_FILENAME),
            output)
