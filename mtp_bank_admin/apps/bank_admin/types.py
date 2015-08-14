from enum import Enum


class PaymentType(Enum):
    payment = 1
    refund = 2


class RecordType(Enum):
    credit = 1
    debit = 2
