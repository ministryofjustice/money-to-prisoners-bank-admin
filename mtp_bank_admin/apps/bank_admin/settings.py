JOURNAL_SHEET = 'Journal 1'
LOOKUP_SHEET = 'Sheet3'

# general info
DATE_FIELD = 'J11'

# journal table
JOURNAL_START_ROW = 16

JOURNAL_DYNAMIC_COLUMNS = {
    'prison': 'D',
    'debit': 'K',
    'credit': 'L',
}

JOURNAL_COLUMNS = {
    'upload': 'B',
    'company': 'C',
    'responsibility_code': 'E',
    'activity': 'F',
    'account': 'G',
    'funding_source': 'H',
    'analysis': 'I',
    'spare': 'J',
    'description': 'M',
    'line_dff_1': 'N',
    'messages': 'P',
}

COLUMN_VALUES = {
    'upload': {
        'payment': {'debit': 'O', 'credit': 'O'},
    },
    'company': {
        'payment': {'debit': '1', 'credit': '1'},
    },
    'responsibility_code': {
        'payment': {'debit': '9500', 'credit': '9500'},
    },
    'activity': {
        'payment': {'debit': '950', 'credit': '950'},
    },
    'account': {
        'payment': {'debit': '8890', 'credit': '9400'},
    },
    'funding_source': {
        'payment': {'debit': '95', 'credit': '95'},
    },
    'analysis': {
        'payment': {'debit': '000000', 'credit': '000000'},
    },
    'spare': {
        'payment': {'debit': '000000', 'credit': '000000'},
    },
    'line_dff_1': {
        'payment': {'debit': 'MTP Payment', 'credit': 'MTP Payment'},
    },
}

from django.conf.settings import *
