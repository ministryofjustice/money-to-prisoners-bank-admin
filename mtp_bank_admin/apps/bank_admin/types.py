from enum import Enum


class PaymentType(Enum):
    payment = 1
    refund = 2
    reject = 3


class RecordType(Enum):
    credit = 1
    debit = 2
